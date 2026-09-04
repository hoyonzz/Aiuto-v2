import logging

# app
from app.worker.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.dummy_task")
def dummy_task(message: str) -> dict:
    logger.info(f"[Celery Worker] 더미 태스크 수신 성공: {message}")
    return {"status": "success", "echo": message}