"""Extended settings for Phase‑2 (二期).

Provides:
- Multi‑environment selection via ``ENV`` (development, staging, production).
- Feature flags dictionary ``FEATURE_FLAGS`` that can toggle new functionality.
- Backward‑compatible ``get_settings`` wrapper that returns a ``SettingsV2``
  instance so existing code can continue importing ``app.core.config.get_settings``
  without changes. New code should import ``SettingsV2`` directly.
"""

import os
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class SettingsV2(BaseSettings):
    # Existing core settings – copied from the original Settings class
    CHUNK_SIZE: int = 12000
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS: int = 2000

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_CONFIG_PATH: str | None = None
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"
    VLLM_ENDPOINT: str = "https://integrate.api.nvidia.com/v1"
    VLLM_API_KEY: str = ""
    VLLM_EMBED_MODEL: str = "baai/bge-m3"
    EMBEDDING_DIM: int = 768
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # New fields for Phase‑2
    ENV: str = Field(default="development", description="Current environment")
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "TRACE").upper())
    BUSINESS_DB_PATH: str = Field(default="business.db", description="Path to the business SQLite DB file used by NL2SQL")
    LLM_MAX_OUTPUT_TOKENS: int = 4000

    # Feature flags – can be overridden via environment variable JSON string
    FEATURE_FLAGS: dict = Field(default_factory=dict)

    class Config:
        env_file = ".env"
        # Allow env vars like FEATURE_FLAGS__EXPORT=True to set nested dict values
        env_nested_delimiter = "__"


def get_settings() -> SettingsV2:
    """Return a SettingsV2 instance – this mirrors the original ``get_settings``
    function so existing imports keep working.
    """
    return SettingsV2()
