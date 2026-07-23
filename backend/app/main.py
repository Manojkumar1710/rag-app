"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.routers import chat, documents, images, search

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Application Backend",
    description="Production-quality Retrieval-Augmented Generation backend.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(images.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "backend"}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Backend starting up. LLM provider: %s", settings.LLM_PROVIDER)
