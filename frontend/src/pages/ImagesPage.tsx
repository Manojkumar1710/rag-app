import { useState } from "react";
import { UploadCloud, Search as SearchIcon } from "lucide-react";
import type { ImageSearchResultItem } from "../types/api";
import { searchImages, uploadImage } from "../services/api";
import ErrorBanner from "../components/ErrorBanner";
import Spinner from "../components/Spinner";

export default function ImagesPage() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"text" | "ocr">("text");
  const [results, setResults] = useState<ImageSearchResultItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [lastUploaded, setLastUploaded] = useState<string | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      await uploadImage(file);
      setLastUploaded(file.name);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Image upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const res = await searchImages(query, mode);
      setResults(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Image search failed.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Image Upload &amp; Search</h1>
      <p className="page-subtitle">Upload images for OCR + CLIP indexing, then search by text, semantics, or extracted text.</p>

      <ErrorBanner message={error} />

      <label className="card" style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer", marginBottom: 24, justifyContent: "center", padding: 32, border: "1px dashed var(--border)" }}>
        <UploadCloud size={20} color="var(--accent)" />
        <span>{uploading ? "Uploading & indexing image..." : "Click to upload an image (.png, .jpg, .webp)"}</span>
        <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={handleFileChange} disabled={uploading} />
      </label>
      {lastUploaded && <div style={{ fontSize: 12, color: "var(--success)", marginBottom: 16 }}>Indexed: {lastUploaded}</div>}

      <div className="card" style={{ display: "flex", gap: 10, marginBottom: 24 }}>
        <input
          type="text"
          style={{ flex: 1 }}
          placeholder="Search images by description or OCR text..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "text" | "ocr")}
          style={{ background: "var(--bg-elevated)", color: "var(--text-primary)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "0 10px" }}
        >
          <option value="text">Text → Image (CLIP)</option>
          <option value="ocr">OCR Text Search</option>
        </select>
        <button className="btn" onClick={handleSearch} disabled={searching}>
          <SearchIcon size={16} />
        </button>
      </div>

      {searching && <Spinner label="Searching images..." />}

      {!searching && results.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 16 }}>
          {results.map((r) => (
            <div key={r.image_id} className="card">
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.filename}
              </div>
              <div className="badge" style={{ marginBottom: 6 }}>score {r.score}</div>
              {r.ocr_text && (
                <div style={{ fontSize: 12, color: "var(--text-secondary)", maxHeight: 60, overflow: "hidden" }}>
                  {r.ocr_text}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
