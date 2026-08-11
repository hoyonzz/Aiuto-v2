from functools import lru_cache

# LLM Client
from app.worker.llm.base import LLMClient
from app.worker.llm.gemini import GeminiClient
from app.worker.llm.nvidia import NvidiaClient
from app.worker.llm.fallback import FallbackLLMClient

from app.core.config import get_settings



@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    clients = []
    items = settings.llm_chain.split(",")
    for item in items:
        provider, model_name = item.split(":", 1)
        if provider == "gemini":
            clients.append(GeminiClient(api_key=settings.gemini_api_key, model=model_name))
        elif provider == "nvidia":
            clients.append(NvidiaClient(api_key=settings.nvidia_api_key, model=model_name))
        else:
            raise ValueError(f"지원하지 않는 LLM 프로바이더입니다.:{provider}")

    if len(clients) == 1:
        return clients[0]
    return FallbackLLMClient(clients=clients)