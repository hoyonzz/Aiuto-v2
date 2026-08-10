from functools import lru_cache

from app.worker.llm.base import LLMClient
from app.core.config import get_settings



@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    provider, model_name = settings.llm_chain.split(":")
    if provider == "gemini":
        # return GeminiClient(api_key=settings.gemini_api_key, model=model_name)
        pass
    elif provider == "NVIDIA모델":
        # return NvidiaClient(api_key=settings.nvidia_api_key, model=model_name)
        pass
    else:
        raise ValueError(f"지원하지 않는 LLM 프로바이더입니다.:{provider}")