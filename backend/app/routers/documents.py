import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.document import (
    BatchUploadItemResult,
    BatchUploadResponse,
    DeleteResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.document_service import document_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_BATCH_FILES = 20


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25MB).")

    try:
        result = await document_service.ingest(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return result


@router.post("/upload-batch", response_model=BatchUploadResponse)
async def upload_documents_batch(files: list[UploadFile] = File(...)) -> BatchUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_BATCH_FILES} files per batch upload.",
        )

    payloads: list[tuple[str, bytes]] = []
    pre_validation_results: list[BatchUploadItemResult] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
            pre_validation_results.append(
                BatchUploadItemResult(
                    filename=file.filename or "unknown",
                    success=False,
                    error=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
                )
            )
            continue

        content = await file.read()
        if not content:
            pre_validation_results.append(
                BatchUploadItemResult(filename=file.filename, success=False, error="File is empty.")
            )
            continue
        if len(content) > MAX_FILE_SIZE_BYTES:
            pre_validation_results.append(
                BatchUploadItemResult(filename=file.filename, success=False, error="File too large (max 25MB).")
            )
            continue

        payloads.append((file.filename, content))

    ingest_results = await document_service.ingest_batch(payloads)

    all_results = pre_validation_results + [BatchUploadItemResult(**r) for r in ingest_results]
    successful = sum(1 for r in all_results if r.success)

    logger.info(
        "Batch upload: %d total, %d successful, %d failed",
        len(files), successful, len(all_results) - successful,
    )

    return BatchUploadResponse(
        total_files=len(files),
        successful=successful,
        failed=len(all_results) - successful,
        results=all_results,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    docs = document_service.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str) -> DeleteResponse:
    deleted = document_service.delete_document(document_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DeleteResponse(document_id=document_id, deleted_chunks=deleted)