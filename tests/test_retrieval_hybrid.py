from __future__ import annotations

import json
from pathlib import Path

from finqa.retrieval.hybrid import hybrid_search


def _write_index(tmp_path: Path) -> Path:
    index_dir = tmp_path / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "source_file": "acme_2024.json",
            "fiscal_year": "2024",
            "section": "Risk Factors",
            "paragraph_id": "Risk-00001",
            "text": "Supply chain risk increased in 2024 due to vendor concentration.",
        },
        {
            "source_file": "acme_2024.json",
            "fiscal_year": "2024",
            "section": "MD&A",
            "paragraph_id": "MDA-00001",
            "text": "Revenue growth accelerated with strong cloud subscription expansion.",
        },
        {
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
        lambda _query, _chunks: __import__("numpy").array([2.0, 1.0, 0.0]),
    )
    monkeypatch.setattr(
        "finqa.retrieval.hybrid._score_vector",
        lambda _query, _chunks: __import__("numpy").array([0.0, 3.0, 1.0]),
    )

    bm25_first = hybrid_search(index_dir, "q", top_k=1, bm25_weight=1.0, vector_weight=0.0)
    vector_first = hybrid_search(index_dir, "q", top_k=1, bm25_weight=0.0, vector_weight=1.0)

    assert bm25_first[0]["paragraph_id"] == "Risk-00001"
    assert vector_first[0]["paragraph_id"] == "MDA-00001"
