import logging
import uuid

# app
from app.core.db import get_sync_db
from app.enums import AiJobStatus, Intent

# app.models
from app.models.ai_job import AiJob
from app.models.task import Task
from app.models.schedule import Schedule
from app.models.memo import Memo
from app.models.user import User

# app.worker
from app.worker.celery_app import celery_app
from app.worker.llm.factory import get_llm_client
from app.worker.llm.base import TransientLLMError, PermanentLLMError

# time관련
from zoneinfo import ZoneInfo
from datetime import datetime, date


logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.dummy_task")
def dummy_task(message: str) -> dict:
    logger.info(f"[Celery Worker] 더미 태스크 수신 성공: {message}")
    return {"status": "success", "echo": message}

@celery_app.task(name="app.worker.tasks.process_ingest_task")
def process_ingest_task(job_id: str) -> None:
    try:
        parsed_job_id = uuid.UUID(job_id)
    except ValueError:
        logger.error(f"잘못된 UUID 형식입니다: {job_id}")
        return

    with get_sync_db() as session:
        job = session.get(AiJob, parsed_job_id)
        if not job:
            logger.warning(f"작업을 찾을 수 없습니다: {job_id}")
            return

        if job.status == AiJobStatus.SUCCESS:
            logger.info(f"이미 처리 완료된 작업입니다: {job_id}")
            return

       
        job.status = AiJobStatus.PROCESSING
        session.flush()


        user = session.get(User, job.user_id)
        if not user:
            logger.warning(f"유저를 찾을 수 없습니다: {job.user_id}")
            return

        user_tz = getattr(user, "timezone", None) or "Asia/Seoul"
        now_iso = datetime.now(ZoneInfo(user_tz)).isoformat()

        try:
            client = get_llm_client()
            result = client.classify(
                prompt=job.raw_text,
                now_iso=now_iso,
                timezone=user_tz
            )
        except (TransientLLMError, PermanentLLMError) as e:
            job.status = AiJobStatus.FAILED
            job.error = str(e)
            logger.error(f"요청사항 AI 분석 실패: {e}")
            return

        extracted = result.extracted
        created_entity = None
        ref_type = None

        if extracted.title:
            entity_title = extracted.title
        else:
            entity_title = job.raw_text[:30]

        if result.intent == "task":
            ref_type = "task"

            if extracted.due_date:
                due_date_val = date.fromisoformat(extracted.due_date)
            else:
                due_date_val = None

            created_entity = Task(
                user_id=job.user_id,
                title=entity_title,
                due_date=due_date_val,
            )

        elif result.intent == "schedule":
            ref_type = "schedule"

            if extracted.start_at:
                logger.info(f"[LLM 원본 start_at 추출값]: {extracted.start_at}")

                raw_start = extracted.start_at.replace("Z", "+00:00")
                parsed_dt = datetime.fromisoformat(raw_start)

                if parsed_dt.tzinfo is not None:
                    start_at_utc = parsed_dt.astimezone(ZoneInfo("UTC"))
                else:
                    local_dt_with_tz = parsed_dt.replace(tzinfo=ZoneInfo(user_tz))
                    start_at_utc = local_dt_with_tz.astimezone(ZoneInfo("UTC"))
            else:
                start_at_utc = datetime.now(ZoneInfo("UTC"))

            created_entity = Schedule(
                user_id=job.user_id,
                title=entity_title,
                start_at=start_at_utc,
            )

        elif result.intent == "memo":
            ref_type = "memo"

            if extracted.content:
                memo_content = extracted.content
            else:
                memo_content = job.raw_text

            created_entity = Memo(
                user_id=job.user_id,
                content=memo_content
            )

        elif result.intent == "research":
            ref_type = None
            created_entity = None

        if created_entity is not None:
            session.add(created_entity)
            session.flush()
            ref_id = created_entity.id
        else:
            ref_id = None

        job.status = AiJobStatus.SUCCESS
        job.intent = Intent(result.intent)
        job.result_ref_type = ref_type
        job.result_ref_id = ref_id

        job.model_used = getattr(result, "model_name", None) or "gemini-3.5-flash-lite"

        logger.info(
            f"[태스크 성공] job_id={job_id}, intent={job.intent}, "
            f"ref_type={job.result_ref_type}, ref_id={job.result_ref_id}"
        )
        