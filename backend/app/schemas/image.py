from datetime import datetime

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    image_id: str
    filename: str
    ocr_text: str
    width: int
    height: int
    mime_type: str
    uploaded_at: datetime


class ImageSearchRequest(BaseModel):
    query: str
    mode: str = "text"  # "text" (text->image) or "ocr" (ocr text search)
    top_k: int = 5


class ImageSearchResultItem(BaseModel):
    image_id: str
    filename: str
    ocr_text: str
    image_path: str
    score: float


class ImageSearchResponse(BaseModel):
    query: str
    results: list[ImageSearchResultItem]
