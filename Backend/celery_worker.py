# celery_worker.py
from celery_app import celery_app
import tasks  # important to register tasks
