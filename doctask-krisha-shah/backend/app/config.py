import os

from dotenv import load_dotenv

# Loads variables from a local .env for dev convenience. Never commit .env,
# never print its contents, never hardcode secrets here.
load_dotenv()


class Settings:
    DATABASE_URL: str
    STORAGE_ROOT: str
    OPENROUTER_API_KEY: str | None
    SUPERDOCS_API_KEY: str | None
    LLM_PROVIDER: str
    OPENROUTER_MODEL: str
    GEMINI_API_KEY: str | None
    GEMINI_MODEL: str
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_API_KEY: str | None

    def __init__(self) -> None:
        try:
            self.DATABASE_URL = os.environ["DATABASE_URL"]
        except KeyError as exc:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
            ) from exc

        self.STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "./storage")
        self.OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
        self.SUPERDOCS_API_KEY = os.environ.get("SUPERDOCS_API_KEY")
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
        self.OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        self.GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self.OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")


settings = Settings()
