# Backend/celery_config.py
import os
from celery import Celery
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Environment variables (with default fallbacks)
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "orator",
    broker=broker_url,
    backend=result_backend,
    include=["tasks"]
)

# Optional: Configuration settings
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
)
