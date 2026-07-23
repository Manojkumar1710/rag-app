"""Wrapper around ChromaDB PersistentClient: collection management and CRUD
for the document chunk store. This replaces the previous Qdrant-based
service. The Qdrant "images" collection logic is intentionally NOT
reproduced here -- the image pipeline continues to use Qdrant unchanged."""
import logging
import uuid

from chromadb import PersistentClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaService:
    def __init__(self) -> None:
        self.client = PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            collection = self.client.get_collection(settings.DOCUMENTS_COLLECTION)
            logger.info("Loaded existing Chroma collection: %s", settings.DOCUMENTS_COLLECTION)
        except Exception:
            logger.info("Creating new Chroma collection: %s", settings.DOCUMENTS_COLLECTION)
            collection = self.client.create_collection(
                settings.DOCUMENTS_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        return collection

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
        if not chunks:
            return

        ids: list[str] = []
        metadatas: list[dict] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []

        for i, (chunk, vector, page) in enumerate(zip(chunks, vectors, pages)):
            ids.append(str(uuid.uuid4()))
            documents.append(chunk)
            embeddings.append(vector)
            metadatas.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_number": i,
                    "page": page if page is not None else -1,
                    "text": chunk,
                    "upload_date": upload_date,
                }
            )

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Upserted %d chunks for document %s into Chroma", len(ids), document_id)

    def search_documents(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[dict]:
        where = self._build_where(filters) if filters else None

        result = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            # Chroma returns a cosine distance (0 = identical, 2 = opposite).
            # Convert to a similarity score comparable to Qdrant's cosine
            # similarity score (higher is better, range roughly 0..1).
            score = 1.0 - (distance / 2.0)
            payload = dict(metadata) if metadata else {}
            if payload.get("page") == -1:
                payload["page"] = None
            payload["text"] = payload.get("text", document)
            hits.append(
                {
                    "id": doc_id,
                    "score": score,
                    "payload": payload,
                }
            )

        return hits

    def scroll_all_chunks(self, limit: int = 10000) -> list[dict]:
        result = self.collection.get(
            limit=limit,
            include=["documents", "metadatas"],
        )

        records: list[dict] = []
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        for doc_id, document, metadata in zip(ids, documents, metadatas):
            payload = dict(metadata) if metadata else {}
            if payload.get("page") == -1:
                payload["page"] = None
            payload["text"] = payload.get("text", document)
            records.append({"id": doc_id, "payload": payload})

        return records

    def list_documents(self) -> list[dict]:
        records = self.scroll_all_chunks()
        docs: dict[str, dict] = {}
        for r in records:
            payload = r["payload"] or {}
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
        records = self.scroll_all_chunks()
        ids_to_delete = [
            r["id"] for r in records if (r["payload"] or {}).get("document_id") == document_id
        ]
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    @staticmethod
    def _build_where(filters: dict) -> dict:
        if len(filters) == 1:
            key, value = next(iter(filters.items()))
            return {key: {"$eq": value}}
        return {"$and": [{k: {"$eq": v}} for k, v in filters.items()]}


chroma_service = ChromaService()