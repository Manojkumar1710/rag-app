"""Hybrid (semantic + keyword) search over indexed document chunks."""
import logging

from app.core.config import settings
from app.schemas.search import SearchResultItem
from app.services.chroma_service import chroma_service
from app.services.embedding_client import embedding_client
from app.utils.bm25 import BM25, normalize_scores

logger = logging.getLogger(__name__)


class SearchService:
    async def hybrid_search(
        self, query: str, top_k: int = 5, filters: dict | None = None
    ) -> list[SearchResultItem]:
        query_vector = await embedding_client.embed_text(query)

        # Over-fetch on the semantic side so the keyword re-ranking has a
        # meaningful candidate pool to work with.
        candidate_k = max(top_k * 4, 20)
        semantic_hits = chroma_service.search_documents(query_vector, candidate_k, filters)

        if not semantic_hits:
            return []

        texts = [hit["payload"].get("text", "") for hit in semantic_hits]
        bm25 = BM25(texts)
        keyword_scores_raw = bm25.score_all(query)

        semantic_scores_raw = [hit["score"] for hit in semantic_hits]
        semantic_norm = normalize_scores(semantic_scores_raw)
        keyword_norm = normalize_scores(keyword_scores_raw)

        results: list[SearchResultItem] = []
        for hit, sem_n, kw_n, sem_raw, kw_raw in zip(
            semantic_hits, semantic_norm, keyword_norm, semantic_scores_raw, keyword_scores_raw
        ):
            combined = (
                settings.HYBRID_SEMANTIC_WEIGHT * sem_n
                + settings.HYBRID_KEYWORD_WEIGHT * kw_n
            )
            payload = hit["payload"] or {}
            results.append(
                SearchResultItem(
                    document_id=payload.get("document_id", ""),
                    filename=payload.get("filename", ""),
                    chunk_number=payload.get("chunk_number", 0),
                    page=payload.get("page"),
                    text=payload.get("text", ""),
                    semantic_score=round(sem_raw, 4),
                    keyword_score=round(kw_raw, 4),
                    combined_score=round(combined, 4),
                )
            )

        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results[:top_k]


search_service = SearchService()