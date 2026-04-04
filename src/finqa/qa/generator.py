from __future__ import annotations

import re
from typing import Any


_REFUSAL_MESSAGE = "证据不足，暂时无法给出可靠回答。"
_ENGLISH_RE = re.compile(r"[A-Za-z]")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_citation(hit: dict[str, Any]) -> dict[str, str] | None:
    source_file = _normalize_text(hit.get("source_file"))
    fiscal_year = _normalize_text(hit.get("fiscal_year"))
    section = _normalize_text(hit.get("section"))
    paragraph_id = _normalize_text(hit.get("paragraph_id"))
    quote_en = _normalize_text(hit.get("text"))

    if not all([source_file, fiscal_year, section, paragraph_id, quote_en]):
        return None

    if _ENGLISH_RE.search(quote_en) is None:
        return None

    return {
        "source_file": source_file,
        "fiscal_year": fiscal_year,
        "section": section,
        "paragraph_id": paragraph_id,
        "quote_en": quote_en[:300],
    }


def _build_answer(citations: list[dict[str, str]]) -> str:
    lines = ["根据检索到的英文财报证据，可以确认："]
    for idx, item in enumerate(citations, start=1):
        lines.append(
            f"- 证据[{idx}]：{item['fiscal_year']} 年 {item['section']}（段落 {item['paragraph_id']}）"
        )
    lines.append("- 结论范围：仅依据以上引用证据，不包含未检索到的信息。")
    return "\n".join(lines)


def generate_answer(query: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    _ = query
    if not hits:
        return {
            "answer_zh": _REFUSAL_MESSAGE,
            "confidence": 0.0,
            "citations": [],
        }

    citations: list[dict[str, str]] = []
    for hit in hits:
        citation = _build_citation(hit)
        if citation is None:
            continue
        citations.append(citation)
        if len(citations) >= 3:
            break

    if not citations:
        return {
            "answer_zh": _REFUSAL_MESSAGE,
            "confidence": 0.0,
            "citations": [],
        }

    confidence = min(0.85, 0.45 + 0.1 * len(citations))

    return {
        "answer_zh": _build_answer(citations),
        "confidence": round(confidence, 2),
        "citations": citations,
    }
