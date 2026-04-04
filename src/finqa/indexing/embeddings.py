from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import blake2b

import numpy as np

from finqa.common.settings import Settings

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(slots=True)
class EmbeddingInfo:
    provider: str
    model: str
    dim: int
    requested_provider: str
    fallback_from: str | None = None
    fallback_reason: str | None = None


class EmbeddingProvider:
    name: str
    model: str
    dim: int

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int) -> None:
        self.name = "hash"
        self.model = f"hash-{dim}"
        self.dim = dim

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [tok.lower() for tok in _TOKEN_RE.findall(text)]

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in self._tokenize(text):
            digest = blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            mat[i] = self._embed_one(text)
        return mat


class BGELocalEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str,
        dim_hint: int,
        batch_size: int,
        device: str,
        local_files_only: bool,
        trust_remote_code: bool,
    ) -> None:
        self.name = "bge"
        self.model = model
        self.dim = dim_hint
        self._batch_size = max(1, batch_size)
        self._device = device
        self._local_files_only = local_files_only
        self._trust_remote_code = trust_remote_code

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence_transformers_not_installed;"
                "run: python -m pip install sentence-transformers"
            ) from exc

        try:
            model = SentenceTransformer(
                self.model,
                device=self._device,
                trust_remote_code=self._trust_remote_code,
                local_files_only=self._local_files_only,
            )
        except Exception as exc:
            raise RuntimeError(
                f"local_model_load_failed:{exc};"
                "hint: run scripts/download_bge.ps1 and set FINQA_EMBEDDING_BGE_MODEL"
            ) from exc

        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        mat = np.asarray(vectors, dtype=np.float32)
        if mat.ndim != 2 or mat.shape[0] != len(texts):
            raise RuntimeError("unexpected_embedding_shape")

        self.dim = int(mat.shape[1])
        return mat


def _make_hash_provider(cfg: Settings) -> HashEmbeddingProvider:
    return HashEmbeddingProvider(dim=max(8, int(cfg.embedding_hash_dim)))


def _make_primary_provider(cfg: Settings) -> EmbeddingProvider:
    provider = cfg.embedding_provider.strip().lower()
    if provider == "hash":
        return _make_hash_provider(cfg)
    if provider == "bge":
        return BGELocalEmbeddingProvider(
            model=cfg.embedding_bge_model,
            dim_hint=max(8, int(cfg.embedding_bge_dim)),
            batch_size=max(1, int(cfg.embedding_batch_size)),
            device=cfg.embedding_bge_device,
            local_files_only=bool(cfg.embedding_bge_local_files_only),
            trust_remote_code=bool(cfg.embedding_bge_trust_remote_code),
        )

    raise RuntimeError(f"unsupported_provider:{provider}")


def embed_texts(texts: list[str], cfg: Settings) -> tuple[np.ndarray, EmbeddingInfo]:
    requested_provider = cfg.embedding_provider.strip().lower()
    try:
        provider = _make_primary_provider(cfg)
        vectors = provider.embed_texts(texts)
        info = EmbeddingInfo(
            provider=provider.name,
            model=provider.model,
            dim=int(vectors.shape[1]) if vectors.size else provider.dim,
            requested_provider=requested_provider,
        )
        return vectors, info
    except Exception as exc:
        fallback = _make_hash_provider(cfg)
        vectors = fallback.embed_texts(texts)
        info = EmbeddingInfo(
            provider=fallback.name,
            model=fallback.model,
            dim=int(vectors.shape[1]) if vectors.size else fallback.dim,
            requested_provider=requested_provider,
            fallback_from=requested_provider,
            fallback_reason=str(exc),
        )
        return vectors, info
