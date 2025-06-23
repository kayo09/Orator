from celery import Celery
from celery_app import celery_app

if __name__ == "__main__":
    # Launch a worker programmatically
    celery_app.worker_main(["worker", "--loglevel=INFO"])  