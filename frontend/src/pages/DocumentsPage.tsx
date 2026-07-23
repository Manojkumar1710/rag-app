import { useEffect, useState } from "react";
import { Trash2, UploadCloud } from "lucide-react";
import type { DocumentSummary } from "../types/api";
import { deleteDocument, listDocuments, uploadDocumentsBatch, type BatchUploadItemResult } from "../services/api";
import ErrorBanner from "../components/ErrorBanner";
import Spinner from "../components/Spinner";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [batchResults, setBatchResults] = useState<BatchUploadItemResult[]>([]);

  async function refresh() {
    setLoading(true);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length === 0) return;
    setError("");
    setBatchResults([]);
    setUploading(true);
    try {
      const result = await uploadDocumentsBatch(files);
      setBatchResults(result.results);
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.document_id !== id));
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Delete failed.");
    }
  }

  return (
    <div>
      <h1 className="page-title">Documents</h1>
      <p className="page-subtitle">Upload up to 20 PDF, TXT, or Markdown files at once to index for chat and search.</p>

      <ErrorBanner message={error} />

      <label className="card" style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer", marginBottom: 24, justifyContent: "center", padding: 32, border: "1px dashed var(--border)" }}>
        <UploadCloud size={20} color="var(--accent)" />
        <span>{uploading ? "Uploading & indexing..." : "Click to upload documents (.pdf, .txt, .md) — select multiple"}</span>
        <input type="file" accept=".pdf,.txt,.md" multiple hidden onChange={handleFileChange} disabled={uploading} />
      </label>

      {batchResults.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            Batch result: {batchResults.filter((r) => r.success).length} / {batchResults.length} succeeded
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {batchResults.map((r, i) => (
              <div key={i} style={{ fontSize: 13, color: r.success ? "var(--success)" : "var(--danger)" }}>
                {r.success ? "✓" : "✗"} {r.filename} {r.success ? `(${r.chunk_count} chunks)` : `— ${r.error}`}
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <Spinner label="Loading documents..." />
      ) : documents.length === 0 ? (
        <div className="card" style={{ color: "var(--text-secondary)" }}>No documents indexed yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {documents.map((doc) => (
            <div key={doc.document_id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{doc.filename}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {doc.chunk_count} chunks · {doc.file_type.toUpperCase()} · {new Date(doc.upload_date).toLocaleString()}
                </div>
              </div>
              <button className="btn btn-secondary" onClick={() => handleDelete(doc.document_id)}>
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}