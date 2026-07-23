from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict | None = Field(default=None, description="Optional metadata filters")


class SearchResultItem(BaseModel):
    document_id: str
    filename: str
    chunk_number: int
    page: int | None = None
    text: str
    semantic_score: float
    keyword_score: float
    combined_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_results: int
