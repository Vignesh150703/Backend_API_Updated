from __future__ import annotations

from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "medical_pipeline",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])

celery_app.autodiscover_tasks(["app.workers.tasks"])

