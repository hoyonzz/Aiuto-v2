from google import genai
from google.genai import types
from google.genai.errors import APIError

from pydantic import ValidationError

from app.worker.llm.base import ClassificationResult, LLMClient



class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def classify(
            self, text: str, now_iso: str, timezone: str
    ) -> ClassificationResult:
        system_instrction = f"""
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
            response = self.client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instrction,
                    response_mime_type="application/json",
                    response_schema=ClassificationResult,
                    temperature=0.1,
                ),
            )
            return response.parsed
    
        except APIError as e:
            raise e

        except ValidationError as e:
            raise e
    



