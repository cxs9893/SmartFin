from __future__ import annotations

import types

import numpy as np

from finqa.common.settings import Settings
from finqa.indexing.embeddings import embed_texts


def test_bge_embedding_success_path_with_mock(monkeypatch):
    class FakeSentenceTransformer:
        def __init__(self, model, device=None, trust_remote_code=False, local_files_only=True):
            self.model = model
            self.device = device
            self.trust_remote_code = trust_remote_code
            self.local_files_only = local_files_only

        def encode(
            self,
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ):
            # Deterministic 3-dim mock vectors for 2 texts.
            return np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    fake_module = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", fake_module)

    cfg = Settings(
        _env_file=None,
        embedding_provider="bge",
        embedding_bge_model="mock-bge-model",
        embedding_bge_local_files_only=True,
        embedding_strict_mode=True,
    )

    vectors, info = embed_texts(["alpha", "beta"], cfg)

    assert vectors.shape == (2, 3)
    assert info.provider == "bge"
    assert info.requested_provider == "bge"
    assert info.dim == 3
    assert info.fallback_from is None
    assert info.fallback_reason is None
