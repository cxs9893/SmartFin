# Model Acquisition and Local Directory Rules

## Goal
- Keep only model acquisition instructions in git.
- Store model binaries in local cache directories, not in the repository history.

## Recommended Local Path
- `models/bge-base-zh-v1.5`

## Recommended Environment Variables
- `FINQA_EMBEDDING_PROVIDER=bge`
- `FINQA_EMBEDDING_BGE_MODEL=models/bge-base-zh-v1.5`
- `FINQA_EMBEDDING_BGE_LOCAL_FILES_ONLY=true`
- `FINQA_EMBEDDING_BGE_DEVICE=cpu`

## One-Click Download (ModelScope)
Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_bge.ps1
```

Custom example:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_bge.ps1 `
  -ModelId AI-ModelScope/bge-base-zh-v1.5 `
  -OutputDir models/bge-base-zh-v1.5 `
  -MaxWorkers 1
```

## Verify Model Activation
```powershell
$env:PYTHONPATH='src'
$env:FINQA_EMBEDDING_PROVIDER='bge'
$env:FINQA_EMBEDDING_BGE_MODEL='models/bge-base-zh-v1.5'
$env:FINQA_EMBEDDING_BGE_LOCAL_FILES_ONLY='true'
python -m finqa ingest --data-dir data --out-dir .finqa
Get-Content .finqa/index/index_meta.json
```

Expected fields in `index_meta.json`:
- `embedding_provider: "bge"`
- `embedding_model: "models/bge-base-zh-v1.5"` (or absolute path)

## Fallback Behavior
- If local model loading fails, indexing falls back to `hash` automatically.
- Check `embedding_fallback_reason` in `index_meta.json` for the exact reason.

## QA Local LLM (Qwen)
### Recommended Local Path
- `models/Qwen2___5-0___5B-Instruct`

### Recommended Environment Variables
- `FINQA_LLM_PROVIDER=modelscope_local`
- `FINQA_LLM_MODEL=models/Qwen2___5-0___5B-Instruct`
- `FINQA_LLM_DEVICE=auto`
- `FINQA_LLM_MAX_NEW_TOKENS=192`
- `FINQA_LLM_LOCAL_FILES_ONLY=true`

### Verify QA LLM Activation
```powershell
$env:PYTHONPATH='src'
$env:FINQA_LLM_PROVIDER='modelscope_local'
$env:FINQA_LLM_MODEL='models/Qwen2___5-0___5B-Instruct'
$env:FINQA_LLM_LOCAL_FILES_ONLY='true'
python -m finqa ask --q "What are the risk factors in 2024?" --out json
```

### Notes
- QA path is offline-first by default (`local_files_only=true`), and does not require HuggingFace network access.
- If local model loading fails, QA falls back to grounded template answer and still keeps `answer_zh/confidence/citations` contract.
