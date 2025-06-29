import os
from celery import Celery

# Environment variables (with default fallbacks)
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "orator",
    broker=broker_url,
    backend=result_backend,
    include=["tasks"]
)