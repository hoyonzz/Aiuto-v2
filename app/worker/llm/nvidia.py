from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from pydantic import ValidationError

from app.worker.llm.base import ClassificationResult, TransientLLMError, PermanentLLMError



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
        system_instruction = f"""
        너는 사용자의 자연어 요청을 분류하고 핵심 정보를 추출하는 AI 비서야.
        
        [기준 시각 정보]
        - 현재 UTC 시각: {now_iso}
        - 사용자 타임존: {timezone}
        
        [분류 규칙]
        1. schedule: 특정 날짜/시각이 포함된 일정 (예: "내일 3시 회의")
        - extracted 객체에 title, start_at(ISO8601 UTC 변환 시각) 포함할 것.
        2. task: 시각은 없지만 해야 할 일 (예: "보고서 초안 작성해야 함")
        - extracted 객체에 title 포함할 것.
        3. memo: 단순 기록/메모 (예: "오늘 회의 결정: 예산 300만")
        - extracted 객체에 content 포함할 것.
        4. research: 조사나 연구가 필요한 질문 (예: "파이썬 asyncio 알려줘")
        - extracted 객체에 topic 포함할 것.
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
                    return ClassificationResult.model_validate_json(raw_json)
                except (ValidationError, TypeError) as e:
                    raise TransientLLMError(f"Nvidia output parsing failed: {e}") from e

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
            