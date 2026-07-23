import { useEffect, useState } from "react";
import type { DocumentSummary } from "../types/api";
import { listDocuments } from "../services/api";
import ErrorBanner from "../components/ErrorBanner";
import Spinner from "../components/Spinner";

export default function ExplorerPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load index."))
      .finally(() => setLoading(false));
  }, []);

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <div>
      <h1 className="page-title">Indexed Documents Explorer</h1>
      <p className="page-subtitle">A live view of everything currently stored in the vector database.</p>

      <ErrorBanner message={error} />

      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Total Documents</div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{documents.length}</div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Total Chunks</div>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{totalChunks}</div>
        </div>
      </div>

      {loading ? (
        <Spinner label="Loading index..." />
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-secondary)", fontSize: 12 }}>
              <th style={{ padding: "8px 12px" }}>Filename</th>
              <th style={{ padding: "8px 12px" }}>Type</th>
              <th style={{ padding: "8px 12px" }}>Chunks</th>
              <th style={{ padding: "8px 12px" }}>Uploaded</th>
              <th style={{ padding: "8px 12px" }}>Document ID</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.document_id} className="card" style={{ display: "table-row" }}>
                <td style={{ padding: "10px 12px", fontWeight: 600 }}>{d.filename}</td>
                <td style={{ padding: "10px 12px" }}>{d.file_type.toUpperCase()}</td>
                <td style={{ padding: "10px 12px" }}>{d.chunk_count}</td>
                <td style={{ padding: "10px 12px" }}>{new Date(d.upload_date).toLocaleString()}</td>
                <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>{d.document_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
