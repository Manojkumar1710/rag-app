# RAG Studio — Production-Quality Retrieval-Augmented Generation App

A fully containerized, multi-service RAG system: document and image ingestion, hybrid semantic+keyword search, multimodal (CLIP + OCR) image search, and a streaming chat interface grounded in your own data — built with FastAPI microservices, Qdrant, Ollama, and a React/Vite frontend.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────────────┐
│  Frontend   │─────▶│   Backend    │─────▶│   Embedding Server  │
│ React+Vite  │      │   FastAPI    │      │ (MiniLM + CLIP)     │
└─────────────┘      └──────┬───────┘      └────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌─────────────┐ ┌──────────────────┐ ┌─────────┐
       │   Qdrant    │ │ Indexing Service  │ │ Ollama  │
       │ Vector DB   │◀│ (EasyOCR + CLIP)  │ │  (LLM)  │
       └─────────────┘ └──────────────────┘ └─────────┘
```

| Service            | Tech                                      | Port  | Responsibility                                                       |
| ------------------ | ----------------------------------------- | ----- | -------------------------------------------------------------------- |
| `frontend`         | React, Vite, TypeScript, served via nginx | 5173  | UI: chat, uploads, search, explorer                                  |
| `backend`          | FastAPI, Python 3.11                      | 8000  | Orchestration: ingestion, chunking, RAG pipeline, hybrid search      |
| `embedding-server` | FastAPI, Sentence-Transformers, PyTorch   | 8001  | Text embeddings (MiniLM) + CLIP embeddings                           |
| `indexing-service` | FastAPI, EasyOCR                          | 8002  | Image upload, OCR, CLIP indexing into Qdrant                         |
| `qdrant`           | Qdrant                                    | 6333  | Vector storage for `documents` and `images` collections              |
| `ollama`           | Ollama                                    | 11435 | Local LLM inference (containerized), used when `LLM_PROVIDER=ollama` |

## Quick Start

```bash
git clone <this-repo>
cd rag-app
cp .env.example .env
# Set LLM_PROVIDER and, if using a hosted provider, GEMINI_API_KEY or OPENAI_API_KEY in .env
docker compose up --build
```

If you want the Images page to work, the image-indexing stack must also be up: `embedding-server`, `indexing-service`, and `qdrant`. The Docker Compose file already wires those services together. The image uploads inside the app are not Docker images; they are user-uploaded pictures that get OCR/CLIP indexed into Qdrant.

Once all health checks pass:

- Frontend: http://localhost:5173
- Backend docs (Swagger): http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

First build will take several minutes — model weights (MiniLM, CLIP, EasyOCR) are downloaded during the Docker build so containers start up quickly and don't need internet access at runtime.

## LLM Providers

The chat pipeline is provider-agnostic — anyone running this app can choose whichever LLM backend suits them, purely by setting `LLM_PROVIDER` in `.env` and rebuilding the backend (`docker compose up --build backend`). No code changes are needed to switch providers. Options:

- **`ollama`** (default for local dev) — uses the containerized `ollama` service, fully local and free, no API key required. **The Ollama model itself must be pulled separately** before chat will work, either:
  - Inside the container (downloads fresh, ~4-5GB for `qwen2.5-coder:7b`):
    ```bash
    docker exec -it rag-ollama ollama pull qwen2.5-coder:7b
    ```
  - Or, if you already have Ollama installed natively and don't want to download the model twice, bind-mount your existing native Ollama models folder instead of using the `ollama-data` named volume. In `docker-compose.yml`, under the `ollama` service, replace:
    ```yaml
    volumes:
      - ollama-data:/root/.ollama
    ```
    with your OS-specific native path, e.g. on Windows:
    ```yaml
    volumes:
      - C:/Users/<your-username>/.ollama:/root/.ollama
    ```
    **This path is machine-specific** — anyone cloning this repo needs to update it to their own native Ollama path (or just use the default named volume and pull the model fresh inside the container).
  - Verify the model is available with: `docker exec -it rag-ollama ollama list`
- **`gemini`** — uses Google's Gemini REST API (including SSE streaming). Requires `GEMINI_API_KEY` in `.env`. No local model or extra container needed.
- **`openai`** — uses OpenAI's Chat Completions API (including SSE streaming). Requires `OPENAI_API_KEY` in `.env`. No local model or extra container needed.
- **`mock`** — no API key or model needed; returns a deterministic placeholder answer built from retrieved context. Useful for exercising the full pipeline (upload → embed → search → chat → citations) with zero external cost or setup.

To switch providers, just change `LLM_PROVIDER` (and the matching API key, if applicable) in `.env`, then run `docker compose up --build backend`.

## API Reference

All endpoints are served by the `backend` service at `http://localhost:8000`.

