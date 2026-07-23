import logging

from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import search_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    try:
        results = await search_service.hybrid_search(
            query=request.query, top_k=request.top_k, filters=request.filters
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    return SearchResponse(query=request.query, results=results, total_results=len(results))
