import finqa.qa.generator as qa_generator
from finqa.qa.generator import generate_answer


VALID_HITS = [
    {
        "source_file": "AAPL_2024_10K.json",
        "fiscal_year": "2024",
        "section": "Item 1A. Risk Factors",
        "paragraph_id": "Item 1A. Risk Factors-00001",
        "text": "Our business is subject to substantial risks including supply chain disruptions and global economic conditions.",
    }
]


def test_generate_answer_use_llm_when_key_present(monkeypatch):
    monkeypatch.setenv("FINQA_LLM_PROVIDER", "qwen")
    monkeypatch.setenv("FINQA_LLM_API_KEY", "dummy-key")

    def _fake_call(query, citations, config):
        assert query == "What are the risk factors in 2024?"
        assert len(citations) == 1
        assert config["model"] == "qwen3-max-2026-01-23"
        return "基于证据，2024年主要风险包括供应链中断和宏观经济波动。"

    monkeypatch.setattr(qa_generator, "_call_qwen_chat", _fake_call)

    answered = generate_answer("What are the risk factors in 2024?", VALID_HITS)
    assert answered["answer_zh"].startswith("基于证据")
    assert answered["confidence"] >= 0.6
    assert len(answered["citations"]) == 1


def test_generate_answer_fallback_template_when_no_key(monkeypatch):
    monkeypatch.setenv("FINQA_LLM_PROVIDER", "qwen")
    monkeypatch.delenv("FINQA_LLM_API_KEY", raising=False)

    answered = generate_answer("What are the risk factors in 2024?", VALID_HITS)
    assert "根据检索到的英文财报证据" in answered["answer_zh"]
    assert "证据[1]" in answered["answer_zh"]
    assert answered["confidence"] > 0.0
    assert len(answered["citations"]) == 1


def test_generate_answer_refuse_without_complete_english_evidence():
    query = "What are the risk factors in 2024?"
    hits = [
        {"section": "Item 1A", "text": ""},
        {
            "source_file": "AAPL_2024_10K.json",
            "fiscal_year": "2024",
            "section": "Item 1A. Risk Factors",
            "paragraph_id": "Item 1A. Risk Factors-00001",
            "text": "仅中文内容，不满足英文引用要求",
        },
    ]

    refused = generate_answer(query, hits)
    assert "证据不足" in refused["answer_zh"]
    assert refused["confidence"] == 0.0
    assert refused["citations"] == []
