from celery import Celery

# app
from app.core.config import get_settings


settings = get_settings()


celery_app = Celery(
    "aiuto",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    # 직렬화 및 보안
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 시간대 설정
    timezone="UTC",
    enable_utc=True,

    # LLM 및 안정성 옵션
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_track_started=True,
)