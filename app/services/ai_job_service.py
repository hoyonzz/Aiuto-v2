import uuid

# SQLAlchemy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# app
from app.models.ai_job import AiJob
from app.enums import AiJobStatus
from app.worker.tasks import process_ingest_task



async def create_and_dispatch(
        session: AsyncSession,
        user_id: uuid.UUID,
        text: str
) -> AiJob:
    job = AiJob(
        user_id=user_id,
        raw_text=text,
        status=AiJobStatus.PENDING
    )
    session.add(job)

    await session.commit()
    await session.refresh(job)

    process_ingest_task.delay(str(job.id))

    return job

async def get_job_status(
    session: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AiJob | None:
    stmt = select(AiJob).where(
        AiJob.id == job_id,
        AiJob.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()