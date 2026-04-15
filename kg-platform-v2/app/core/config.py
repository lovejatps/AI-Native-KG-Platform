import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Chunking configuration – defaults can be overridden via .env
    CHUNK_SIZE: int = (
        12000  # characters per chunk (default 12k for balanced extraction)
    )
    CHUNK_OVERLAP: int = 200  # overlap between chunks
    MAX_CHUNKS: int = 2000  # safety guard – after this many chunks we stop processing

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    # Milvus connection can be configured via host/port or via a JSON config file
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_CONFIG_PATH: str | None = None  # optional path to JSON with host/port
    # LLM credentials – support multiple providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Default LLM model (can be overridden per instance)
    DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"
    # vLLM embedding service configuration
    VLLM_ENDPOINT: str = "https://integrate.api.nvidia.com/v1"
    VLLM_API_KEY: str = ""
    VLLM_EMBED_MODEL: str = "baai/bge-m3"
    # Embedding dimension – must match Milvus collection vector dim
    EMBEDDING_DIM: int = 768
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    ENV: str = "development"
    # Log level can be overridden via LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    # Maximum tokens the LLM can emit for KG extraction (default 4000)
    LLM_MAX_OUTPUT_TOKENS: int = 4000

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
