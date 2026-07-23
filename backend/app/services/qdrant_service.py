"""Wrapper around the Qdrant client: collection management and CRUD for both
the `documents` and `images` collections."""
import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self._ready = False

    def _require_ready(self) -> None:
        if not self._ready:
            self._ensure_collections()

    def _ensure_collections(self) -> None:
        try:
            existing = {c.name for c in self.client.get_collections().collections}
        except Exception as exc:  # noqa: BLE001
            self._ready = False
            raise RuntimeError(f"Qdrant unavailable at {settings.QDRANT_URL}") from exc

        if settings.DOCUMENTS_COLLECTION not in existing:
            logger.info("Creating Qdrant collection: %s", settings.DOCUMENTS_COLLECTION)
            self.client.create_collection(
                collection_name=settings.DOCUMENTS_COLLECTION,
                vectors_config=qmodels.VectorParams(
                    size=settings.TEXT_VECTOR_DIM, distance=qmodels.Distance.COSINE
                ),
            )

        if settings.IMAGES_COLLECTION not in existing:
            logger.info("Creating Qdrant collection: %s", settings.IMAGES_COLLECTION)
            self.client.create_collection(
                collection_name=settings.IMAGES_COLLECTION,
                vectors_config={
                    "clip": qmodels.VectorParams(size=512, distance=qmodels.Distance.COSINE),
                    "ocr_text": qmodels.VectorParams(
                        size=settings.TEXT_VECTOR_DIM, distance=qmodels.Distance.COSINE
                    ),
                },
            )

        self._ready = True

    # ----------------------------- Documents ----------------------------- #
    def upsert_chunks(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        chunks: list[str],
        vectors: list[list[float]],
        pages: list[int | None],
        upload_date: str,
    ) -> None:
        self._require_ready()
        points = []
        for i, (chunk, vector, page) in enumerate(zip(chunks, vectors, pages)):
            points.append(
                qmodels.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_number": i,
                        "page": page,
                        "text": chunk,
                        "upload_date": upload_date,
                    },
                )
            )
        self.client.upsert(collection_name=settings.DOCUMENTS_COLLECTION, points=points)

    def search_documents(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[qmodels.ScoredPoint]:
        self._require_ready()
        qfilter = self._build_filter(filters) if filters else None
        return self.client.search(
            collection_name=settings.DOCUMENTS_COLLECTION,
            query_vector=vector,
            limit=top_k,
            query_filter=qfilter,
            with_payload=True,
        )

    def scroll_all_chunks(self, limit: int = 10000) -> list[qmodels.Record]:
        self._require_ready()
        records, _ = self.client.scroll(
            collection_name=settings.DOCUMENTS_COLLECTION,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return records

    def list_documents(self) -> list[dict]:
        records = self.scroll_all_chunks()
        docs: dict[str, dict] = {}
        for r in records:
            payload = r.payload or {}
            doc_id = payload.get("document_id")
            if not doc_id:
                continue
            if doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "filename": payload.get("filename"),
                    "upload_date": payload.get("upload_date"),
                    "file_type": payload.get("file_type"),
                    "chunk_count": 0,
                }
            docs[doc_id]["chunk_count"] += 1
        return list(docs.values())

    def delete_document(self, document_id: str) -> int:
        self._require_ready()
        records = self.scroll_all_chunks()
        ids_to_delete = [
            r.id for r in records if (r.payload or {}).get("document_id") == document_id
        ]
        if ids_to_delete:
            self.client.delete(
                collection_name=settings.DOCUMENTS_COLLECTION,
                points_selector=qmodels.PointIdsList(points=ids_to_delete),
            )
        return len(ids_to_delete)

    # ------------------------------- Images ------------------------------- #
    def search_images(
        self, vector: list[float], using: str, top_k: int
    ) -> list[qmodels.ScoredPoint]:
        self._require_ready()
        return self.client.search(
            collection_name=settings.IMAGES_COLLECTION,
            query_vector=qmodels.NamedVector(name=using, vector=vector),
            limit=top_k,
            with_payload=True,
        )

    @staticmethod
    def _build_filter(filters: dict) -> qmodels.Filter:
        conditions = [
            qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v))
            for k, v in filters.items()
        ]
        return qmodels.Filter(must=conditions)


qdrant_service = QdrantService()