| Method   | Path                       | Description                                                      |
| -------- | -------------------------- | ---------------------------------------------------------------- |
| `POST`   | `/api/v1/documents/upload` | Upload a PDF/TXT/MD file; parses, chunks, embeds, and indexes it |
| `GET`    | `/api/v1/documents`        | List all indexed documents with chunk counts                     |
| `DELETE` | `/api/v1/documents/{id}`   | Remove a document and all its chunks                             |
| `POST`   | `/api/v1/search`           | Hybrid (semantic + BM25 keyword) search over chunks              |
| `POST`   | `/api/v1/chat`             | RAG chat; set `"stream": true` for Server-Sent Events            |
| `POST`   | `/api/v1/images/upload`    | Upload an image for OCR + CLIP indexing                          |
| `POST`   | `/api/v1/images/search`    | Search images by text→image (CLIP) or OCR text                   |
| `GET`    | `/health`                  | Liveness check                                                   |

Interactive OpenAPI docs are available at `/docs` once the backend is running.

### Example: chat request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the document say about pricing?", "top_k": 5, "stream": false}'
```

## RAG Pipeline

1. **Upload**: document is parsed (PDF via `pypdf`, TXT/MD as plain text) and recursively split into overlapping chunks (paragraph → line → sentence → word fallback hierarchy).
2. **Embed**: each chunk is embedded via the embedding-server (`all-MiniLM-L6-v2`, 384-dim) and stored in the Qdrant `documents` collection alongside metadata (document id, filename, page, chunk number, upload date).
3. **Search**: a query is embedded and matched semantically in Qdrant; the top semantic candidates are then re-ranked with a BM25 keyword score computed in-process, and a weighted combination (`HYBRID_SEMANTIC_WEIGHT` / `HYBRID_KEYWORD_WEIGHT`) produces the final ranking.
4. **Chat**: the same hybrid search retrieves context for the user's question, which is assembled into a prompt and sent to the configured LLM provider (or the mock fallback — see LLM Providers above). If no relevant chunks are retrieved (e.g. an empty index, or a query with no meaningful match), the backend returns a fixed "I don't have any relevant documents to answer that" response **without calling the LLM**, so answers never fall back to the model's own general knowledge. The response and citations (source chunks) are returned to the frontend; streaming responses use Server-Sent Events.

## Image Pipeline

1. **Upload**: the backend forwards the image to the indexing-service.
2. **OCR**: EasyOCR extracts any readable text from the image.
3. **Embeddings**: a CLIP image embedding (512-dim) and an OCR-text embedding (384-dim) are generated and stored as **named vectors** on the same Qdrant point, alongside metadata (filename, OCR text, image path, dimensions, mime type, upload timestamp).
4. **Search**: text queries are embedded with CLIP's text tower for text→image semantic search, or with the MiniLM text model for OCR-text search — both query against the appropriate named vector in Qdrant.

## Remote Access (Tailscale Funnel)

To expose a locally-running instance to the internet (e.g. for a friend to test), this project has been run successfully behind [Tailscale Funnel](https://tailscale.com/kb/1223/funnel):

```bash
# Requires Funnel enabled for your tailnet (one-time setup via the Tailscale admin console)
tailscale funnel --bg --set-path=/ 5173
tailscale funnel --bg --set-path=/api 8000
```

This exposes frontend at the root path and backend under `/api` on the same public HTTPS hostname (e.g. `https://<device>.<tailnet>.ts.net`). When doing this:

- Set `VITE_BACKEND_URL` in `.env` to the public `/api` URL before building the frontend.
- Set `CORS_ORIGINS` in `.env` to the public frontend URL (root, no path) before building the backend.
- Rebuild `frontend` and `backend` after changing these (`docker compose up --build frontend backend`).
- Check current Funnel routes anytime with `tailscale funnel status`.

## Docker Hub Naming Plan

Use these names if you want to build, tag, and push the app services to your Docker Hub account `manoj701312`:

