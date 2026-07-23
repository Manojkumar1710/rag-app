"""
Embedding Server
================
Exposes text and image embedding models over a small FastAPI HTTP API.

Models are loaded once at process startup (module-level singletons) so that
every request reuses the same in-memory model instead of reloading weights
from disk, which would be far too slow for an interactive service.
"""

import base64
import io
import logging
import os

from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("embedding-server")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "sentence-transformers/clip-ViT-B-32")

# --------------------------------------------------------------------------- #
# Model loading (singleton, at import time)
# --------------------------------------------------------------------------- #
logger.info("Loading text embedding model: %s", TEXT_MODEL_NAME)
text_model = SentenceTransformer(TEXT_MODEL_NAME)

logger.info("Loading CLIP model: %s", CLIP_MODEL_NAME)
clip_model = SentenceTransformer(CLIP_MODEL_NAME)

logger.info("Models loaded successfully.")

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class TextEmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="List of texts to embed")


class ImageEmbedRequest(BaseModel):
    images_base64: list[str] = Field(..., min_length=1, description="Base64-encoded images")


class ClipTextEmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="Texts to embed in CLIP space")


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dimension: int
    model: str


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="Embedding Server", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "text_model": TEXT_MODEL_NAME, "clip_model": CLIP_MODEL_NAME}


@app.post("/embed/text", response_model=EmbedResponse)
def embed_text(req: TextEmbedRequest) -> EmbedResponse:
    try:
        vectors = text_model.encode(req.texts, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text embedding failed")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc

    return EmbedResponse(
        embeddings=[v.tolist() for v in vectors],
        dimension=vectors.shape[1],
        model=TEXT_MODEL_NAME,
    )


@app.post("/embed/image", response_model=EmbedResponse)
def embed_image(req: ImageEmbedRequest) -> EmbedResponse:
    images = []
    for idx, b64 in enumerate(req.images_base64):
        try:
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            images.append(img)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"Invalid image at index {idx}: {exc}"
            ) from exc

    try:
        vectors = clip_model.encode(images, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Image embedding failed")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc

    return EmbedResponse(
        embeddings=[v.tolist() for v in vectors],
        dimension=vectors.shape[1],
        model=CLIP_MODEL_NAME,
    )


@app.post("/embed/clip-text", response_model=EmbedResponse)
def embed_clip_text(req: ClipTextEmbedRequest) -> EmbedResponse:
    """Embed text into the same vector space as CLIP images, for text-to-image search."""
    try:
        vectors = clip_model.encode(req.texts, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as exc:  # noqa: BLE001
        logger.exception("CLIP text embedding failed")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc

    return EmbedResponse(
        embeddings=[v.tolist() for v in vectors],
        dimension=vectors.shape[1],
        model=CLIP_MODEL_NAME,
    )
