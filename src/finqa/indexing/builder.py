from __future__ import annotations

import json
import pickle
import re
from pathlib import Path
from typing import Any

import faiss
from rank_bm25 import BM25Okapi

from finqa.common.settings import Settings
from finqa.indexing.embeddings import embed_texts

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_DEFAULT_DIM = 256


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


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
    cfg = Settings()

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

    texts = [str(chunk.get("text", "")) for chunk in chunks]
    vectors, embed_info = embed_texts(texts, cfg)

    vector_dim = int(embed_info.dim if embed_info.dim > 0 else _DEFAULT_DIM)
    faiss_index = faiss.IndexFlatIP(vector_dim)
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
        "embedding_provider": embed_info.provider,
        "embedding_model": embed_info.model,
        "embedding_dim": vector_dim,
        "embedding_requested_provider": embed_info.requested_provider,
    }
    if embed_info.fallback_from is not None:
        meta["embedding_fallback_from"] = embed_info.fallback_from
    if embed_info.fallback_reason:
        meta["embedding_fallback_reason"] = embed_info.fallback_reason

    (index_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
