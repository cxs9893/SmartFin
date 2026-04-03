from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from finqa.ingest.pipeline import ingest_directory
from finqa.indexing.builder import build_indices
from finqa.qa.generator import generate_answer
from finqa.report.writer import generate_report
from finqa.retrieval.hybrid import hybrid_search

app = typer.Typer(help="SmartFin CLI")


@app.command("ingest")
def ingest_cmd(
    data_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    out_dir: Path = typer.Option(Path(".finqa")),
) -> None:
    chunks_path = ingest_directory(data_dir, out_dir)
    build_indices(chunks_path, out_dir / "index")
    print(f"[green]Ingest done.[/green] chunks -> {chunks_path}")


@app.command("ask")
def ask_cmd(
    q: str = typer.Option(..., "--q", help="Question text"),
    top_k: int = typer.Option(8, min=1, max=30),
    out: str = typer.Option("text", help="text|json"),
) -> None:
    hits = hybrid_search(Path(".finqa/index"), q, top_k=top_k)
    payload = generate_answer(q, hits)

    if out == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print("[bold]Answer[/bold]")
    print(payload["answer_zh"])
    print("\n[bold]Citations[/bold]")
    for item in payload.get("citations", []):
        print(
            f"- {item['source_file']} | {item['fiscal_year']} | {item['section']} | {item['paragraph_id']}"
        )


@app.command("report")
def report_cmd(
    mode: str = typer.Option("cross_year", help="cross_year|single_year"),
    top_k: int = typer.Option(12, min=1, max=50),
    out: str = typer.Option("text", help="text|json"),
) -> None:
    hits = hybrid_search(Path(".finqa/index"), "report", top_k=top_k)
    payload = generate_report(mode, hits)
    if out == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print("[bold]Report[/bold]")
    print(payload["report_zh"])
    print("\n[bold]Highlights[/bold]")
    for h in payload.get("highlights", []):
        print(f"- {h}")


@app.command("inspect")
def inspect_cmd(
    doc: str = typer.Option(..., help="document filename"),
    section: str = typer.Option("", help="section filter"),
    limit: int = typer.Option(20, min=1, max=200),
) -> None:
    hits = hybrid_search(Path(".finqa/index"), f"{doc} {section}", top_k=limit)
    print(json.dumps(hits, ensure_ascii=False, indent=2))
