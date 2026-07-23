from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = Field(default=False)


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_number: int
    page: int | None = None
    snippet: str
    score: float


class ChatResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    answer: str
    citations: list[Citation]
    model_used: str
