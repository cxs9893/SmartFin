from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from finqa.common.settings import settings


_REFUSAL_MESSAGE = "证据不足，暂时无法给出可靠回答。"
_ENGLISH_RE = re.compile(r"[A-Za-z]")
_MODEL_CACHE: dict[str, tuple[Any, Any, str]] = {}


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


def _build_template_answer(citations: list[dict[str, str]]) -> str:
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


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_llm_config() -> dict[str, str | int]:
    return {
        "provider": _get_env("FINQA_LLM_PROVIDER", settings.llm_provider).lower(),
        "model": _get_env("FINQA_LLM_MODEL", settings.llm_model),
        "device": _get_env("FINQA_LLM_DEVICE", settings.llm_device),
        "max_new_tokens": int(_get_env("FINQA_LLM_MAX_NEW_TOKENS", str(settings.llm_max_new_tokens))),
        "local_files_only": _to_bool(
            _get_env("FINQA_LLM_LOCAL_FILES_ONLY", str(settings.llm_local_files_only))
        ),
    }


def _build_messages(query: str, citations: list[dict[str, str]]) -> list[dict[str, str]]:
    evidence_lines = []
    for idx, c in enumerate(citations, start=1):
        evidence_lines.append(
            f"[E{idx}] source_file={c['source_file']} | fiscal_year={c['fiscal_year']} | "
            f"section={c['section']} | paragraph_id={c['paragraph_id']} | quote_en={c['quote_en']}"
        )

    system_prompt = (
        "你是财报问答助手。你只能使用给定证据作答，不能引入任何证据之外的信息。"
        "如证据不足必须回答：证据不足，暂时无法给出可靠回答。"
        "输出中文。"
    )
    user_prompt = (
        f"问题：{query}\n\n"
        "证据如下：\n"
        + "\n".join(evidence_lines)
        + "\n\n请基于证据给出简洁中文答案。"
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


def _call_modelscope_local(
    query: str,
    citations: list[dict[str, str]],
    config: dict[str, str | int],
) -> str | None:
    model_ref = str(config["model"]).strip()
    if not model_ref:
        return None
    local_files_only = bool(config["local_files_only"])

    model_path = Path(model_ref)
    is_local_path = model_path.exists()
    if local_files_only and not is_local_path:
        return None

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception:
        return None

    device_pref = str(config["device"]).lower()
    if device_pref == "cpu":
        device = "cpu"
    elif device_pref == "cuda":
        device = "cuda"
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    cache_key = f"{model_ref}::{device}::{int(local_files_only)}"
    cached = _MODEL_CACHE.get(cache_key)
    if cached is None:
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_ref, trust_remote_code=True, local_files_only=local_files_only
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_ref, trust_remote_code=True, local_files_only=local_files_only
            )
        except Exception:
            return None
        if device == "cuda":
            model = model.to("cuda")
        _MODEL_CACHE[cache_key] = (tokenizer, model, device)
        cached = _MODEL_CACHE[cache_key]

    tokenizer, model, device = cached
    messages = _build_messages(query, citations)

    try:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}\n\n回答："

    try:
        inputs = tokenizer(prompt, return_tensors="pt")
        if device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        outputs = model.generate(
            **inputs,
            max_new_tokens=int(config["max_new_tokens"]),
            do_sample=False,
            temperature=0.0,
        )
        generated = outputs[0][inputs["input_ids"].shape[1] :]
        answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
    except Exception:
        return None

    if not answer:
        return None
    return answer


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
    if str(config["provider"]) in {"modelscope_local", "local"}:
        llm_answer = _call_modelscope_local(query, citations, config)
        if llm_answer:
            answer_zh = llm_answer
            used_llm = True

    if not answer_zh:
        answer_zh = _build_template_answer(citations)

    confidence = min(0.9, 0.5 + 0.1 * len(citations))
    if not used_llm:
        confidence = max(0.5, confidence - 0.15)

    return {
        "answer_zh": answer_zh,
        "confidence": round(confidence, 2),
        "citations": citations,
    }
