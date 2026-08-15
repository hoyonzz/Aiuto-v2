from typing import Literal, Protocol
from pydantic import BaseModel, Field



class ExtractedData(BaseModel):
    title: str|None = Field(default=None, max_length=30)
    start_at: str|None = None
    content: str|None = None
    topic: str|None = None
    due_date: str | None = Field(default=None, max_length=10)

class ClassificationResult(BaseModel):

    intent: Literal["task", "schedule", "memo", "research"]
    confidence: float = Field(
        ge=0.0,
        le=1.0
    )
    extracted: ExtractedData

class LLMClient(Protocol):
    def classify(
        self,
        prompt: str,
        now_iso: str,
        timezone: str
    ) -> ClassificationResult:
        ...

# 오류 정의
class TransientLLMError(Exception):
    """일시적 오류: Network Error, Timeout, Rate Limit(429), 5xx, JSON Parsing Error등.
    
    -> 폴백 체인에서 다음 프로바이더로 넘겨가야 하는 대상.
    """
    pass

class PermanentLLMError(Exception):
    """영구적 오류: 400 Bad Request, 401 Unauthorized, 콘텐츠 필터 차단 등.
    
    -> 코드나 설정의 버그이므로 폴백을 수행하지 않고 즉시 에러 발생.
    """
    pass