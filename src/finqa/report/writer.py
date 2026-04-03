from __future__ import annotations

from collections import Counter
from typing import Any


def _safe_year_value(year: str) -> int:
    digits = "".join(ch for ch in year if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return -1


def _normalize_mode(mode: str) -> str:
    if mode in {"single_year", "cross_year"}:
        return mode
    return "cross_year"


def _evidence_payload(hit: dict[str, Any]) -> dict[str, str]:
    snippet = str(hit.get("text", "")).strip().replace("\n", " ")
    return {
        "source_file": str(hit.get("source_file", "unknown")),
        "fiscal_year": str(hit.get("fiscal_year", "unknown")),
        "section": str(hit.get("section", "unknown")),
        "paragraph_id": str(hit.get("paragraph_id", "unknown")),
        "snippet": snippet[:220],
    }


def _build_yearly_breakdown(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    years: dict[str, list[dict[str, Any]]] = {}
    for hit in hits:
        year = str(hit.get("fiscal_year", "unknown"))
        years.setdefault(year, []).append(hit)

    sorted_years = sorted(years.keys(), key=_safe_year_value, reverse=True)
    breakdown: list[dict[str, Any]] = []
    for year in sorted_years:
        year_hits = years[year]
        section_counter = Counter(str(h.get("section", "unknown")) for h in year_hits)
        top_sections = [section for section, _ in section_counter.most_common(3)]
        breakdown.append(
            {
                "fiscal_year": year,
                "evidence_count": len(year_hits),
                "top_sections": top_sections,
            }
        )
    return breakdown


def _empty_report(mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "report_zh": "暂无足够证据生成报告。",
        "summary": {
            "year_count": 0,
            "evidence_count": 0,
            "section_count": 0,
            "selected_year": None,
        },
        "highlights": [],
        "yearly_breakdown": [],
        "evidence": [],
    }


def generate_report(mode: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    if not hits:
        return _empty_report(normalized_mode)

    working_hits = hits
    yearly_breakdown = _build_yearly_breakdown(hits)
    selected_year: str | None = None

    if normalized_mode == "single_year" and yearly_breakdown:
        selected_year = str(yearly_breakdown[0]["fiscal_year"])
        working_hits = [h for h in hits if str(h.get("fiscal_year", "unknown")) == selected_year]
        yearly_breakdown = _build_yearly_breakdown(working_hits)

    section_counter = Counter(str(h.get("section", "unknown")) for h in working_hits)
    highlights = [
        f"[{h.get('fiscal_year', 'unknown')}] {h.get('section', 'unknown')}"
        for h in working_hits[:5]
    ]
    evidence = [_evidence_payload(hit) for hit in working_hits[:8]]

    if normalized_mode == "single_year":
        report_zh = (
            f"single_year 模式：聚焦 {selected_year or 'unknown'} 年，共纳入 "
            f"{len(working_hits)} 条证据，重点章节为 {', '.join(section_counter.keys()) or 'unknown'}。"
        )
    else:
        years = [str(item["fiscal_year"]) for item in yearly_breakdown]
        report_zh = (
            f"cross_year 模式：覆盖 {len(years)} 个年度（{', '.join(years) or 'unknown'}），"
            f"共纳入 {len(working_hits)} 条证据。"
        )

    return {
        "mode": normalized_mode,
        "report_zh": report_zh,
        "summary": {
            "year_count": len({str(h.get("fiscal_year", "unknown")) for h in working_hits}),
            "evidence_count": len(working_hits),
            "section_count": len(section_counter),
            "selected_year": selected_year,
        },
        "highlights": highlights,
        "yearly_breakdown": yearly_breakdown,
        "evidence": evidence,
    }
