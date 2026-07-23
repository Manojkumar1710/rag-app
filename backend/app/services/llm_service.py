"""LLM orchestration: builds the RAG prompt and calls the configured provider.

Supports Ollama, Gemini, OpenAI, and a deterministic mock fallback (used when
no API key is configured, e.g. in local dev/CI), so the rest of the system
stays fully testable without external API access.
"""
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using ONLY the provided "
    "context. If the context does not contain the answer, say you don't know. "
    "Write in a clean, modern assistant style. Default structure: 1) short direct "
    "answer first, 2) then bullets or numbered steps on separate lines, 3) code "
    "on its own line in fenced code blocks. If the user asks for commands, show "
    "one command per line with a short explanation beneath it. If the user asks "
    "for the full information, give a fuller answer with clear sections. Avoid "
    "giant paragraphs, avoid stuffing multiple commands on the same line, and "
    "never use tables unless they are clearly better than bullets. Always cite "
    "which source(s) you used by their [number]."
)


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context_block = "\n\n".join(
        f"[{i + 1}] {chunk}" for i, chunk in enumerate(context_chunks)
    )
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Formatting rules:\n"
        f"- Put each new point on its own line.\n"
        f"- Use blank lines between sections.\n"
        f"- Use fenced code blocks for commands and code.\n"
        f"- For step-by-step requests, prefer numbered lists.\n"
        f"- For detailed/full-information requests, use short section headings.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )


class LLMService:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER

    async def generate(self, question: str, context_chunks: list[str]) -> tuple[str, str]:
        """Returns (answer_text, model_used)."""
        prompt = build_prompt(question, context_chunks)

        if self.provider == "ollama":
            return await self._call_ollama(prompt), settings.OLLAMA_MODEL
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            return await self._call_gemini(prompt), settings.GEMINI_MODEL
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            return await self._call_openai(prompt), settings.OPENAI_MODEL

        logger.warning(
            "No real LLM provider configured (provider=%s) - using mock LLM.", self.provider
        )
        return self._mock_answer(question, context_chunks), "mock-llm"

    async def generate_stream(
        self, question: str, context_chunks: list[str]
    ) -> AsyncIterator[str]:
        """Yields answer text incrementally. Falls back to mock streaming if needed."""
        if self.provider == "ollama":
            async for piece in self._stream_ollama(build_prompt(question, context_chunks)):
                yield piece
            return
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            async for piece in self._stream_gemini(build_prompt(question, context_chunks)):
                yield piece
            return
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            async for piece in self._stream_openai(build_prompt(question, context_chunks)):
                yield piece
            return

        answer = self._mock_answer(question, context_chunks)
        for word in answer.split(" "):
            yield word + " "

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        body = {
            "model": settings.OLLAMA_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            logger.error("Unexpected Ollama response shape: %s", data)
            raise RuntimeError("Ollama returned an unexpected response") from exc

    async def _stream_ollama(self, prompt: str) -> AsyncIterator[str]:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        body = {
            "model": settings.OLLAMA_MODEL,
            "stream": True,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    import json as _json

                    try:
                        chunk = _json.loads(line)
                    except ValueError:
                        continue
                    content = chunk.get("message", {}).get("content")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break

    # ------------------------------ Gemini ------------------------------ #
    async def _call_gemini(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini response shape: %s", data)
            raise RuntimeError("Gemini returned an unexpected response") from exc

    async def _stream_gemini(self, prompt: str) -> AsyncIterator[str]:
        # The Gemini REST streaming endpoint uses streamGenerateContent with SSE-like chunks.
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:streamGenerateContent?key={settings.GEMINI_API_KEY}&alt=sse"
        )
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    import json as _json

                    payload = line[len("data:"):].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        chunk = _json.loads(payload)
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                        yield text
                    except (KeyError, IndexError, ValueError):
                        continue

    # ------------------------------ OpenAI ------------------------------ #
    async def _call_openai(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        body = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def _stream_openai(self, prompt: str) -> AsyncIterator[str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        body = {
            "model": settings.OPENAI_MODEL,
            "stream": True,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    import json as _json

                    payload = line[len("data:"):].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        chunk = _json.loads(payload)
                        delta = chunk["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (KeyError, IndexError, ValueError):
                        continue

    # ------------------------------- Mock -------------------------------- #
    @staticmethod
    def _mock_answer(question: str, context_chunks: list[str]) -> str:
        if not context_chunks:
            return (
                "I don't have any indexed documents relevant to that question yet. "
                "Try uploading some documents first."
            )
        preview = context_chunks[0][:300]
        return (
            f"[Mock LLM - no API key configured] Based on the retrieved context, "
            f"here is a relevant excerpt related to your question \"{question}\": "
            f"\"{preview}...\" Configure GEMINI_API_KEY or OPENAI_API_KEY for real answers."
        )


llm_service = LLMService()
