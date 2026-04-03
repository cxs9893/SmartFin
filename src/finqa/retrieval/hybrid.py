from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

DEFAULT_BM25_WEIGHT = 0.6
DEFAULT_VECTOR_WEIGHT = 0.4
DEFAULT_VECTOR_DIM = 256
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _load_chunks(index_dir: Path) -> list[dict[str, Any]]:
    manifest = index_dir / "manifest.txt"
    if not manifest.exists():
        return []

    chunks_path = Path(manifest.read_text(encoding="utf-8").strip())
    if not chunks_path.exists():
        return []

    chunks: list[dict[str, Any]] = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            payload = json.loads(line)
            if isinstance(payload, dict):
                chunks.append(payload)
    return chunks


def _ensure_weights(bm25_weight: float, vector_weight: float) -> tuple[float, float]:
    b = max(0.0, float(bm25_weight))
    v = max(0.0, float(vector_weight))
    total = b + v
    if total == 0:
        return DEFAULT_BM25_WEIGHT, DEFAULT_VECTOR_WEIGHT
    return b / total, v / total


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    min_v = float(np.min(scores))
    max_v = float(np.max(scores))
    if max_v <= min_v:
        return np.zeros_like(scores, dtype=float)
    return (scores - min_v) / (max_v - min_v)


def _embedding(text: str, dim: int = DEFAULT_VECTOR_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in _tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], byteorder="little", signed=False) % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _score_bm25(query: str, chunks: list[dict[str, Any]]) -> np.ndarray:
    docs = [_tokenize(str(chunk.get("text") or "")) for chunk in chunks]
    q_tokens = _tokenize(query)
    if not docs or not q_tokens:
        return np.zeros(len(chunks), dtype=float)

    bm25 = BM25Okapi(docs)
    return np.asarray(bm25.get_scores(q_tokens), dtype=float)


def _score_vector(query: str, chunks: list[dict[str, Any]]) -> np.ndarray:
    if not chunks or not query.strip():
        return np.zeros(len(chunks), dtype=float)

    q_vec = _embedding(query)
    if float(np.linalg.norm(q_vec)) == 0.0:
        return np.zeros(len(chunks), dtype=float)

    doc_matrix = np.vstack([_embedding(str(chunk.get("text") or "")) for chunk in chunks])
    return (doc_matrix @ q_vec).astype(float)


def _citation_from_chunk(chunk: dict[str, Any]) -> dict[str, str]:
    return {
        "source_file": str(chunk.get("source_file", "unknown")),
        "fiscal_year": str(chunk.get("fiscal_year", "unknown")),
        "section": str(chunk.get("section", "unknown")),
        "paragraph_id": str(chunk.get("paragraph_id", "unknown")),
        "quote_en": str(chunk.get("text", ""))[:300],
    }


def hybrid_search(
    index_dir: Path,
    query: str,
    top_k: int = 8,
    *,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    bm25_top_k: int | None = None,
    vector_top_k: int | None = None,
) -> list[dict[str, Any]]:
    chunks = _load_chunks(index_dir)
    if not chunks or top_k <= 0:
        return []

    top_k = min(int(top_k), len(chunks))
    bm25_weight, vector_weight = _ensure_weights(bm25_weight, vector_weight)

    bm25_scores = _score_bm25(query, chunks)
    vector_scores = _score_vector(query, chunks)
    bm25_norm = _normalize_scores(bm25_scores)
    vector_norm = _normalize_scores(vector_scores)

    bm25_candidate_k = min(len(chunks), int(bm25_top_k or max(top_k * 4, top_k)))
    vector_candidate_k = min(len(chunks), int(vector_top_k or max(top_k * 4, top_k)))

    bm25_order = np.argsort(-bm25_scores, kind="stable")[:bm25_candidate_k]
    vector_order = np.argsort(-vector_scores, kind="stable")[:vector_candidate_k]
    candidate_indices = sorted(set(bm25_order.tolist()) | set(vector_order.tolist()))
    if not candidate_indices:
        candidate_indices = list(range(len(chunks)))

    fused_scores = (bm25_weight * bm25_norm) + (vector_weight * vector_norm)
    ranked_candidates = sorted(candidate_indices, key=lambda i: float(fused_scores[i]), reverse=True)[:top_k]

    hits: list[dict[str, Any]] = []
    for rank, idx in enumerate(ranked_candidates, start=1):
        chunk = chunks[idx]
        citation = _citation_from_chunk(chunk)
        hit = {
            "source_file": citation["source_file"],
            "fiscal_year": citation["fiscal_year"],
            "section": citation["section"],
            "paragraph_id": citation["paragraph_id"],
            "text": str(chunk.get("text", "")),
        }
        payload: dict[str, Any] = {
            # Backward compatible fields consumed by qa/report.
            **hit,
            # Standardized retrieval contract for downstream users.
            "hit": hit,
            "citation": citation,
            "rank": rank,
            "score": float(fused_scores[idx]),
            "bm25_score": float(bm25_scores[idx]),
            "vector_score": float(vector_scores[idx]),
            "fusion_score": float(fused_scores[idx]),
        }
        hits.append(payload)
    return hits
