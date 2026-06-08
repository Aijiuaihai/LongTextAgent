"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for model providers, data paths, and checkpoints."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Literal["ollama", "openai_compatible", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.6:35b"

    embedding_provider: Literal["ollama", "openai"] = "ollama"
    ollama_embedding_model: str = "qwen3-embedding:8b"

    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None

    data_dir: Path = Field(default=Path("./data"))
    output_dir: Path = Field(default=Path("./outputs"))
    checkpoint_db_path: Path = Field(default=Path("./outputs/checkpoints.sqlite"))

    def safe_summary(self) -> dict[str, str | None]:
        """Return a log-safe configuration summary without secrets."""

        return {
            "llm_provider": self.llm_provider,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "embedding_provider": self.embedding_provider,
            "ollama_embedding_model": self.ollama_embedding_model,
            "openai_base_url": self.openai_base_url,
            "openai_model": self.openai_model,
            "data_dir": str(self.data_dir),
            "output_dir": str(self.output_dir),
            "checkpoint_db_path": str(self.checkpoint_db_path),
        }


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""

    return Settings()

