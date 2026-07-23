import os


class Settings:
    EMBEDDING_SERVER_URL: str = os.getenv("EMBEDDING_SERVER_URL", "http://localhost:8003")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    IMAGES_COLLECTION: str = os.getenv("IMAGES_COLLECTION", "images")
    IMAGE_STORAGE_DIR: str = os.getenv("IMAGE_STORAGE_DIR", "/data/images")
    OCR_LANGUAGES: list[str] = os.getenv("OCR_LANGUAGES", "en").split(",")


settings = Settings()
