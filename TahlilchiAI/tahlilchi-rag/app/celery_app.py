"""Celery application configuration for background task processing."""

from celery import Celery

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "tahlilchi_rag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    # Task execution
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    # Task routes
    task_routes={
        "app.tasks.document_tasks.*": {"queue": "documents"},
    },
    # Rate limits
    task_default_rate_limit="10/m",  # 10 tasks per minute
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
