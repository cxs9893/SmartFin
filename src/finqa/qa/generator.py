from __future__ import annotations

from typing import Any


_REFUSAL_MESSAGE = "证据不足，暂时无法给出可靠回答。"


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

    return {
        "source_file": source_file,
        "fiscal_year": fiscal_year,
        "section": section,
        "paragraph_id": paragraph_id,
        "quote_en": quote_en[:300],
    }


def _build_answer(citations: list[dict[str, str]]) -> str:
    top = citations[0]
    lines = [
        "根据检索到的英文财报证据，可以确认：",
        f"- 相关年份：{top['fiscal_year']}",
        f"- 相关章节：{top['section']}",
        "- 关键信息：以上结论仅来自下方引用段落。",
    ]
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
