# Retrieval Hybrid Iteration Notes

## 1. Iteration Goal
Implement hybrid retrieval with BM25 + vector scoring and fused ranking, while keeping compatibility for direct use by qa/report modules.

## 2. Scope of This Iteration
- Added hybrid retrieval logic in `src/finqa/retrieval/hybrid.py`
- Exposed retrieval entry in `src/finqa/retrieval/__init__.py`
- Added retrieval contract tests in `tests/test_retrieval_hybrid.py`

## 3. Delivered Features
### 3.1 Hybrid Retrieval
- Two channels:
  - BM25 lexical scoring (`rank_bm25`)
  - Lightweight vector scoring (hashed embedding + cosine similarity)
- Candidate recall from both channels, then merged and re-ranked by fusion score.

### 3.2 Configurable Parameters
`hybrid_search(...)` supports:
- `top_k`
- `bm25_weight`
- `vector_weight`
- `bm25_top_k`
- `vector_top_k`

Weight normalization behavior:
- negative values are clamped to `0`
- if both weights are `0`, fallback to defaults (`0.6 / 0.4`)

### 3.3 Standardized Output Contract
Each returned item includes:
- Backward-compatible top-level fields:
  - `source_file`, `fiscal_year`, `section`, `paragraph_id`, `text`
- Standard retrieval contract fields:
  - `hit`, `citation`, `rank`, `score`, `bm25_score`, `vector_score`, `fusion_score`

`citation` fields:
- `source_file`, `fiscal_year`, `section`, `paragraph_id`, `quote_en`

## 4. Acceptance Mapping
### Requirement 1: configurable top-k and weights
- Satisfied via function arguments and internal normalization.

### Requirement 2: output fields align with merge acceptance
- Satisfied by preserving original top-level fields for qa/report and adding explicit `hit/citation` contract fields.

### Requirement 3: at least one retrieval test/minimal validation
- Added `tests/test_retrieval_hybrid.py`:
  - field contract and ranking assertions
  - weight effect behavior assertions (via monkeypatch score control)

## 5. Validation and Results
Command used:
```bash
PYTHONPATH=src pytest -q tests/test_retrieval_hybrid.py tests/test_smoke.py
```

Observed result:
- `3 passed, 1 warning`
- warning is about pytest cache write permission and does not affect retrieval logic.

## 6. Commits in This Iteration
1. `c0a45b4` feat(retrieval): add hybrid bm25-vector fusion search
2. `9363384` test(retrieval): add hybrid retrieval contract coverage

## 7. Known Risks / Limitations
- Vector retrieval is currently a lightweight hashed embedding approximation, not a persisted FAISS index.
- Ranking quality may be lower than production-grade semantic retrieval.
- No index-time vector cache yet; embedding is computed at query-time.

## 8. Suggested Next Iterations
1. Introduce persisted vector index in indexing module and load it in retrieval path.
2. Add retrieval metrics benchmark (Recall@K, MRR, nDCG) on a fixed eval set.
3. Add query-time diagnostics for score contribution (`bm25` vs `vector`) for tuning.
4. Promote retrieval config to centralized settings/env for easier deployment tuning.
