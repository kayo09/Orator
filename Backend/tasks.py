import io, os, tempfile, uuid
from celery import Celery, chain, shared_task
from celery.utils.log import get_task_logger
from TTS.api import TTS
# @celery_app.task
# def convert_text_to_audio(text: str):
#     # Dummy logic — yet to be implemented
#     return f"Audio generated from text: {text[:20]}..."
logger = get_task_logger(__name__)   
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=True)
@shared_task
def convert_text_to_audio(text: str):
    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    audio_name = f"{uuid.uuid4()}.wav"
    tts_model.tts_to_file(text=text, file_path=audio_path)
    
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
            
    os.remove(audio_path)
    logger.info(f"TTS conversion completed. Audio file: {audio_name}")

    return {
            "audio_name": audio_name,
            "audio_data": audio_data.hex(),  # Convert bytes to hex string for JSON serialization
            "status": "success"
        }
