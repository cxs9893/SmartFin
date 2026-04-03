from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _normalize_record(record: dict[str, Any], source_file: str, idx: int) -> dict[str, Any]:
    section = str(record.get("section") or record.get("item") or "unknown")
    text = str(record.get("text") or record.get("content") or "").strip()
    fiscal_year = str(record.get("fiscal_year") or record.get("year") or "unknown")
    paragraph_id = str(record.get("paragraph_id") or f"{section}-{idx:05d}")
    return {
        "source_file": source_file,
        "fiscal_year": fiscal_year,
        "section": section,
        "paragraph_id": paragraph_id,
        "text": text,
    }


def ingest_directory(data_dir: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []

    json_files = sorted(data_dir.rglob("*.json"))
    for json_file in json_files:
        payload = json.loads(json_file.read_text(encoding="utf-8"))

        if isinstance(payload, dict):
            if isinstance(payload.get("sections"), list):
                iterable = payload["sections"]
            elif isinstance(payload.get("data"), list):
                iterable = payload["data"]
            else:
                iterable = [payload]
        elif isinstance(payload, list):
            iterable = payload
        else:
            iterable = []

        for idx, record in enumerate(iterable):
            if not isinstance(record, dict):
                continue
            normalized = _normalize_record(record, json_file.name, idx)
            if normalized["text"]:
                chunks.append(normalized)

    out_path = out_dir / "chunks.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return out_path
