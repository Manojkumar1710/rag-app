import { useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import type { SearchResultItem } from "../types/api";
import { search } from "../services/api";
import ErrorBanner from "../components/ErrorBanner";
import Spinner from "../components/Spinner";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await search(query, 8);
      setResults(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Semantic Search</h1>
      <p className="page-subtitle">Hybrid retrieval combining semantic similarity and keyword (BM25) relevance.</p>

      <ErrorBanner message={error} />

      <div className="card" style={{ display: "flex", gap: 10, marginBottom: 24 }}>
        <input
          type="text"
          style={{ flex: 1 }}
          placeholder="Search your indexed documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button className="btn" onClick={handleSearch} disabled={loading}>
          <SearchIcon size={16} />
        </button>
      </div>

      {loading && <Spinner label="Searching..." />}

      {!loading && results.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {results.map((r, i) => (
            <div key={i} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>{r.filename}{r.page ? ` (p.${r.page})` : ` #${r.chunk_number}`}</span>
                <div style={{ display: "flex", gap: 6 }}>
                  <span className="badge">combined {r.combined_score}</span>
                  <span className="badge">semantic {r.semantic_score}</span>
                  <span className="badge">keyword {r.keyword_score}</span>
                </div>
              </div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>{r.text}</div>
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="card" style={{ color: "var(--text-secondary)" }}>No results yet — try a search.</div>
      )}
    </div>
  );
}