| Service          | Local Container Name   | Docker Hub Image Name                  |
| ---------------- | ---------------------- | -------------------------------------- |
| Backend          | `rag-backend`          | `manoj701312/rag-backend:1.0`          |
| Frontend         | `rag-frontend`         | `manoj701312/rag-frontend:1.0`         |
| Embedding server | `rag-embedding-server` | `manoj701312/rag-embedding-server:1.0` |
| Indexing service | `rag-indexing-service` | `manoj701312/rag-indexing-service:1.0` |
| Qdrant           | `rag-qdrant`           | `qdrant/qdrant:v1.11.3`                |
| Ollama           | `rag-ollama`           | `ollama/ollama:latest`                 |

Recommended commands:

```bash
docker build -t manoj701312/rag-backend:1.0 ./backend
docker build -t manoj701312/rag-embedding-server:1.0 ./embedding-server
docker build -t manoj701312/rag-indexing-service:1.0 ./indexing-service
docker build -t manoj701312/rag-frontend:1.0 ./frontend

docker push manoj701312/rag-backend:1.0
docker push manoj701312/rag-embedding-server:1.0
docker push manoj701312/rag-indexing-service:1.0
docker push manoj701312/rag-frontend:1.0
```

If you want a `latest` tag too, tag the same image again before pushing:

```bash
docker tag manoj701312/rag-backend:1.0 manoj701312/rag-backend:latest
docker tag manoj701312/rag-embedding-server:1.0 manoj701312/rag-embedding-server:latest
docker tag manoj701312/rag-indexing-service:1.0 manoj701312/rag-indexing-service:latest
docker tag manoj701312/rag-frontend:1.0 manoj701312/rag-frontend:latest
```

For local containers, use the same names shown above. That keeps the setup easy to remember and avoids naming conflicts.

## Environment Variables

See `.env.example` for the full list with defaults and inline documentation. Key variables:

| Variable                                                    | Description                                                                                                                   |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `LLM_PROVIDER`                                              | `ollama` \| `mock` \| `gemini` \| `openai`                                                                                    |
| `OLLAMA_MODEL`, `OLLAMA_BASE_URL`                           | Ollama model name and internal service URL                                                                                    |
| `GEMINI_API_KEY` / `OPENAI_API_KEY`                         | Provider credentials (only needed for the corresponding `LLM_PROVIDER`)                                                       |
| `QDRANT_URL`, `EMBEDDING_SERVER_URL`, `INDEXING_SERVER_URL` | Internal service URLs (Docker network)                                                                                        |
| `BACKEND_PORT`, `FRONTEND_PORT`                             | Host-exposed ports                                                                                                            |
| `VITE_BACKEND_URL`                                          | Backend URL baked into the frontend at build time — must be host-reachable (update and rebuild frontend if exposing remotely) |
| `CORS_ORIGINS`                                              | Comma-separated allowed frontend origins for the backend                                                                      |
| `CHUNK_SIZE`, `CHUNK_OVERLAP`                               | Chunking parameters                                                                                                           |
| `HYBRID_SEMANTIC_WEIGHT`, `HYBRID_KEYWORD_WEIGHT`           | Hybrid search weighting                                                                                                       |

## Project Structure

```
rag-app/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/            # config, logging
│   │   ├── routers/         # documents, search, chat, images
│   │   ├── services/        # qdrant, embedding client, llm, document, search, chat, image
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── utils/           # chunking, bm25, document_parser
│   └── Dockerfile
├── embedding-server/
│   ├── main.py
│   └── Dockerfile
├── indexing-service/
│   ├── main.py
│   ├── config.py
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── pages/            # Chat, Documents, Images, Search, Explorer
    │   ├── components/       # Sidebar, ErrorBanner, Spinner
    │   ├── services/api.ts   # backend HTTP client
    │   └── types/api.ts
    └── Dockerfile
```

## Development Notes

- All services validate input via Pydantic models and return structured HTTP error responses.
- No `print()` statements — every service uses Python's `logging` module.
- No hardcoded configuration — everything flows through environment variables with sensible defaults.
- Health checks are defined for every container so `depends_on: condition: service_healthy` gates startup ordering correctly.
- The mock LLM mode means the entire stack (upload → embed → search → chat → citations) can be exercised end-to-end with zero external API keys.
- The chat pipeline never lets the LLM answer without retrieved context — see the RAG Pipeline section above.
- The frontend layout is responsive: below 768px width, the sidebar collapses into a horizontal, icon-only scrollable nav bar so the app remains usable on phones.

## Stopping & Cleaning Up

```bash
docker compose down            # stop containers
docker compose down -v         # also remove volumes (Qdrant data, stored documents/images)
```
