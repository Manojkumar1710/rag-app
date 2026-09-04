"""RAG chat pipeline: embed question -> retrieve context -> build prompt -> call LLM."""
import logging
from collections.abc import AsyncIterator

from app.schemas.chat import Citation
from app.services.llm_service import llm_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


class ChatService:
    async def answer(self, question: str, top_k: int = 5) -> tuple[str, list[Citation], str]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        context_chunks = [r.text for r in results]

        answer_text, model_used = await llm_service.generate(question, context_chunks)

        citations = [
            Citation(
                document_id=r.document_id,
                filename=r.filename,
                chunk_number=r.chunk_number,
                page=r.page,
                snippet=r.text[:200],
                score=r.combined_score,
            )
            for r in results
        ]
        return answer_text, citations, model_used

    async def answer_stream(self, question: str, top_k: int = 5) -> AsyncIterator[str]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        context_chunks = [r.text for r in results]
        async for piece in llm_service.generate_stream(question, context_chunks):
            yield piece

    async def retrieve_citations(self, question: str, top_k: int = 5) -> list[Citation]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        return [
            Citation(
                document_id=r.document_id,
                filename=r.filename,
                chunk_number=r.chunk_number,
                page=r.page,
                snippet=r.text[:200],
                score=r.combined_score,
            )
            for r in results
        ]


chat_service = ChatService()
"""RAG chat pipeline: embed question -> retrieve context -> build prompt -> call LLM."""
import logging
from collections.abc import AsyncIterator

from app.schemas.chat import Citation
from app.services.llm_service import llm_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

NO_CONTEXT_MESSAGE = (
    "I don't have any relevant documents to answer that. "
    "Try uploading a document first, or rephrase your question."
)


class ChatService:
    async def answer(self, question: str, top_k: int = 5) -> tuple[str, list[Citation], str]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        context_chunks = [r.text for r in results]

        if not context_chunks:
            logger.info("No relevant context found for question: %s", question)
            return NO_CONTEXT_MESSAGE, [], "none"

        answer_text, model_used = await llm_service.generate(question, context_chunks)

        citations = [
            Citation(
                document_id=r.document_id,
                filename=r.filename,
                chunk_number=r.chunk_number,
                page=r.page,
                snippet=r.text[:200],
                score=r.combined_score,
            )
            for r in results
        ]
        return answer_text, citations, model_used

    async def answer_stream(self, question: str, top_k: int = 5) -> AsyncIterator[str]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        context_chunks = [r.text for r in results]

        if not context_chunks:
            logger.info("No relevant context found for question: %s", question)
            yield NO_CONTEXT_MESSAGE
            return

        async for piece in llm_service.generate_stream(question, context_chunks):
            yield piece

    async def retrieve_citations(self, question: str, top_k: int = 5) -> list[Citation]:
        results = await search_service.hybrid_search(question, top_k=top_k)
        return [
            Citation(
                document_id=r.document_id,
                filename=r.filename,
                chunk_number=r.chunk_number,
                page=r.page,
                snippet=r.text[:200],
                score=r.combined_score,
            )
            for r in results
        ]


chat_service = ChatService()