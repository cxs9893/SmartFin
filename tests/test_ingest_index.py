from __future__ import annotations

import json

from finqa.ingest.pipeline import ingest_directory
from finqa.indexing.builder import build_indices
from finqa.retrieval.hybrid import hybrid_search


def test_ingest_index_idempotent_and_retrievable(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    nested = data_dir / "nested"
    nested.mkdir()

    (data_dir / "a.json").write_text(
        json.dumps(
            {
                "sections": [
                    {
                        "section": "Item 1",
                        "text": "Revenue grew 20% year-over-year.",
                        "fiscal_year": "2024",
                        "paragraph_id": "p-001",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (nested / "b.json").write_text(
        json.dumps(
            [
                {
                    "item": "Risk Factors",
                    "content": "Supply chain volatility remains elevated.",
                    "year": "2023",
                    "id": "rf-002",
                }
            ]
        ),
        encoding="utf-8",
    )
    (nested / "sql_key_shape.json").write_text(
        json.dumps(
            {
                "select a.file_fiscal_year, b.section_title, b.section_id, b.section_text from sec": [
                    {
                        "file_fiscal_year": 2022,
                        "section_title": "Management Discussion",
                        "section_id": 7,
                        "section_text": "Operating margin expanded despite volatility.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (nested / "broken.json").write_text("{not valid json}", encoding="utf-8")

    workspace = tmp_path / ".finqa"

    chunks_path = ingest_directory(data_dir, workspace)
    build_indices(chunks_path, workspace / "index")
    first_snapshot = chunks_path.read_text(encoding="utf-8")

    chunks_path_2 = ingest_directory(data_dir, workspace)
    build_indices(chunks_path_2, workspace / "index")
    second_snapshot = chunks_path_2.read_text(encoding="utf-8")

    assert chunks_path == chunks_path_2
    assert first_snapshot == second_snapshot

    index_dir = workspace / "index"
    assert (workspace / "chunks" / "chunks.jsonl").exists()
    assert (index_dir / "manifest.txt").exists()
    assert (index_dir / "bm25" / "bm25.pkl").exists()
    assert (index_dir / "bm25" / "documents.jsonl").exists()
    assert (index_dir / "faiss" / "index.faiss").exists()
    assert (index_dir / "faiss" / "id_map.json").exists()
    assert (index_dir / "index_meta.json").exists()

    manifest_target = (index_dir / "manifest.txt").read_text(encoding="utf-8").strip()
    assert manifest_target == str(chunks_path.resolve())

    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(chunks) == 3
    assert any(c["section"] == "Management Discussion" and c["fiscal_year"] == "2022" for c in chunks)

    hits = hybrid_search(index_dir, "revenue", top_k=5)
    assert hits
    top = hits[0]
    for key in ["hit", "citation", "rank", "score", "bm25_score", "vector_score", "fusion_score"]:
        assert key in top
    for key in ["source_file", "fiscal_year", "section", "paragraph_id", "quote_en"]:
        assert key in top["citation"]
