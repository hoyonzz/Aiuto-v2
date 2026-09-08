import uuid

# FastAPI
from fastapi import APIRouter, Depends, status, HTTPException

# SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession

# app
from app.api.deps import get_current_user, get_db

# models
from app.models.user import User

# schemas
from app.schemas.ai_job import IngestResponse, IngestRequest, JobStatusResponse

# services
from app.services.ai_job_service import create_and_dispatch, get_job_status


router = APIRouter()


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
    summary="자연어 입력 비동기 처리 접수"
)
async def ingest_text(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> IngestResponse:
    job = await create_and_dispatch(
        session=db,
        user_id=current_user.id,
        text=request.text
    )
    return IngestResponse(job_id=job.id, status=job.status)

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="AI 비동기 작업 상태 및 결과 단건 조회"
)
async def read_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStatusResponse:
    job = await get_job_status(
        session=db,
        job_id=job_id,
        user_id=current_user.id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 작업을 찾을 수 없거나 접근 권한이 없습니다.",
        )

    return JobStatusResponse.model_validate(job)