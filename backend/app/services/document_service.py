"""Document ingestion: parse -> chunk -> embed -> store."""
import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.document import DocumentSummary, DocumentUploadResponse
from app.services.chroma_service import chroma_service
from app.services.embedding_client import embedding_client
from app.utils.chunking import recursive_chunk_text
from app.utils.document_parser import extract_text_with_pages

logger = logging.getLogger(__name__)


class DocumentService:
    async def ingest(self, filename: str, content: bytes) -> DocumentUploadResponse:
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        pages = extract_text_with_pages(filename, content)

        if not pages:
            raise ValueError("No extractable text found in document.")

        document_id = str(uuid.uuid4())
        upload_date = datetime.now(timezone.utc).isoformat()

        all_chunks: list[str] = []
        all_pages: list[int | None] = []

        for page_number, page_text in pages:
            chunks = recursive_chunk_text(
                page_text,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            all_chunks.extend(chunks)
            all_pages.extend([page_number] * len(chunks))

        if not all_chunks:
            raise ValueError("Document produced no chunks after splitting.")

        vectors = await embedding_client.embed_texts(all_chunks)

        chroma_service.upsert_chunks(
            document_id=document_id,
            filename=filename,
            file_type=file_type,
            chunks=all_chunks,
            vectors=vectors,
            pages=all_pages,
            upload_date=upload_date,
        )

        logger.info("Ingested document %s (%s) with %d chunks", document_id, filename, len(all_chunks))

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            chunk_count=len(all_chunks),
            upload_date=datetime.fromisoformat(upload_date),
        )

    async def ingest_batch(
        self, files: list[tuple[str, bytes]]
    ) -> list[dict]:
        """Ingest multiple documents sequentially. Returns a list of result
        dicts (one per file) so a partial failure in one file doesn't abort
        the rest of the batch."""
        results: list[dict] = []
        for filename, content in files:
            try:
                result = await self.ingest(filename, content)
                results.append(
                    {
                        "filename": filename,
                        "success": True,
                        "document_id": result.document_id,
                        "chunk_count": result.chunk_count,
                        "error": None,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to ingest %s in batch: %s", filename, exc)
                results.append(
                    {
                        "filename": filename,
                        "success": False,
                        "document_id": None,
                        "chunk_count": None,
                        "error": str(exc),
                    }
                )
        return results

    def list_documents(self) -> list[DocumentSummary]:
        docs = chroma_service.list_documents()
        return [
            DocumentSummary(
                document_id=d["document_id"],
                filename=d["filename"] or "unknown",
                chunk_count=d["chunk_count"],
                upload_date=datetime.fromisoformat(d["upload_date"]) if d["upload_date"] else datetime.now(timezone.utc),
                file_type=d["file_type"] or "unknown",
            )
            for d in docs
        ]

    def delete_document(self, document_id: str) -> int:
        return chroma_service.delete_document(document_id)


document_service = DocumentService()