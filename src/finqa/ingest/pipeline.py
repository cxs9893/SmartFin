from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_RECORD_LIST_KEYS = ("sections", "data", "records", "items", "chunks")
_WS_RE = re.compile(r"\s+")


def _collapse_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _to_str(value: Any, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in _RECORD_LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return [payload]


def _normalize_record(record: dict[str, Any], source_path: str, idx: int) -> dict[str, Any]:
    source_file = Path(source_path).name
    doc_id = Path(source_path).stem
    section = _to_str(record.get("section") or record.get("item") or record.get("title"))
    fiscal_year = _to_str(
        record.get("fiscal_year")
        or record.get("year")
        or record.get("fy")
        or record.get("report_year")
    )
    text = _collapse_ws(str(record.get("text") or record.get("content") or record.get("paragraph") or ""))
    paragraph_id = _to_str(
        record.get("paragraph_id")
        or record.get("id")
        or record.get("para_id")
        or f"{source_file}-{idx:05d}",
        fallback=f"{source_file}-{idx:05d}",
    )
    chunk_seed = f"{source_path}|{paragraph_id}|{text}"
    chunk_id = hashlib.sha1(chunk_seed.encode("utf-8")).hexdigest()[:16]

    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "source_path": source_path,
        "source_file": source_file,
        "fiscal_year": fiscal_year,
        "section": section,
        "paragraph_id": paragraph_id,
        "text": text,
        "quote_en": text[:300],
    }


def ingest_directory(data_dir: Path, out_dir: Path) -> Path:
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()

    json_files = sorted(data_dir.rglob("*.json"), key=lambda p: p.as_posix())
    for json_file in json_files:
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        source_path = json_file.relative_to(data_dir).as_posix()
        records = _extract_records(payload)
        for idx, record in enumerate(records):
            normalized = _normalize_record(record, source_path, idx)
            if not normalized["text"]:
                continue
            chunk_id = str(normalized["chunk_id"])
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            chunks.append(normalized)

    chunks.sort(key=lambda item: (item["source_path"], item["paragraph_id"], item["chunk_id"]))

    out_path = chunks_dir / "chunks.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")

    return out_path
