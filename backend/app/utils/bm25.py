"""Lightweight BM25 implementation used for the keyword half of hybrid search.

Qdrant handles vector (semantic) search; for the keyword component we score
candidate chunks (already retrieved via semantic search, or all chunks for a
small corpus) using BM25 over a simple whitespace/punctuation tokenizer. This
avoids needing a separate full-text search engine for a portfolio-scale app.
"""
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.tokenized_docs = [tokenize(doc) for doc in documents]
        self.doc_lengths = [len(doc) for doc in self.tokenized_docs]
        self.avg_doc_len = (sum(self.doc_lengths) / len(self.doc_lengths)) if self.doc_lengths else 0.0
        self.doc_freqs: list[Counter] = [Counter(doc) for doc in self.tokenized_docs]
        self.n_docs = len(documents)
        self.idf = self._compute_idf()

    def _compute_idf(self) -> dict[str, float]:
        df: Counter = Counter()
        for doc in self.tokenized_docs:
            for term in set(doc):
                df[term] += 1

        idf = {}
        for term, freq in df.items():
            idf[term] = math.log(1 + (self.n_docs - freq + 0.5) / (freq + 0.5))
        return idf

    def score(self, query: str, doc_index: int) -> float:
        if self.n_docs == 0 or self.avg_doc_len == 0:
            return 0.0

        query_terms = tokenize(query)
        doc_freq = self.doc_freqs[doc_index]
        doc_len = self.doc_lengths[doc_index]

        score = 0.0
        for term in query_terms:
            if term not in doc_freq:
                continue
            f = doc_freq[term]
            idf = self.idf.get(term, 0.0)
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * numerator / denominator
        return score

    def score_all(self, query: str) -> list[float]:
        return [self.score(query, i) for i in range(self.n_docs)]


def normalize_scores(scores: list[float]) -> list[float]:
    """Min-max normalize a list of scores into [0, 1]. Handles flat/empty lists safely."""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]
