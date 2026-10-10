"""Central settings. Values are read from environment variables (or a .env file).

Properties read os.environ at access time, which keeps tests simple.
The LLM key is never logged or returned by any endpoint.
"""
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)
_fallback_secret = secrets.token_urlsafe(32)


class Settings:
    @property
    def data_dir(self) -> Path:
        return Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))

    @property
    def db_path(self) -> Path:
        return Path(os.getenv("DATABASE_PATH") or (self.data_dir / "recruitment.db"))

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def secret_key(self) -> str:
        key = os.getenv("SECRET_KEY")
        if not key:
            logger.warning("SECRET_KEY not set - using a temporary key (logins reset on restart).")
            return _fallback_secret
        return key

    @property
    def token_expire_minutes(self) -> int:
        return int(os.getenv("TOKEN_EXPIRE_MINUTES", "480"))

    @property
    def admin_username(self) -> str:
        return os.getenv("ADMIN_USERNAME", "admin")

    @property
    def admin_password(self) -> str:
        return os.getenv("ADMIN_PASSWORD", "")

    @property
    def llm_api_key(self) -> str:
        return os.getenv("LLM_API_KEY", "")

    @property
    def llm_base_url(self) -> str:
        return os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def llm_timeout(self) -> int:
        return int(os.getenv("LLM_TIMEOUT", "40"))

    @property
    def agent_use_llm_router(self) -> bool:
        return os.getenv("AGENT_USE_LLM_ROUTER", "true").lower() == "true"

    @property
    def embedding_backend(self) -> str:
        return os.getenv("EMBEDDING_BACKEND", "sentence-transformers").lower()

    @property
    def embedding_model(self) -> str:
        return os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    @property
    def max_upload_mb(self) -> int:
        return int(os.getenv("MAX_UPLOAD_MB", "5"))


settings = Settings()
