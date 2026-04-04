from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from finqa.common.settings import settings


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


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip()


def _resolve_llm_config() -> dict[str, str | int]:
    return {
        "provider": _get_env("FINQA_LLM_PROVIDER", settings.llm_provider).lower(),
        "api_key": _get_env("FINQA_LLM_API_KEY", settings.llm_api_key),
        "base_url": _get_env("FINQA_LLM_BASE_URL", settings.llm_base_url).rstrip("/"),
        "model": _get_env("FINQA_LLM_MODEL", settings.llm_model),
        "timeout_seconds": int(_get_env("FINQA_LLM_TIMEOUT_SECONDS", str(settings.llm_timeout_seconds))),
    }


def _build_messages(query: str, citations: list[dict[str, str]]) -> list[dict[str, str]]:
    evidence_lines = []
    for idx, c in enumerate(citations, start=1):
        evidence_lines.append(
            f"[E{idx}] source_file={c['source_file']} | fiscal_year={c['fiscal_year']} | "
            f"section={c['section']} | paragraph_id={c['paragraph_id']} | quote_en={c['quote_en']}"
        )
    system_prompt = (
        "You are a grounded financial QA assistant. "
        "Use only the provided evidence quotes. "
        "Do not add facts beyond evidence. "
        "Answer in Chinese only."
    )
    user_prompt = (
        f"Question: {query}\n\n"
        "Evidence:\n"
        + "\n".join(evidence_lines)
        + "\n\nOutput constraints:\n"
        "- Provide a concise Chinese answer based only on evidence.\n"
        "- If evidence is insufficient, reply exactly: 证据不足，暂时无法给出可靠回答。"
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


def _call_qwen_chat(query: str, citations: list[dict[str, str]], config: dict[str, str | int]) -> str | None:
    api_key = str(config["api_key"])
    if not api_key:
        return None

    payload = {
        "model": str(config["model"]),
        "messages": _build_messages(query, citations),
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        url=f"{config['base_url']}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=int(config["timeout_seconds"])) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    content_text = str(content).strip()
    if not content_text:
        return None
    return content_text


def generate_answer(query: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
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

    config = _resolve_llm_config()
    answer_zh = ""
    used_llm = False
    if str(config["provider"]) in {"qwen", "openai"}:
        llm_answer = _call_qwen_chat(query, citations, config)
        if llm_answer:
            answer_zh = llm_answer
            used_llm = True

    if not answer_zh:
        answer_zh = _build_answer(citations)

    confidence = min(0.9, 0.5 + 0.1 * len(citations))
    if not used_llm:
        confidence = max(0.5, confidence - 0.15)

    return {
        "answer_zh": answer_zh,
        "confidence": round(confidence, 2),
        "citations": citations,
    }
