from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def hybrid_search(index_dir: Path, query: str, top_k: int = 8) -> list[dict[str, Any]]:
    _ = query
    manifest = index_dir / "manifest.txt"
    if not manifest.exists():
        return []

    chunks_path = Path(manifest.read_text(encoding="utf-8").strip())
    if not chunks_path.exists():
        return []

    hits: list[dict[str, Any]] = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            payload = json.loads(line)
            hits.append(payload)
            if len(hits) >= top_k:
                break
    return hits
