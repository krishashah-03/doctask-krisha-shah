import requests

from app.config import settings
from app.llm.client import LLMClient, LLMResponse

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterLLMClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        response = requests.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(
                f"OpenRouter API error {response.status_code} for model {self.model!r}: {response.text}"
            )
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}

        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cost_usd=usage.get("cost"),
        )
