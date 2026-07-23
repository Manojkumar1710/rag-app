"""Pydantic schemas for document upload/listing/deletion."""
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentChunkMetadata(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    chunk_number: int
    upload_date: datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    upload_date: datetime
    message: str = "Document uploaded and indexed successfully."


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    upload_date: datetime
    file_type: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int


class BatchUploadItemResult(BaseModel):
    filename: str
    success: bool
    document_id: str | None = None
    chunk_count: int | None = None
    error: str | None = None


class BatchUploadResponse(BaseModel):
    total_files: int
    successful: int
    failed: int
    results: list[BatchUploadItemResult]


class DeleteResponse(BaseModel):
    document_id: str
    deleted_chunks: int
    message: str = "Document deleted successfully."


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human readable error message")