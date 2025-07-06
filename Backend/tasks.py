import io
import os
import tempfile
import uuid
import subprocess
import shutil
from celery.utils.log import get_task_logger
from celery_config import celery_app

logger = get_task_logger(__name__)

# Globals and chunking configuration
tts_model = None
MIN_CHARS = 50       # Minimum chars per chunk to avoid tiny audio segments
MAX_CHARS = 2000     # Target max chars per chunk (~1–2 minute speech)


def get_tts_model():
    """Lazily load the TTS engine only when needed, with error handling."""
    global tts_model
    if tts_model is None:
        try:
            logger.info("Initializing TTS model...")
            # Heavy imports inside function so module can load in CI/tests
            from TTS.api import TTS
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            # Force CPU for stability; disable progress bar
            tts_model = TTS(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                gpu=False,
                progress_bar=False,
            )
            logger.info("TTS model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS model: {e}")
            # Reraise so callers can retry or fail gracefully
            raise
    return tts_model


def make_chunks(text: str) -> list[str]:
    """Split text into sentence-based chunks between MIN_CHARS and MAX_CHARS."""
    # sentence tokenizer inside function to avoid global nltk download
    from nltk.tokenize import sent_tokenize
    import nltk
    nltk.download("punkt_tab", quiet=True)

    # Normalize whitespace
    text = text.replace("\n", " ")
    sentences = sent_tokenize(text)
    chunks: list[str] = []
    current = ""

    for sent in sentences:
        # If adding the sentence exceeds our max, seal the current chunk
        if len(current) + len(sent) + 1 > MAX_CHARS:
            if current:
                chunks.append(current.strip())
            current = sent
        else:
            current = f"{current} {sent}".strip()

    # Add the final chunk
    if current:
        chunks.append(current.strip())

    # Merge any too-small trailing chunks into the previous one
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHARS:
            merged[-1] = f"{merged[-1]} {chunk}"
        else:
            merged.append(chunk)
    return merged


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def convert_text_to_audio(self, text: str, file_id: str = None) -> str:
    """Main Celery task: convert input text into a single WAV audio file."""
    try:
        logger.info(f"Starting TTS conversion for text length: {len(text)} chars")
        
        # Use file_id if provided, otherwise generate UUID
        if file_id:
            audio_name = f"{file_id}.wav"
        else:
            audio_name = f"{uuid.uuid4()}.wav"

        # Discover a writable static directory
        possible_paths = [
            "/app/static/audio",
            "./static/audio",
            "static/audio",
        ]
        static_audio_dir = None
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                testfile = os.path.join(path, f"test_{uuid.uuid4()}.tmp")
                with open(testfile, "w") as f:
                    f.write("test")
                os.remove(testfile)
                static_audio_dir = path
                logger.info(f"Using audio directory: {path}")
                break
            except Exception:
                continue

        if not static_audio_dir:
            raise RuntimeError("No writable audio output directory found")

        audio_path = os.path.join(static_audio_dir, audio_name)

        # Chunk the text
        chunks = make_chunks(text)
        logger.info(f"Text split into {len(chunks)} chunk(s)")
        self.update_state(state='PROGRESS', meta={"current": 0, "total": len(chunks), "audio_name": audio_name})
        # Load TTS model
        model = get_tts_model()

        # Single vs multiple chunks
        if len(chunks) == 1:
            try:
                model.tts_to_file(text=chunks[0], file_path=audio_path)
            except RuntimeError as e:
                logger.warning(f"Skipping tiny chunk: {e}")
                # Leave file absent or empty
        else:
            # Convert each chunk and concatenate
            temp_dir = tempfile.mkdtemp()
            temp_files = []
            try:
                for i, chunk in enumerate(chunks):
                    chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                    logger.info(f"Converting chunk {i+1}/{len(chunks)}")
                    try:
                        model.tts_to_file(text=chunk, file_path=chunk_path)
                        temp_files.append(chunk_path)
                    except RuntimeError as e:
                        logger.warning(f"Chunk {i+1} failed: {e}")
                    self.update_state(state='PROGRESS', meta={"current": i + 1, "total": len(chunks), "audio_name": audio_name})    


                # Attempt concatenation via ffmpeg
                list_file = os.path.join(temp_dir, "files.txt")
                with open(list_file, "w") as f:
                    for tf in temp_files:
                        f.write(f"file '{tf}'\n")
                try:
                    subprocess.run([
                        "ffmpeg", "-f", "concat", "-safe", "0",
                        "-i", list_file, "-c", "copy", audio_path
                    ], check=True, capture_output=True)
                    logger.info("Audio chunks combined via ffmpeg")
                except Exception:
                    logger.warning("ffmpeg failed or unavailable, using first chunk")
                    if temp_files:
                        shutil.copy2(temp_files[0], audio_path)
            finally:
                # Cleanup temp files
                for tf in temp_files:
                    try: os.remove(tf)
                    except: pass
                try: os.rmdir(temp_dir)
                except: pass

        # Ensure audio exists and is non-empty
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise RuntimeError("Audio generation failed or produced empty file")

        logger.info(f"TTS conversion complete: {audio_path}")
        return audio_name

    except Exception as e:
        logger.error(f"TTS conversion failed: {e}")
        # Cleanup partial
        try:
            if 'audio_path' in locals() and os.path.exists(audio_path): # type: ignore
                os.remove(audio_path) # type: ignore
                logger.info("Cleaned up partial audio file")
        except:
            pass
        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        raise
# ----------------------------------------------------------------------------- 

@celery_app.task(bind=True)
def health_check(self) -> str:
    """Verify Celery worker is responsive."""
    logger.info("Health check executed")
    return "OK"


@celery_app.task(bind=True)
def test_tts_short(self) -> str:
    """Quick smoke test for the TTS pipeline."""
    return convert_text_to_audio(self, "Hello, this is a TTS system test.")