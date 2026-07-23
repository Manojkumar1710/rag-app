import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.image import ImageSearchRequest, ImageSearchResponse, ImageUploadResponse
from app.services.image_service import image_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/images", tags=["images"])

ALLOWED_MIME_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/webp")


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    try:
        return await image_service.upload_image(file.filename or "image", content, file.content_type)
    except RuntimeError as exc:
        logger.exception("Image upload unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Image upload failed")
        raise HTTPException(status_code=502, detail=f"Image indexing failed: {exc}") from exc


@router.post("/search", response_model=ImageSearchResponse)
async def search_images(request: ImageSearchRequest) -> ImageSearchResponse:
    try:
        results = await image_service.search_images(request.query, request.mode, request.top_k)
    except RuntimeError as exc:
        logger.exception("Image search unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Image search failed")
        raise HTTPException(status_code=500, detail=f"Image search failed: {exc}") from exc

    return ImageSearchResponse(query=request.query, results=results)
