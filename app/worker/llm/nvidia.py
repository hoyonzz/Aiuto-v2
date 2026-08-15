from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from pydantic import ValidationError

from app.worker.llm.base import ClassificationResult, TransientLLMError, PermanentLLMError
from app.worker.llm.time_utils import build_date_anchors, to_utc_iso


class NvidiaClient:
    def __init__(
        self,
        api_key: str,
        model: str = ""
    ):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        self.model = model

    def classify(
            self,
            prompt: str,
            now_iso: str,
            timezone: str
    ) -> ClassificationResult:
        date_anchors = build_date_anchors(now_iso)
        system_instruction = f"""
        너는 사용자의 자연어 요청을 분류하고 핵심 정보를 추출하는 AI 비서야.
        
        [기준 시각 정보]
        {date_anchors}
        - 사용자 타임존: {timezone}
        
        [분류 규칙]
        1. schedule: 특정 날짜/시각이 포함된 일정 (예: "내일 3시 회의")
        - extracted 객체에 title, start_at 포함할 것.
        - start_at은 [날짜 참고표]의 날짜 + 문장 속 시각을 그대로 조합한 로컬 시각이다. 예: "내일 3시" + 내일 = 2026-08-14 -> "2026-08-14T15:00:00"
        - '자정'/'밤 12시'처럼 날짜 귀속이 모호한 표현은 오늘이 아니라 내일 날짜의 00:00으로 계산하라.
        - 절대 UTC로 변환하지 마라. 시간대 계산을 하지 말고 그냥 표에 있는 날짜와 문장에 나온 시각을 이어붙이기만 해라.
        2. task: 시각은 없지만 해야 할 일 (예: "보고서 초안 작성해야 함")
        - extracted 객체에 title 포함할 것.
        - 마감 기한이 언급되면 (예: "금요일까지") extracted 객체에 due_date도 포함할 것.
            [날짜 참고표]를 참고해 해당 날짜를 "YYYY-MM-DD" 형식으로 적을 것.
            시각은 포함하지 말 것. 마감 언급이 없으면 due_date는 비워둘것.
        - 단, 마감과 함께 하루 중 고정된 시각(예: "자정", "오전 9시", "오후 5시")이
            언급되면 이는 task가 아니라 schedule이다.
        - "3시간 뒤"/"30분 뒤"처럼 지금으로부터의 상대적 시간 간격은 고정된 시각이
            아니다. 이 경우 계산하지 말고 task로 분류하며, title에 원문 표현을 그대로 남길 것 (예: "3시간 뒤 전화하기").
        3. memo: 단순 기록/메모 (예: "오늘 회의 결정: 예산 300만")
        - extracted 객체에 content 포함할 것.
        4. research: 조사나 연구가 필요한 질문 (예: "파이썬 asyncio 알려줘")
        - extracted 객체에 topic 포함할 것.

        [출력 규칙]
        - 각 필드에는 최종 값만 넣는다. 설명, 계산 과정, 중간 사고를 절대 포함하지 않는다.
        - title은 한국어 명사구로 30자 이내로 작성한다. 문장으로 쓰지 않는다.
        """

        try:
            json_schema = ClassificationResult.model_json_schema()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role":"user", "content": prompt}
                ],
                temperature=0.1,
                extra_body={"nvext": {"guided_json": json_schema}}
            )

            choice = response.choices[0] if response.choices else None
            finish_reason = str(getattr(choice, "finish_reason", "")).upper() if choice else ""

            if finish_reason in ("STOP", "LENGTH"):
                raw_json = choice.message.content if choice and choice.message else None

                if raw_json is None:
                    raise TransientLLMError("Nvidia 응답 내용 유실 (content is None)")

                try:
                    result = ClassificationResult.model_validate_json(raw_json)
                except (ValidationError, TypeError) as e:
                    raise TransientLLMError(f"Nvidia output parsing failed: {e}") from e

                if result.extracted.start_at is not None:
                    result.extracted.start_at = to_utc_iso(result.extracted.start_at, timezone)
                return result
            else:
                raise PermanentLLMError(f"Nvidia 콘텐츠/정책 차단 또는 비정상 종료 (finish_reason: {finish_reason})")
            
        except (RateLimitError, APIConnectionError) as e:
            raise TransientLLMError(str(e)) from e

        except APIError as e:
            if e.status_code in (429, 500, 502, 503, 504):
                raise TransientLLMError(f"Nvidia 일시적 오류 [{e.status_code}]: {e}") from e
            raise PermanentLLMError(
                f"Nvidia 영구적 오류 [{e.status_code}]: {e}"
            ) from e

        except ValidationError as e:
            raise TransientLLMError(f"Nvidia output parsing failed: {e}") from e
            