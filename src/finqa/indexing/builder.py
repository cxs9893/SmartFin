from pathlib import Path


def build_indices(chunks_path: Path, index_dir: Path) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "bm25.index").write_text("TODO: bm25 index placeholder\n", encoding="utf-8")
    (index_dir / "vector.index").write_text("TODO: faiss index placeholder\n", encoding="utf-8")
    (index_dir / "manifest.txt").write_text(str(chunks_path), encoding="utf-8")
