"""Centralized configuration loaded from environment variables (.env)."""
import os
from functools import lru_cache


class Settings:
    # --- Server ---
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Downstream services ---
    EMBEDDING_SERVER_URL: str = os.getenv("EMBEDDING_SERVER_URL", "http://localhost:8003")
    INDEXING_SERVER_URL: str = os.getenv("INDEXING_SERVER_URL", "http://localhost:8002")

    # --- ChromaDB (document vector store) ---
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    DOCUMENTS_COLLECTION: str = os.getenv("DOCUMENTS_COLLECTION", "documents")
    TEXT_VECTOR_DIM: int = int(os.getenv("TEXT_VECTOR_DIM", "384"))

    # --- Qdrant (image vector store - unchanged, image pipeline only) ---
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    IMAGES_COLLECTION: str = os.getenv("IMAGES_COLLECTION", "images")

    # --- LLM providers ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" | "gemini" | "openai" | "mock"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Chunking ---
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "120"))

    # --- Search ---
    SEARCH_TOP_K: int = int(os.getenv("SEARCH_TOP_K", "5"))
    HYBRID_SEMANTIC_WEIGHT: float = float(os.getenv("HYBRID_SEMANTIC_WEIGHT", "0.6"))
    HYBRID_KEYWORD_WEIGHT: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.4"))

    # --- Storage ---
    DOCUMENT_STORAGE_DIR: str = os.getenv("DOCUMENT_STORAGE_DIR", "/data/documents")

    # --- CORS ---
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174"
    ).split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()