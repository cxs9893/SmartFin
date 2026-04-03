from __future__ import annotations

from typing import Any


def generate_report(mode: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    if not hits:
        return {
            "mode": mode,
            "report_zh": "暂无足够证据生成报告。",
            "highlights": [],
        }

    highlights: list[str] = []
    for hit in hits[:5]:
        highlights.append(f"[{hit.get('fiscal_year', 'unknown')}] {hit.get('section', 'unknown')}")

    return {
        "mode": mode,
        "report_zh": "基于已检索财报段落生成的简要分析报告（MVP占位版）。",
        "highlights": highlights,
    }
