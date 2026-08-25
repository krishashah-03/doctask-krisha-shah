import requests

from app.config import settings
from app.llm.client import LLMClient, LLMResponse

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLMClient(LLMClient):
    """Talks to Groq's OpenAI-compatible /chat/completions endpoint.

    Groq's free tier has no per-token billing, so cost_usd is always 0 —
    unlike Ollama Cloud, this isn't a shortcut, it's accurate. What it does
    have is a tight tokens-per-minute ceiling (~6k TPM on most models as of
    2026), so callers that fan out many requests quickly should expect 429s.
    """

    def __init__(self, model: str | None = None) -> None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.api_key = settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            # Without a completion cap, a reasoning model can spend its whole
            # budget on hidden thinking tokens and return an empty final
            # answer, which Groq then rejects as json_validate_failed.
            # Groq's free-tier TPM limit is charged against (prompt tokens +
            # this reservation) up front, not actual usage — kept modest so
            # a single call doesn't eat the whole per-minute budget by itself.
            "max_completion_tokens": 4096,
        }
        if "gpt-oss" in self.model:
            # reasoning_effort is only accepted for the gpt-oss models — Groq
            # 400s on other models if it's present. "low" leaves more of the
            # completion budget for the actual JSON answer.
            payload["reasoning_effort"] = "low"

        response = requests.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        if response.status_code == 429:
            raise RuntimeError(
                f"Groq rate limit hit for model {self.model!r}: {response.text}"
            )
        if not response.ok:
            raise RuntimeError(
                f"Groq API error {response.status_code} for model {self.model!r}: {response.text}"
            )
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}

        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cost_usd=0.0,
        )
