import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# app
from app.enums import AiJobStatus, Intent



class IngestRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="사용자의 자연어 입력 텍스트",
        examples=["다음 주 화요일에 휴가가 있어서, PT선생님에게 미리 알려줘야해."]
    )

class IngestResponse(BaseModel):
    job_id: uuid.UUID = Field(
        ...,
        description="생성된 AI 작업 식별자",
    )
    status: AiJobStatus = Field(
        default=AiJobStatus.PENDING,    
        description="초기 접수 상태(기본: PENDING)",
    )


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID = Field(
        validation_alias="id",
        description="AI 작업 고유 식별자 (UUID)",
    )
    status: AiJobStatus = Field(
        ...,
        description="AI 작업 진행 상태",
    )
    intent: Intent | None = Field(
        default=None,
        description="분류된 작업 의도(task, schedule, memo, research)",
    )
    result_ref_type: str | None = Field(
        default=None,
        description="생성된 도메인 엔티티 종류(task, schedule, memo)",
    )
    result_ref_id: uuid.UUID | None = Field(
        default=None,
        description="생성된 도메인 엔티티의 고유 식별자(UUID)",
    )
    error: str | None = Field(
        default=None,
        description="작업 실패 시 에러 사유 (성공 시 null)",
    )
    created_at: datetime = Field(
        ...,
        description="작업 요청 접수 일시",
    )
    updated_at: datetime = Field(
        ...,
        description="작업 상태 최종 변경 일시",
    )