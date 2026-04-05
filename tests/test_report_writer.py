from finqa.report.writer import generate_report


def _sample_hits():
    return [
        {
            "source_file": "aapl_2024.json",
            "fiscal_year": "2024",
            "section": "Risk Factors",
            "paragraph_id": "rf-1",
            "text": "Supply chain disruptions and macro uncertainty remained key risks.",
        },
        {
            "source_file": "aapl_2024.json",
            "fiscal_year": "2024",
            "section": "MD&A",
            "paragraph_id": "mda-1",
            "text": "Revenue mix shifted toward services while gross margin improved.",
        },
        {
            "source_file": "aapl_2023.json",
            "fiscal_year": "2023",
            "section": "Risk Factors",
            "paragraph_id": "rf-2",
            "text": "Foreign exchange volatility affected reported net sales.",
        },
    ]


def test_generate_report_cross_year_structured():
    payload = generate_report("cross_year", _sample_hits())

    assert payload["mode"] == "cross_year"
    assert payload["summary"]["year_count"] == 2
    assert payload["summary"]["evidence_count"] == 3
    assert payload["summary"]["selected_year"] is None
    assert len(payload["yearly_breakdown"]) == 2
    assert payload["yearly_breakdown"][0]["fiscal_year"] == "2024"
    assert payload["evidence"][0]["source_file"] == "aapl_2024.json"
    assert payload["pipeline"]["embedding_provider"]
    assert payload["pipeline"]["llm_provider"]


def test_generate_report_single_year_filters_latest():
    payload = generate_report("single_year", _sample_hits())

    assert payload["mode"] == "single_year"
    assert payload["summary"]["selected_year"] == "2024"
    assert payload["summary"]["year_count"] == 1
    assert payload["summary"]["evidence_count"] == 2
    assert len(payload["yearly_breakdown"]) == 1
    assert payload["yearly_breakdown"][0]["fiscal_year"] == "2024"
    assert all(item["fiscal_year"] == "2024" for item in payload["evidence"])


def test_generate_report_empty_hits():
    payload = generate_report("single_year", [])

    assert payload["mode"] == "single_year"
    assert payload["summary"]["evidence_count"] == 0
    assert payload["yearly_breakdown"] == []
    assert payload["evidence"] == []


def test_generate_report_llm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FINQA_ENABLE_LLM", raising=False)

    payload = generate_report("cross_year", _sample_hits())

    assert payload["pipeline"]["llm_enabled"] is False
    assert payload["pipeline"]["llm_active"] is False
    assert payload["llm_error"] is None


def test_generate_report_local_llm_enabled_but_model_missing(monkeypatch):
    monkeypatch.setenv("FINQA_ENABLE_LLM", "1")
    monkeypatch.setenv("FINQA_LLM_PROVIDER", "modelscope_local")
    monkeypatch.setenv("FINQA_LLM_LOCAL_FILES_ONLY", "true")
    monkeypatch.setenv("FINQA_LLM_MODEL", "models/not-exist")

    payload = generate_report("cross_year", _sample_hits())

    assert payload["pipeline"]["llm_active"] is True
    assert payload["llm_error"] is not None
    assert "本地模型不存在" in payload["llm_error"]
