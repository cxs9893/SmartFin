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


def test_generate_answer_use_local_model_when_available(monkeypatch):
    monkeypatch.setenv("FINQA_LLM_PROVIDER", "modelscope_local")
    monkeypatch.setenv("FINQA_LLM_MODEL", "models/Qwen2___5-0___5B-Instruct")

    def _fake_local(query, citations, config):
        assert query == "What are the risk factors in 2024?"
        assert len(citations) == 1
        assert config["model"] == "models/Qwen2___5-0___5B-Instruct"
        return "基于证据，2024年主要风险包括供应链中断和宏观经济波动。"

    monkeypatch.setattr(qa_generator, "_call_modelscope_local", _fake_local)

    answered = generate_answer("What are the risk factors in 2024?", VALID_HITS)
    assert answered["answer_zh"].startswith("基于证据")
    assert answered["confidence"] >= 0.6
    assert len(answered["citations"]) == 1


def test_generate_answer_fallback_template_when_local_unavailable(monkeypatch):
    monkeypatch.setenv("FINQA_LLM_PROVIDER", "modelscope_local")

    def _fake_local(query, citations, config):
        _ = (query, citations, config)
        return None

    monkeypatch.setattr(qa_generator, "_call_modelscope_local", _fake_local)

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


def test_call_modelscope_local_skip_remote_when_local_only_and_model_not_local_path():
    out = qa_generator._call_modelscope_local(
        query="q",
        citations=VALID_HITS,
        config={
            "model": "Qwen/Qwen2.5-0.5B-Instruct",
            "device": "cpu",
            "max_new_tokens": 32,
            "local_files_only": True,
        },
    )
    assert out is None
