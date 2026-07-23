import axios from "axios";
import type {
  ChatMessage,
  Citation,
  DocumentSummary,
  ImageSearchResultItem,
  SearchResultItem,
} from "../types/api";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 60000,
});

// ----------------------------- Documents ----------------------------- //
export async function uploadDocument(file: File): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);
  await api.post("/api/v1/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export interface BatchUploadItemResult {
  filename: string;
  success: boolean;
  document_id?: string;
  chunk_count?: number;
  error?: string;
}

export interface BatchUploadResponse {
  total_files: number;
  successful: number;
  failed: number;
  results: BatchUploadItemResult[];
}

export async function uploadDocumentsBatch(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const { data } = await api.post("/api/v1/documents/upload-batch", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const { data } = await api.get("/api/v1/documents");
  return data.documents;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/api/v1/documents/${documentId}`);
}

// ------------------------------- Search -------------------------------- //
export async function search(query: string, topK = 5): Promise<SearchResultItem[]> {
  const { data } = await api.post("/api/v1/search", { query, top_k: topK });
  return data.results;
}

// -------------------------------- Chat ---------------------------------- //
export async function sendChatMessage(
  message: string,
  history: ChatMessage[]
): Promise<{ answer: string; citations: Citation[]; model_used: string }> {
  const { data } = await api.post("/api/v1/chat", {
    message,
    history: history.map((h) => ({ role: h.role, content: h.content })),
    stream: false,
  });
  return data;
}

/** Streams chat tokens via SSE. Calls onToken for each chunk and onDone with citations at the end. */
export async function streamChatMessage(
  message: string,
  onToken: (token: string) => void,
  onDone: (citations: Citation[]) => void,
  onError: (err: string) => void
): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history: [], stream: true }),
  });

  if (!response.body) {
    onError("No response stream available.");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const evt of events) {
      if (evt.startsWith("event: citations")) {
        const dataLine = evt.split("\n").find((l) => l.startsWith("data:"));
        if (dataLine) {
          try {
            const citations = JSON.parse(dataLine.replace("data:", "").trim());
            onDone(citations);
          } catch {
            onDone([]);
          }
        }
      } else if (evt.startsWith("event: error")) {
        const dataLine = evt.split("\n").find((l) => l.startsWith("data:"));
        onError(dataLine ? dataLine.replace("data:", "").trim() : "Unknown error");
      } else if (evt.startsWith("data:")) {
        onToken(evt.replace("data:", ""));
      }
    }
  }
}

// ------------------------------- Images --------------------------------- //
export async function uploadImage(file: File): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);
  await api.post("/api/v1/images/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export async function searchImages(
  query: string,
  mode: "text" | "ocr" = "text",
  topK = 8
): Promise<ImageSearchResultItem[]> {
  const { data } = await api.post("/api/v1/images/search", { query, mode, top_k: topK });
  return data.results;
}