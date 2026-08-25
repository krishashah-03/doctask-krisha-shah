import os

from dotenv import load_dotenv

# Loads variables from a local .env for dev convenience. Never commit .env,
# never print its contents, never hardcode secrets here.
load_dotenv()


class Settings:
    DATABASE_URL: str
    STORAGE_ROOT: str
    SUPERDOCS_API_KEY: str | None
    LLM_PROVIDER: str
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    OLLAMA_API_KEY: str | None
    GROQ_API_KEY: str | None
    GROQ_MODEL: str

    def __init__(self) -> None:
        try:
            self.DATABASE_URL = os.environ["DATABASE_URL"]
        except KeyError as exc:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
            ) from exc

        self.STORAGE_ROOT = os.environ.get("STORAGE_ROOT", "./storage")
        self.SUPERDOCS_API_KEY = os.environ.get("SUPERDOCS_API_KEY")
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
        self.OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
        self.GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
        self.GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


settings = Settings()
