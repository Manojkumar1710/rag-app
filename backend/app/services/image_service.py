"""Image upload (delegates OCR/embedding/storage to the indexing-service) and
image search (CLIP text->image, and OCR-text search) against Qdrant."""
import logging

import httpx

from app.core.config import settings
from app.schemas.image import ImageSearchResultItem, ImageUploadResponse
from app.services.embedding_client import embedding_client
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


class ImageService:
    async def upload_image(self, filename: str, content: bytes, content_type: str) -> ImageUploadResponse:
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (filename, content, content_type)}
            resp = await client.post(f"{settings.INDEXING_SERVER_URL}/index/image", files=files)
        resp.raise_for_status()
        data = resp.json()
        return ImageUploadResponse(
            image_id=data["id"],
            filename=data["filename"],
            ocr_text=data["ocr_text"],
            width=data["width"],
            height=data["height"],
            mime_type=data["mime_type"],
            uploaded_at=data["uploaded_at"],
        )

    async def search_images(
        self, query: str, mode: str, top_k: int
    ) -> list[ImageSearchResultItem]:
        if mode == "ocr":
            vector = await embedding_client.embed_text(query)
            using = "ocr_text"
        else:
            # text -> image search uses the CLIP text tower so the query lands
            # in the same embedding space as the indexed CLIP image vectors.
            vector = await embedding_client.embed_clip_text(query)
            using = "clip"

        hits = qdrant_service.search_images(vector, using=using, top_k=top_k)

        return [
            ImageSearchResultItem(
                image_id=str(hit.id),
                filename=(hit.payload or {}).get("filename", ""),
                ocr_text=(hit.payload or {}).get("ocr_text", ""),
                image_path=(hit.payload or {}).get("image_path", ""),
                score=round(hit.score, 4),
            )
            for hit in hits
        ]


image_service = ImageService()
