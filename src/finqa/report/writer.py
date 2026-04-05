from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any


_REPORT_MODEL_CACHE: dict[str, tuple[Any, Any, str]] = {}


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


def _llm_enable_mode(value: str | None) -> str:
    if value is None:
        return "off"
    normalized = value.strip().lower()
    if normalized == "auto":
        return "auto"
    if normalized in {"1", "true", "yes", "on"}:
        return "on"
    return "off"


def _pipeline_config() -> dict[str, Any]:
    embedding_provider = os.getenv("FINQA_EMBEDDING_PROVIDER", "bge")
    llm_provider = os.getenv("FINQA_LLM_PROVIDER", "modelscope_local")
    llm_model = os.getenv("FINQA_LLM_MODEL", "models/Qwen2___5-0___5B-Instruct")
    llm_device = os.getenv("FINQA_LLM_DEVICE", "auto")
    llm_local_files_only = _is_truthy(os.getenv("FINQA_LLM_LOCAL_FILES_ONLY", "true"))
    llm_enable_mode = _llm_enable_mode(os.getenv("FINQA_ENABLE_LLM", "0"))
    llm_provider_ok = llm_provider in {"modelscope_local", "local"}
    llm_model_exists = Path(llm_model).exists()
    llm_enabled = llm_enable_mode in {"on", "auto"}
    if llm_enable_mode == "on":
        llm_active = llm_provider_ok
    elif llm_enable_mode == "auto":
        llm_active = llm_provider_ok and llm_model_exists
    else:
        llm_active = False

    return {
        "embedding_provider": embedding_provider,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_device": llm_device,
        "llm_local_files_only": llm_local_files_only,
        "llm_enable_mode": llm_enable_mode,
        "llm_model_exists": llm_model_exists,
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


def _call_modelscope_local_report(mode: str, evidence: list[dict[str, str]]) -> tuple[str | None, str | None]:
    model_ref = os.getenv("FINQA_LLM_MODEL", "models/Qwen2___5-0___5B-Instruct").strip()
    if not model_ref:
        return None, "FINQA_LLM_MODEL 未配置"

    local_files_only = _is_truthy(os.getenv("FINQA_LLM_LOCAL_FILES_ONLY", "true"))
    model_path = Path(model_ref)
    if local_files_only and not model_path.exists():
        return None, f"本地模型不存在: {model_ref}"

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # noqa: BLE001
        return None, f"本地模型依赖不可用: {exc}"

    device_pref = os.getenv("FINQA_LLM_DEVICE", "auto").strip().lower()
    if device_pref == "cpu":
        device = "cpu"
    elif device_pref == "cuda":
        device = "cuda"
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    cache_key = f"{model_ref}::{device}::{int(local_files_only)}"
    cached = _REPORT_MODEL_CACHE.get(cache_key)
    if cached is None:
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_ref, trust_remote_code=True, local_files_only=local_files_only
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_ref, trust_remote_code=True, local_files_only=local_files_only
            )
        except Exception as exc:  # noqa: BLE001
            return None, f"本地模型加载失败: {exc}"
        if device == "cuda":
            model = model.to("cuda")
        _REPORT_MODEL_CACHE[cache_key] = (tokenizer, model, device)
        cached = _REPORT_MODEL_CACHE[cache_key]

    tokenizer, model, device = cached
    evidence_lines = [
        f"- [{item['fiscal_year']}] {item['section']}: {item['snippet']}"
        for item in evidence[:8]
    ]
    messages = [
        {
            "role": "system",
            "content": "你是财报分析助手，仅基于给定证据生成简洁中文报告。",
        },
        {
            "role": "user",
            "content": f"请基于以下财报证据，生成 {mode} 模式的中文简要分析。只输出报告正文，不要额外标题。\n"
            + "\n".join(evidence_lines),
        },
    ]

    try:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}\n\n报告："

    try:
        inputs = tokenizer(prompt, return_tensors="pt")
        if device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        outputs = model.generate(
            **inputs,
            max_new_tokens=int(os.getenv("FINQA_LLM_MAX_NEW_TOKENS", "192")),
            do_sample=False,
            temperature=0.0,
        )
        generated = outputs[0][inputs["input_ids"].shape[1] :]
        report = tokenizer.decode(generated, skip_special_tokens=True).strip()
    except Exception as exc:  # noqa: BLE001
        return None, f"本地模型推理失败: {exc}"

    if not report:
        return None, "本地模型返回内容为空"
    return report, None


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
        llm_text, llm_error = _call_modelscope_local_report(normalized_mode, evidence)
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
