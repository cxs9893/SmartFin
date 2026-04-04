from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from finqa.retrieval.hybrid import hybrid_search


def _write_index(tmp_path: Path) -> Path:
    index_dir = tmp_path / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "c-risk",
            "source_file": "acme_2024.json",
            "fiscal_year": "2024",
            "section": "Risk Factors",
            "paragraph_id": "Risk-00001",
            "text": "Supply chain risk increased in 2024 due to vendor concentration.",
        },
        {
            "chunk_id": "c-mda-2024",
            "source_file": "acme_2024.json",
            "fiscal_year": "2024",
            "section": "MD&A",
            "paragraph_id": "MDA-00001",
            "text": "Revenue growth accelerated with strong cloud subscription expansion.",
        },
        {
            "chunk_id": "c-mda-2023",
            "source_file": "acme_2023.json",
            "fiscal_year": "2023",
            "section": "MD&A",
            "paragraph_id": "MDA-00002",
            "text": "Operating margin remained stable while costs were tightly controlled.",
        },
    ]

    with chunks_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    (index_dir / "manifest.txt").write_text(str(chunks_path), encoding="utf-8")
    return index_dir


def _write_faiss_payload(index_dir: Path, vectors: np.ndarray) -> None:
    faiss_dir = index_dir / "faiss"
    faiss_dir.mkdir(parents=True, exist_ok=True)

    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(vectors.astype(np.float32))
    faiss.write_index(index, str(faiss_dir / "index.faiss"))

    id_map = ["c-risk", "c-mda-2024", "c-mda-2023"]
    (faiss_dir / "id_map.json").write_text(json.dumps(id_map, ensure_ascii=False), encoding="utf-8")

    meta = {
        "embedding_provider": "hash",
        "embedding_model": "hash-3",
        "embedding_dim": 3,
        "embedding_requested_provider": "bge",
    }
    (index_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def test_hybrid_search_returns_standard_hit_and_citation_fields(tmp_path: Path) -> None:
    index_dir = _write_index(tmp_path)

    hits = hybrid_search(
        index_dir,
        "supply chain risk",
        top_k=2,
        bm25_weight=0.7,
        vector_weight=0.3,
        bm25_top_k=3,
        vector_top_k=2,
    )

    assert len(hits) == 2
    assert hits[0]["fusion_score"] >= hits[1]["fusion_score"]

    required_top_level = {
        "source_file",
        "fiscal_year",
        "section",
        "paragraph_id",
        "text",
        "hit",
        "citation",
        "rank",
        "score",
        "bm25_score",
        "vector_score",
        "fusion_score",
    }
    assert required_top_level.issubset(hits[0].keys())

    citation = hits[0]["citation"]
    assert {"source_file", "fiscal_year", "section", "paragraph_id", "quote_en"}.issubset(citation.keys())


def test_hybrid_search_weights_are_configurable(monkeypatch, tmp_path: Path) -> None:
    index_dir = _write_index(tmp_path)

    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_bm25",
        lambda _query, _chunks: np.array([2.0, 1.0, 0.0]),
    )
    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_vector",
        lambda _query, _chunks, _index_dir: np.array([0.0, 3.0, 1.0]),
    )

    bm25_first = hybrid_search(index_dir, "q", top_k=1, bm25_weight=1.0, vector_weight=0.0)
    vector_first = hybrid_search(index_dir, "q", top_k=1, bm25_weight=0.0, vector_weight=1.0)

    assert bm25_first[0]["paragraph_id"] == "Risk-00001"
    assert vector_first[0]["paragraph_id"] == "MDA-00001"


def test_hybrid_search_prefers_embedding_model_scores_over_faiss(monkeypatch, tmp_path: Path) -> None:
    index_dir = _write_index(tmp_path)
    _write_faiss_payload(
        index_dir,
        np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        ),
    )

    monkeypatch.setattr(
        "finqa.retrieval.hybrid.embed_texts",
        lambda _texts, _cfg: (
            np.asarray(
                [
                    [0.0, 1.0, 0.0],  # query
                    [1.0, 0.0, 0.0],  # c-risk
                    [0.0, 1.0, 0.0],  # c-mda-2024
                    [0.0, 0.0, 1.0],  # c-mda-2023
                ],
                dtype=np.float32,
            ),
            object(),
        ),
    )
    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_vector_faiss",
        lambda _query, _chunks, _index_dir: (_ for _ in ()).throw(AssertionError("faiss should not be prioritized")),
    )

    hits = hybrid_search(index_dir, "Apple revenue", top_k=1, bm25_weight=0.0, vector_weight=1.0)
    assert hits[0]["paragraph_id"] == "MDA-00001"


def test_hybrid_search_fallbacks_to_hash_when_query_embedding_unavailable(monkeypatch, tmp_path: Path) -> None:
    index_dir = _write_index(tmp_path)
    _write_faiss_payload(
        index_dir,
        np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        ),
    )

    monkeypatch.setattr(
        "finqa.retrieval.hybrid.embed_texts",
        lambda _texts, _cfg: (_ for _ in ()).throw(RuntimeError("missing_embedding_key")),
    )
    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_vector_faiss",
        lambda _query, _chunks, _index_dir: None,
    )
    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_vector_hash",
        lambda _query, _chunks: np.asarray([0.0, 3.0, 1.0], dtype=float),
    )

    hits = hybrid_search(index_dir, "Apple revenue", top_k=1, bm25_weight=0.0, vector_weight=1.0)
    assert hits[0]["paragraph_id"] == "MDA-00001"
