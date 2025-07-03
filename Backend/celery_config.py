import os
from pathlib import Path
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
Path("./static/audio").mkdir(parents=True, exist_ok=True)

# Configure Celery with optimized settings for TTS tasks
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Results
    result_expires=7200,  # Results expire after 2 hours (increased from 1 hour)
    result_persistent=True,  # Keep results in Redis
    
    # Task routing and execution
    task_always_eager=False,  # Don't execute tasks synchronously
    task_eager_propagates=True,  # Propagate exceptions when eager
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Only prefetch one task at a time (important for heavy tasks)
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to prevent memory leaks
    worker_disable_rate_limits=True,  # Disable rate limiting
    
    # Task settings
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=2400,  # 40 minutes hard limit
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker is lost
    
    # Redis specific settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Result backend settings
    result_backend_transport_options={
        'retry_on_timeout': True,
        'visibility_timeout': 3600,  # 1 hour
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Memory management
    worker_max_memory_per_child=1024000,  # 1GB memory limit per worker child
)

# # Optional: Add task routes for different queues
# celery_app.conf.task_routes = {
#     'tasks.convert_text_to_audio': {'queue': 'tts_queue'},
#     'tasks.health_check': {'queue': 'default'},
#     'tasks.test_tts_short': {'queue': 'tts_queue'},
# }