from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import settings


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise NotImplementedError


def get_llm_client() -> LLMClient:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "mock":
        from app.llm.mock import MockLLMClient

        return MockLLMClient()

    if provider == "ollama":
        from app.llm.ollama import OllamaLLMClient

        return OllamaLLMClient()

    if provider == "groq":
        from app.llm.groq import GroqLLMClient

        return GroqLLMClient()

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")
