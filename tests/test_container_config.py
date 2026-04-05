from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_has_runtime_dirs_and_entry_command():
    content = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "WORKDIR /app" in content
    assert "RUN mkdir -p /app/data /app/.finqa" in content
    assert "pip install --no-cache-dir -e \".[embedding,local-llm]\"" in content


def test_compose_runs_ingest_and_report_pipeline():
    content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "env_file" in content
    assert ".env.example" in content
    assert "FINQA_LLM_PROVIDER" in content
    assert "FINQA_LLM_MODEL" in content
    assert "./models:/app/models" in content
    assert "finqa ingest --data-dir /app/data --out-dir /app/.finqa" in content
    assert "finqa report --mode cross_year --out json" in content
    assert "report.json" in content
