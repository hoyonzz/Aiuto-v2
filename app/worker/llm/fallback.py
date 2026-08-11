from app.worker.llm.base import LLMClient, ClassificationResult, PermanentLLMError, TransientLLMError



class FallbackLLMClient:
    def __init__(self, clients: list[LLMClient]):
        if not clients:
            raise ValueError("AI서비스가 정의되지 않았습니다.")
        self.clients = clients

    def classify(self, prompt: str, now_iso: str, timezone: str) -> ClassificationResult:
        last_error = None
        for client in self.clients:
            try:
                result = client.classify(
                    prompt=prompt,
                    now_iso=now_iso,
                    timezone=timezone
                    )
                return result

            except TransientLLMError as e:
                last_error = e
                continue
            except PermanentLLMError:
                raise 

        if last_error:
            raise last_error