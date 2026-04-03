from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Citation:
    source_file: str
    fiscal_year: str
    section: str
    paragraph_id: str
    quote_en: str
    chunk_id: str | None = None
    source_path: str | None = None
    doc_id: str | None = None


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    source_path: str
    source_file: str
    fiscal_year: str
    section: str
    paragraph_id: str
    text: str
    quote_en: str
