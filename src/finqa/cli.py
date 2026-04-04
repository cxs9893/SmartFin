from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich import print as rich_print

from finqa.ingest.pipeline import ingest_directory
from finqa.indexing.builder import build_indices
from finqa.qa.generator import generate_answer
from finqa.report.writer import generate_report
from finqa.retrieval.hybrid import hybrid_search

app = typer.Typer(help="SmartFin CLI")


def _emit_json(payload: Any) -> None:
    """Emit UTF-8 JSON safely, even on non-UTF8 Windows consoles."""
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    stream = sys.stdout

    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8")
        except OSError:
            pass

    try:
        stream.write(text)
        stream.flush()
        return
    except UnicodeEncodeError:
        pass

    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        raise
    buffer.write(text.encode("utf-8"))
    buffer.flush()


@app.command("ingest")
def ingest_cmd(
    data_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    out_dir: Path = typer.Option(Path(".finqa")),
) -> None:
    chunks_path = ingest_directory(data_dir, out_dir)
    build_indices(chunks_path, out_dir / "index")
    rich_print(f"[green]Ingest done.[/green] chunks -> {chunks_path}")


@app.command("ask")
def ask_cmd(
    q: str = typer.Option(..., "--q", help="Question text"),
    top_k: int = typer.Option(8, min=1, max=30),
    out: str = typer.Option("text", help="text|json"),
) -> None:
    hits = hybrid_search(Path(".finqa/index"), q, top_k=top_k)
    payload = generate_answer(q, hits)

    if out == "json":
        _emit_json(payload)
        return

    rich_print("[bold]Answer[/bold]")
    rich_print(payload["answer_zh"])
    rich_print("\n[bold]Citations[/bold]")
    for item in payload.get("citations", []):
        rich_print(
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
        _emit_json(payload)
        return

    rich_print("[bold]Report[/bold]")
    rich_print(payload["report_zh"])
    rich_print("\n[bold]Highlights[/bold]")
    for h in payload.get("highlights", []):
        rich_print(f"- {h}")


@app.command("inspect")
def inspect_cmd(
    doc: str = typer.Option(..., help="document filename"),
    section: str = typer.Option("", help="section filter"),
    limit: int = typer.Option(20, min=1, max=200),
) -> None:
    hits = hybrid_search(Path(".finqa/index"), f"{doc} {section}", top_k=limit)
    _emit_json(hits)
