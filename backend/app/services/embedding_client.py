"""HTTP client for the embedding-server microservice with a local fallback."""
import logging
from functools import lru_cache

import httpx
from httpx import ConnectError, ConnectTimeout, ReadTimeout, RemoteProtocolError

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self) -> None:
        self.base_url = settings.EMBEDDING_SERVER_URL

    async def _post_json(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            data = await self._post_json("/embed/text", {"texts": texts})
            return data["embeddings"]
        except (ConnectError, ConnectTimeout, ReadTimeout, RemoteProtocolError):
            logger.warning("Embedding server unavailable at %s; using local fallback.", self.base_url)
            return await _local_embedding_client.embed_texts(texts)

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]

    async def embed_clip_text(self, text: str) -> list[float]:
        try:
            data = await self._post_json("/embed/clip-text", {"texts": [text]})
            return data["embeddings"][0]
        except (ConnectError, ConnectTimeout, ReadTimeout, RemoteProtocolError):
            logger.warning("Embedding server unavailable at %s; using local fallback.", self.base_url)
            return (await _local_embedding_client.embed_clip_texts([text]))[0]


class _LocalEmbeddingClient:
    def __init__(self) -> None:
        self._text_model = None
        self._clip_model = None

    def _get_text_model(self):
        if self._text_model is None:
            from sentence_transformers import SentenceTransformer

            self._text_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._text_model

    def _get_clip_model(self):
        if self._clip_model is None:
            from sentence_transformers import SentenceTransformer

            self._clip_model = SentenceTransformer("sentence-transformers/clip-ViT-B-32")
        return self._clip_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_text_model()
        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    async def embed_clip_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_clip_model()
        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


embedding_client = EmbeddingClient()
_local_embedding_client = _LocalEmbeddingClient()
