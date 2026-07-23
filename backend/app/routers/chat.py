import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("")
async def chat(request: ChatRequest):
    if request.stream:
        return await _stream_chat(request)

    try:
        answer, citations, model_used = await chat_service.answer(
            request.message, top_k=request.top_k
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    return ChatResponse(answer=answer, citations=citations, model_used=model_used)


async def _stream_chat(request: ChatRequest) -> StreamingResponse:
    async def event_generator():
        try:
            async for piece in chat_service.answer_stream(request.message, top_k=request.top_k):
                yield f"data: {piece}\n\n"

            citations = await chat_service.retrieve_citations(request.message, top_k=request.top_k)
            import json

            citations_payload = json.dumps([c.model_dump() for c in citations])
            yield f"event: citations\ndata: {citations_payload}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed")
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
