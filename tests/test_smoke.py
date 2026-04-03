from finqa.ingest.pipeline import ingest_directory


def test_import_path_smoke(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "demo.json").write_text('[{"section":"Item 1","text":"hello","fiscal_year":"2024"}]', encoding='utf-8')

    out = ingest_directory(data_dir, tmp_path / ".finqa")
    assert out.exists()
