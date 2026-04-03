from finqa.qa.generator import generate_answer


def test_generate_answer_grounded_and_refusal():
    query = "What are the risk factors in 2024?"
    hits = [
        {
            "source_file": "AAPL_2024_10K.json",
            "fiscal_year": "2024",
            "section": "Item 1A. Risk Factors",
            "paragraph_id": "Item 1A. Risk Factors-00001",
            "text": "Our business is subject to substantial risks including supply chain disruptions and global economic conditions.",
        }
    ]

    answered = generate_answer(query, hits)
    assert "根据检索到的英文财报证据" in answered["answer_zh"]
    assert answered["confidence"] > 0.0
    assert len(answered["citations"]) == 1

    citation = answered["citations"][0]
    assert citation["source_file"] == "AAPL_2024_10K.json"
    assert citation["fiscal_year"] == "2024"
    assert citation["section"] == "Item 1A. Risk Factors"
    assert citation["paragraph_id"] == "Item 1A. Risk Factors-00001"
    assert citation["quote_en"].startswith("Our business is subject to substantial risks")

    refused = generate_answer(query, [{"section": "Item 1A", "text": ""}])
    assert "证据不足" in refused["answer_zh"]
    assert refused["confidence"] == 0.0
    assert refused["citations"] == []
