from __future__ import annotations

from typing import Any


def generate_answer(query: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    if not hits:
        return {
            "answer_zh": "证据不足，暂时无法给出可靠回答。",
            "confidence": 0.0,
            "citations": [],
        }

    top = hits[0]
    answer = (
        "基于已检索到的10-K段落，当前问题的核心信息如下：\n"
        f"- 年份: {top.get('fiscal_year', 'unknown')}\n"
        f"- 章节: {top.get('section', 'unknown')}\n"
        f"- 摘要: {str(top.get('text', ''))[:180]}"
    )

    return {
        "answer_zh": answer,
        "confidence": 0.42,
        "citations": [
            {
                "source_file": top.get("source_file", "unknown"),
                "fiscal_year": top.get("fiscal_year", "unknown"),
                "section": top.get("section", "unknown"),
                "paragraph_id": top.get("paragraph_id", "unknown"),
                "quote_en": str(top.get("text", ""))[:300],
            }
        ],
        "query": query,
    }
