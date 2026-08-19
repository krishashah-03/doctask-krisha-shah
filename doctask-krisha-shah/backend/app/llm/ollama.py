import requests

from app.config import settings
from app.llm.client import LLMClient, LLMResponse


class OllamaLLMClient(LLMClient):
    """Talks to an Ollama-compatible /api/chat endpoint — either a local
    server (no key needed, default http://localhost:11434) or Ollama Cloud
    (set OLLAMA_BASE_URL=https://ollama.com and OLLAMA_API_KEY).
    """

    def __init__(
        self, model: str | None = None, base_url: str | None = None, api_key: str | None = None
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.api_key = api_key or settings.OLLAMA_API_KEY

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(
            f"{self.base_url}/api/chat",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "format": "json",
                "stream": False,
            },
            # Cloud models can have a slow cold-start on the first request
            # after being idle; local Ollama rarely needs this long.
            timeout=300,
        )
        if not response.ok:
            raise RuntimeError(
                f"Ollama API error {response.status_code} for model {self.model!r}: {response.text}"
            )
        data = response.json()

        content = data["message"]["content"]

        return LLMResponse(
            content=content,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            cost_usd=0.0,
        )
