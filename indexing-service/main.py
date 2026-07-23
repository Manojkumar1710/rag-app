"""
Picture Indexing Service
=========================
Receives uploaded images, runs OCR (EasyOCR), generates CLIP image embeddings
and OCR-text embeddings, stores the raw image to disk, and writes a vector
record (with both embeddings concatenated/stored as named vectors) into the
Qdrant "images" collection.
"""

import base64
import logging
import os
import uuid
from datetime import datetime, timezone

import easyocr
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from config import settings

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("indexing-service")

os.makedirs(settings.IMAGE_STORAGE_DIR, exist_ok=True)

logger.info("Loading EasyOCR reader for languages: %s", settings.OCR_LANGUAGES)
ocr_reader = easyocr.Reader(settings.OCR_LANGUAGES, gpu=False)

qdrant = QdrantClient(url=settings.QDRANT_URL)

CLIP_DIM = 512
TEXT_DIM = 384


def ensure_collection() -> None:
    collections = [c.name for c in qdrant.get_collections().collections]
    if settings.IMAGES_COLLECTION not in collections:
        logger.info("Creating Qdrant collection: %s", settings.IMAGES_COLLECTION)
        qdrant.create_collection(
            collection_name=settings.IMAGES_COLLECTION,
            vectors_config={
                "clip": qmodels.VectorParams(size=CLIP_DIM, distance=qmodels.Distance.COSINE),
                "ocr_text": qmodels.VectorParams(size=TEXT_DIM, distance=qmodels.Distance.COSINE),
            },
        )


ensure_collection()

app = FastAPI(title="Picture Indexing Service", version="1.0.0")


class ImageIndexResponse(BaseModel):
    id: str
    filename: str
    ocr_text: str
    image_path: str
    width: int
    height: int
    mime_type: str
    uploaded_at: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


async def _get_clip_embedding(image_b64: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.EMBEDDING_SERVER_URL}/embed/image",
            json={"images_base64": [image_b64]},
        )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


async def _get_text_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.EMBEDDING_SERVER_URL}/embed/text",
            json={"texts": [text if text.strip() else " "]},
        )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


@app.post("/index/image", response_model=ImageIndexResponse)
async def index_image(file: UploadFile = File(...)) -> ImageIndexResponse:
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        raise HTTPException(status_code=400, detail=f"Unsupported mime type: {file.content_type}")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    image_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1] or ".png"
    stored_filename = f"{image_id}{ext}"
    stored_path = os.path.join(settings.IMAGE_STORAGE_DIR, stored_filename)

    try:
        with open(stored_path, "wb") as f:
            f.write(raw_bytes)
        with Image.open(stored_path) as img:
            width, height = img.size
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}") from exc

    # OCR
    try:
        ocr_results = ocr_reader.readtext(stored_path, detail=0)
        ocr_text = " ".join(ocr_results).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed for %s: %s", stored_filename, exc)
        ocr_text = ""

    image_b64 = base64.b64encode(raw_bytes).decode("utf-8")

    try:
        clip_vector = await _get_clip_embedding(image_b64)
        ocr_vector = await _get_text_embedding(ocr_text)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Embedding server error: {exc}") from exc

    uploaded_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "filename": file.filename,
        "ocr_text": ocr_text,
        "image_path": stored_path,
        "uploaded_at": uploaded_at,
        "width": width,
        "height": height,
        "mime_type": file.content_type,
    }

    qdrant.upsert(
        collection_name=settings.IMAGES_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=image_id,
                vector={"clip": clip_vector, "ocr_text": ocr_vector},
                payload=payload,
            )
        ],
    )

    logger.info("Indexed image %s (%s)", image_id, file.filename)

    return ImageIndexResponse(
        id=image_id,
        filename=file.filename or stored_filename,
        ocr_text=ocr_text,
        image_path=stored_path,
        width=width,
        height=height,
        mime_type=file.content_type,
        uploaded_at=uploaded_at,
    )
