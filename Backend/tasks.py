# Backend/tasks.py

from celery_config import celery_app

@celery_app.task
def convert_text_to_audio(text: str):
    # Dummy logic — yet to be implemented
    return f"Audio generated from text: {text[:20]}..."
