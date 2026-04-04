from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from finqa.common.settings import Settings
from finqa.indexing.embeddings import embed_texts

DEFAULT_BM25_WEIGHT = 0.4
DEFAULT_VECTOR_WEIGHT = 0.6
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


def _load_index_meta(index_dir: Path) -> dict[str, Any]:
    meta_path = index_dir / "index_meta.json"
    if not meta_path.exists():
        return {}
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _embed_query_with_index_meta(query: str, index_meta: dict[str, Any]) -> np.ndarray:
    cfg = Settings()
    provider = str(index_meta.get("embedding_provider") or cfg.embedding_provider).strip().lower()
    model = str(index_meta.get("embedding_model") or cfg.embedding_bge_model)
    dim = int(index_meta.get("embedding_dim") or cfg.embedding_hash_dim or DEFAULT_VECTOR_DIM)

    if provider == "hash":
        query_cfg = Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, dim))
    elif provider == "bge":
        query_cfg = Settings(
            _env_file=None,
            embedding_provider="bge",
            embedding_bge_model=model,
            embedding_bge_dim=max(8, dim),
            embedding_bge_device=cfg.embedding_bge_device,
            embedding_bge_local_files_only=cfg.embedding_bge_local_files_only,
            embedding_bge_trust_remote_code=cfg.embedding_bge_trust_remote_code,
            embedding_batch_size=cfg.embedding_batch_size,
        )
    else:
        query_cfg = Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, dim))

    vectors, info = embed_texts([query], query_cfg)
    query_vec = np.asarray(vectors[0], dtype=np.float32)

    # Guarantee fallback-to-hash behavior when provider output cannot match the index dim.
    if query_vec.shape[0] != dim:
        hash_cfg = Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, dim))
        hash_vectors, hash_info = embed_texts([query], hash_cfg)
        query_vec = np.asarray(hash_vectors[0], dtype=np.float32)
        _ = hash_info

    _ = info
    return query_vec


def _build_embedding_cfg(index_meta: dict[str, Any]) -> Settings:
    cfg = Settings()
    provider = str(index_meta.get("embedding_provider") or cfg.embedding_provider).strip().lower()
    model = str(index_meta.get("embedding_model") or cfg.embedding_bge_model)
    dim = int(index_meta.get("embedding_dim") or cfg.embedding_hash_dim or DEFAULT_VECTOR_DIM)

    if provider == "hash":
        return Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, dim))
    if provider == "bge":
        return Settings(
            _env_file=None,
            embedding_provider="bge",
            embedding_bge_model=model,
            embedding_bge_dim=max(8, dim),
            embedding_bge_device=cfg.embedding_bge_device,
            embedding_bge_local_files_only=cfg.embedding_bge_local_files_only,
            embedding_bge_trust_remote_code=cfg.embedding_bge_trust_remote_code,
            embedding_batch_size=cfg.embedding_batch_size,
        )
    return Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, dim))


def _score_bm25(query: str, chunks: list[dict[str, Any]]) -> np.ndarray:
    docs = [_tokenize(str(chunk.get("text") or "")) for chunk in chunks]
    q_tokens = _tokenize(query)
    if not docs or not q_tokens:
        return np.zeros(len(chunks), dtype=float)

    bm25 = BM25Okapi(docs)
    return np.asarray(bm25.get_scores(q_tokens), dtype=float)


def _score_vector_hash(query: str, chunks: list[dict[str, Any]]) -> np.ndarray:
    if not chunks or not query.strip():
        return np.zeros(len(chunks), dtype=float)

    q_vec = _embedding(query)
    if float(np.linalg.norm(q_vec)) == 0.0:
        return np.zeros(len(chunks), dtype=float)

    doc_matrix = np.vstack([_embedding(str(chunk.get("text") or "")) for chunk in chunks])
    return (doc_matrix @ q_vec).astype(float)


def _score_vector_embedding_model(query: str, chunks: list[dict[str, Any]], index_meta: dict[str, Any]) -> np.ndarray | None:
    if not query.strip() or not chunks:
        return np.zeros(len(chunks), dtype=float)

    try:
        cfg = _build_embedding_cfg(index_meta)
        texts = [query] + [str(chunk.get("text") or "") for chunk in chunks]
        vectors, _ = embed_texts(texts, cfg)
        if vectors.ndim != 2 or vectors.shape[0] != len(texts):
            return None
        query_vec = np.asarray(vectors[0], dtype=np.float32)
        doc_matrix = np.asarray(vectors[1:], dtype=np.float32)
        return (doc_matrix @ query_vec).astype(float)
    except Exception:
        return None


def _score_vector_faiss(query: str, chunks: list[dict[str, Any]], index_dir: Path) -> np.ndarray | None:
    faiss_path = index_dir / "faiss" / "index.faiss"
    id_map_path = index_dir / "faiss" / "id_map.json"
    index_meta = _load_index_meta(index_dir)

    if not (faiss_path.exists() and id_map_path.exists() and index_meta):
        return None

    if not query.strip() or not chunks:
        return np.zeros(len(chunks), dtype=float)

    try:
        index = faiss.read_index(str(faiss_path))
        id_map_payload = json.loads(id_map_path.read_text(encoding="utf-8"))
        if not isinstance(id_map_payload, list):
            return None

        id_map = [str(item) for item in id_map_payload]
        chunk_id_to_pos: dict[str, int] = {}
        for i, chunk in enumerate(chunks):
            chunk_id = str(chunk.get("chunk_id") or "")
            if chunk_id:
                chunk_id_to_pos[chunk_id] = i

        query_vec = _embed_query_with_index_meta(query, index_meta)
        if query_vec.shape[0] != index.d:
            hash_cfg = Settings(_env_file=None, embedding_provider="hash", embedding_hash_dim=max(8, int(index.d)))
            hash_vectors, _ = embed_texts([query], hash_cfg)
            query_vec = np.asarray(hash_vectors[0], dtype=np.float32)

        search_k = min(max(1, len(id_map)), max(1, len(chunks)))
        sims, ids = index.search(query_vec.reshape(1, -1).astype(np.float32), search_k)

        scores = np.zeros(len(chunks), dtype=float)
        for sim, idx in zip(sims[0], ids[0], strict=False):
            if idx < 0 or idx >= len(id_map):
                continue
            chunk_id = str(id_map[int(idx)])
            pos = chunk_id_to_pos.get(chunk_id)
            if pos is None:
                continue
            scores[pos] = float(sim)
        return scores
    except Exception:
        return None


def _score_vector(query: str, chunks: list[dict[str, Any]], index_dir: Path) -> np.ndarray:
    index_meta = _load_index_meta(index_dir)
    model_scores = _score_vector_embedding_model(query, chunks, index_meta)
    if model_scores is not None:
        return model_scores

    faiss_scores = _score_vector_faiss(query, chunks, index_dir)
    if faiss_scores is not None:
        return faiss_scores
    return _score_vector_hash(query, chunks)


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
    vector_scores = _score_vector(query, chunks, index_dir)
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
