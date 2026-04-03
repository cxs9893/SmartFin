from __future__ import annotations

import json
import pickle
import re
from hashlib import blake2b
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_VECTOR_DIM = 256


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


def _hash_embed(text: str, dim: int = _VECTOR_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for tok in _tokenize(text):
        digest = blake2b(tok.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[idx] += sign

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
    if not chunks_path.exists():
        return []

    chunks: list[dict[str, Any]] = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                chunks.append(payload)
    return chunks


def build_indices(chunks_path: Path, index_dir: Path) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    bm25_dir = index_dir / "bm25"
    faiss_dir = index_dir / "faiss"
    bm25_dir.mkdir(parents=True, exist_ok=True)
    faiss_dir.mkdir(parents=True, exist_ok=True)

    chunks = _load_chunks(chunks_path)

    docs_path = bm25_dir / "documents.jsonl"
    with docs_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")

    tokenized_corpus = [_tokenize(str(chunk.get("text", ""))) for chunk in chunks]
    if tokenized_corpus:
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_payload: dict[str, Any] = {
            "bm25": bm25,
            "doc_ids": [str(chunk.get("chunk_id", "")) for chunk in chunks],
        }
    else:
        bm25_payload = {"bm25": None, "doc_ids": []}

    with (bm25_dir / "bm25.pkl").open("wb") as f:
        pickle.dump(bm25_payload, f)

    vectors = np.zeros((len(chunks), _VECTOR_DIM), dtype=np.float32)
    for i, chunk in enumerate(chunks):
        vectors[i] = _hash_embed(str(chunk.get("text", "")))

    faiss_index = faiss.IndexFlatIP(_VECTOR_DIM)
    if len(chunks) > 0:
        faiss_index.add(vectors)

    faiss.write_index(faiss_index, str(faiss_dir / "index.faiss"))
    with (faiss_dir / "id_map.json").open("w", encoding="utf-8") as f:
        json.dump([str(chunk.get("chunk_id", "")) for chunk in chunks], f, ensure_ascii=False, indent=2)

    manifest = index_dir / "manifest.txt"
    manifest.write_text(str(chunks_path.resolve()), encoding="utf-8")

    meta = {
        "version": 1,
        "doc_count": len(chunks),
        "bm25_path": str((bm25_dir / "bm25.pkl").resolve()),
        "faiss_path": str((faiss_dir / "index.faiss").resolve()),
        "chunks_path": str(chunks_path.resolve()),
    }
    (index_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
