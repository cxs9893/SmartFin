from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any
from urllib import error, request


def _safe_year_value(year: str) -> int:
    digits = "".join(ch for ch in year if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return -1


def _normalize_mode(mode: str) -> str:
    if mode in {"single_year", "cross_year"}:
        return mode
    return "cross_year"


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _pipeline_config() -> dict[str, Any]:
    embedding_provider = os.getenv("FINQA_EMBEDDING_PROVIDER", "bge")
    llm_provider = os.getenv("FINQA_LLM_PROVIDER", "modelscope_local")
    llm_model = os.getenv("FINQA_LLM_MODEL", "models/Qwen2___5-0___5B-Instruct")
    llm_enabled = _is_truthy(os.getenv("FINQA_ENABLE_LLM"))
    openai_key = os.getenv("OPENAI_API_KEY", "")
    llm_active = llm_enabled and llm_provider == "openai-compatible" and bool(openai_key)

    return {
        "embedding_provider": embedding_provider,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_enabled": llm_enabled,
        "llm_active": llm_active,
    }


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
        "pipeline": _pipeline_config(),
        "llm_error": None,
    }


def _call_openai_compatible_report(mode: str, evidence: list[dict[str, str]]) -> tuple[str | None, str | None]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None, "OPENAI_API_KEY 未配置"

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    evidence_lines = [
        f"- [{item['fiscal_year']}] {item['section']}: {item['snippet']}"
        for item in evidence[:8]
    ]
    user_prompt = (
        f"请基于以下财报证据，生成 {mode} 模式的中文简要分析。"
        "只输出报告正文，不要额外标题。\n" + "\n".join(evidence_lines)
    )

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是财报分析助手，仅基于给定证据生成简洁中文报告。",
            },
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, f"LLM HTTPError {exc.code}: {detail[:200]}"
    except Exception as exc:  # noqa: BLE001
        return None, f"LLM 调用失败: {exc}"

    choices = payload.get("choices") or []
    if not choices:
        return None, "LLM 返回为空"
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        return None, "LLM 返回内容为空"
    return content, None


def generate_report(mode: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    pipeline = _pipeline_config()
    if not hits:
        payload = _empty_report(normalized_mode)
        payload["pipeline"] = pipeline
        return payload

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

    llm_error: str | None = None
    if pipeline["llm_active"]:
        llm_text, llm_error = _call_openai_compatible_report(normalized_mode, evidence)
        if llm_text:
            report_zh = llm_text

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
        "pipeline": pipeline,
        "llm_error": llm_error,
    }
