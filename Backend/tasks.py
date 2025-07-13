import io
import os
import tempfile
import uuid
import subprocess
import shutil
import re
import unicodedata
import logging
import json
from celery.utils.log import get_task_logger
from celery_config import celery_app

logger = get_task_logger(__name__)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Chunking configuration
MIN_CHARS = 50
MAX_CHARS = 1000

def get_optimal_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", True
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps", False
        else:
            return "cpu", False
    except ImportError:
        return "cpu", False

def preprocess_text(text: str) -> str:
    if not text or not text.strip():
        return ""

    text = unicodedata.normalize('NFKD', text)
    replacements = {
        '\u00a0': ' ', '\u2013': '-', '\u2014': '-', '\u2018': "'",
        '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\.{4,}', '...', text)
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)
    text = re.sub(r'\s*([,.!?;:])\s*', r'\1 ', text)
    text = re.sub(r'\s*(\")\s*', r'\1', text)
    text = re.sub(r'\s+"([^"]*?)"\s+', r' "\1" ', text)
    text = re.sub(r'\s*\(\s*([^)]*?)\s*\)\s*', r' (\1) ', text)
    text = re.sub(r'(Chapter\s+\d+[:\-\s]*)', r'\1. ', text, flags=re.IGNORECASE)
    text = re.sub(r'(Section\s+\d+[:\-\s]*)', r'\1. ', text, flags=re.IGNORECASE)
    text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
    text = text.strip()

    sentences = re.split(r'[.!?]+', text)
    cleaned = [s.strip() for s in sentences if len(s.strip()) > 3]
    if cleaned:
        text = '. '.join(cleaned)
        if not text.endswith(('.', '!', '?')):
            text += '.'

    return text

def make_chunks(text: str) -> list[str]:
    try:
        import nltk
        nltk.download("punkt", quiet=True)
        from nltk.tokenize import sent_tokenize
        sentences = sent_tokenize(text)
        logger.info("Using NLTK tokenizer")
    except Exception as e:
        logger.warning(f"NLTK failed: {e}, using regex fallback")
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > MAX_CHARS:
            if current:
                chunks.append(current.strip())
            current = sent
        else:
            current = f"{current} {sent}".strip()

    if current:
        chunks.append(current.strip())

    merged = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHARS:
            merged[-1] = f"{merged[-1]} {chunk}"
        else:
            merged.append(chunk)

    return [c for c in merged if len(c.strip()) >= MIN_CHARS]

def get_tts_model_local():
    from TTS.api import TTS
    device, use_gpu = get_optimal_device()
    models = [
        {"name": "tts_models/en/vctk/vits", "multi": True},
        {"name": "tts_models/en/ljspeech/tacotron2-DDC", "multi": False},
        {"name": "tts_models/en/ljspeech/vits", "multi": False}
    ]
    for m in models:
        try:
            model = TTS(model_name=m["name"], gpu=use_gpu, progress_bar=False)
            model._is_multi_speaker = m["multi"]
            return model
        except Exception as e:
            logger.warning(f"Failed to load {m['name']}: {e}")
    raise RuntimeError("All TTS models failed to load")

def ffmpeg_installed():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def generate_tts_audio(model, text, file_path):
    try:
        speaker = None
        if getattr(model, '_is_multi_speaker', False):
            try:
                speakers = model.speakers
                speaker = "p225" if "p225" in speakers else speakers[0]
            except:
                raise RuntimeError("No valid speaker found")

        model.tts_to_file(text=text, file_path=file_path, speaker=speaker if speaker else None)
        return True
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return False

def find_audio_output_dir():
    paths = ["/app/static/audio", "./static/audio", "static/audio"]
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
            if os.access(path, os.W_OK):
                return path
        except Exception as e:
            logger.warning(f"Audio path check failed for {path}: {e}")
    raise RuntimeError("No writable audio directory found")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def convert_text_to_audio(self, text: str, file_id: str = None) -> str:
    try:
        logger.info(f"Starting conversion: {len(text)} chars")
        text = preprocess_text(text)
        if not text:
            raise ValueError("No valid text")

        audio_name = f"{file_id or uuid.uuid4()}.wav"
        audio_dir = find_audio_output_dir()
        audio_path = os.path.join(audio_dir, audio_name)
        
        logger.info(f"Audio will be saved to: {audio_path}")
        logger.info(f"Audio directory: {audio_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")

        chunks = make_chunks(text)
        model = get_tts_model_local()

        temp_dir = tempfile.mkdtemp()
        temp_files = []
        segments = []
        current_time = 0.0

        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            if generate_tts_audio(model, chunk, chunk_path):
                temp_files.append(chunk_path)

                # Get chunk duration with ffprobe
                duration = 0.0
                try:
                    result = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries",
                         "format=duration", "-of",
                         "default=noprint_wrappers=1:nokey=1", chunk_path],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                    )
                    duration = float(result.stdout.decode().strip())
                except Exception as e:
                    logger.warning(f"ffprobe failed on chunk {i}: {e}")

                segments.append({
                    "text": chunk,
                    "start_time": round(current_time, 2),
                    "end_time": round(current_time + duration, 2)
                })
                current_time += duration

        if not temp_files:
            raise RuntimeError("No audio generated")

        list_file = os.path.join(temp_dir, "files.txt")
        with open(list_file, "w") as f:
            for fpath in temp_files:
                f.write(f"file '{fpath}'\n")

        if ffmpeg_installed():
            subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", audio_path],
                           check=True, capture_output=True, text=True)
        else:
            shutil.copy2(temp_files[0], audio_path)

        shutil.rmtree(temp_dir, ignore_errors=True)

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise RuntimeError("Final audio is empty")

        # Save segment data to static/audio/{file_id}_segments.json
        segment_path = os.path.join(audio_dir, f"{file_id}_segments.json")
        with open(segment_path, "w") as f:
            json.dump({"segments": segments}, f, indent=2)
        logger.info(f"Segments saved to {segment_path}")
        logger.info(f"Segments file exists: {os.path.exists(segment_path)}")
        logger.info(f"Segments file size: {os.path.getsize(segment_path) if os.path.exists(segment_path) else 'N/A'}")

        logger.info(f"Audio saved: {audio_path}")
        logger.info(f"Audio file exists: {os.path.exists(audio_path)}")
        logger.info(f"Audio file size: {os.path.getsize(audio_path) if os.path.exists(audio_path) else 'N/A'}")
        return audio_name

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        raise


@celery_app.task(bind=True)
def health_check(self):
    return "OK"

@celery_app.task(bind=True)
def test_tts_short(self):
    return convert_text_to_audio(self, "Hello, this is a TTS test.")

@celery_app.task(bind=True)
def get_available_speakers(self):
    try:
        model = get_tts_model_local()
        speakers = getattr(model, "speakers", [])
        return {
            "is_multi_speaker": getattr(model, '_is_multi_speaker', False),
            "speakers": speakers
        }
    except Exception as e:
        logger.error(f"Speaker fetch failed: {e}")
        return {"is_multi_speaker": False, "speakers": [], "error": str(e)}
