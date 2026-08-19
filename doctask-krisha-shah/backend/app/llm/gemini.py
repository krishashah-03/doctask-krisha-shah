import requests

from app.config import settings
from app.llm.client import LLMClient, LLMResponse

_GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiLLMClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.api_key = settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        url = _GEMINI_URL_TEMPLATE.format(model=self.model)
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(
                f"Gemini API error {response.status_code} for model {self.model!r}: {response.text}"
            )
        data = response.json()

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata") or {}

        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
            cost_usd=None,
        )
