# ingest 模块迭代记录

## 迭代目标（Iteration Goal）
- 本次迭代聚焦将 `finqa ingest` 从占位流程升级为可持续迭代的稳定基础能力：支持多形态 JSON 导入、统一 chunk 标准化、以及 BM25 + FAISS 索引持久化。
- 预期收益：`ingest` 可重复执行且不因已有索引报错，产物目录结构固定，后续 `retrieval/qa/report` 可以直接消费统一字段。

## 本次迭代范围（Scope of This Iteration）
- 范围内（In scope）：
  - `src/finqa/ingest/pipeline.py`：JSON 解析容错、字段归一化、稳定 chunk 产出。
  - `src/finqa/indexing/builder.py`：BM25 与 FAISS 索引构建与落盘。
  - `src/finqa/common/types.py`：补充 citation/chunk 类型字段。
  - `tests/test_ingest_index.py`：最小可回归验证。
- 范围外（Out of scope）：
  - `retrieval` 的实际 BM25/向量融合检索逻辑。
  - `qa/report` 的生成逻辑升级。
  - Docker 与 README 主体改造。

## 已交付功能（Delivered Features）
- 功能 1：稳定 JSON 导入与 chunk 标准化
  - 支持 `list` 与 `dict` 多种载荷，兼容 `sections/data/records/items/chunks` 等常见键。
  - 非法 JSON 自动跳过，避免整批中断。
  - 统一输出字段：`chunk_id/doc_id/source_path/source_file/fiscal_year/section/paragraph_id/text/quote_en`。
  - 输出固定路径：`.finqa/chunks/chunks.jsonl`，并通过去重+排序保证重复执行结果稳定。
- 功能 2：BM25 + FAISS 索引持久化
  - 索引目录固定为：`.finqa/index/`。
  - 落盘产物：
    - `bm25/bm25.pkl`
    - `bm25/documents.jsonl`
    - `faiss/index.faiss`
    - `faiss/id_map.json`
    - `manifest.txt`
    - `index_meta.json`
  - 每次构建覆盖更新，不依赖“首次执行”前提。
- 功能 3：citation 结构前置补齐
  - `Citation` 类型新增可选字段：`chunk_id/source_path/doc_id`。
  - 新增 `Chunk` dataclass，明确数据契约，便于后续模块消费。
- 功能 4：本地 BGE embedding 接入与自动回退
  - 新增 embedding provider 抽象：`bge`（本地模型）+ `hash`（fallback）。
  - `build_indices` 使用真实向量构建 FAISS，支持落盘复用。
  - `index_meta.json` 增加 `embedding_provider/embedding_model/embedding_dim/embedding_requested_provider`。
  - 当本地模型缺失或加载失败时自动回退到 `hash`，不中断 ingest/index 流程。

## 验收映射（Acceptance Mapping）
- 验收项 A（可重复执行，不因已有索引报错） -> 实现/证据：
  - ingest/index 均采用 `mkdir(..., exist_ok=True)` 与覆盖式写入；
  - `tests/test_ingest_index.py` 中连续执行两次 ingest+build，断言输出一致且流程成功。
- 验收项 B（产物目录结构稳定，可被 retrieval 消费） -> 实现/证据：
  - 固定生成 `.finqa/chunks/chunks.jsonl` 与 `.finqa/index/*`；
  - `manifest.txt` 指向绝对 chunks 路径，兼容现有 retrieval。
- 验收项 C（输出 citation 所需字段） -> 实现/证据：
  - chunk 写入包含 `source_file/fiscal_year/section/paragraph_id/quote_en`，并补充 `chunk_id/source_path/doc_id`；
  - 测试断言检索返回命中包含关键字段。

## 验证与结果（Validation and Results）
- 命令：
  - `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests/test_ingest_index.py`
  - `$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests/test_embeddings.py`
  - `$env:PYTHONPATH='src'; python -m finqa ingest --data-dir data --out-dir .finqa`
- 结果：
  - `test_ingest_index.py`：`1 passed`
  - `test_embeddings.py`：`1 passed`（覆盖本地 BGE 成功路径）。
  - CLI 验证成功，`.finqa/chunks/chunks.jsonl` 产出 `150` 条 chunk。
  - `.finqa/index/index_meta.json` 显示：
    - `embedding_provider=bge`
    - `embedding_model=models/bge-base-zh-v1.5`
    - `embedding_dim=768`
    - `embedding_requested_provider=bge`

## 本迭代提交记录（Commits in This Iteration）
- `a027613` `feat(ingest): stabilize json chunks and persist bm25-faiss indices`
- `65958df` `test(ingest): verify idempotent build and stable index layout`
- `95f8422` `docs: 新增ingest与索引迭代结果文档`
- `3a40bc9` `feat(ingest): 支持SQL键结构JSON与SEC字段映射`
- `6d6cf1a` `test(ingest): 对齐混合检索输出契约并补充SQL键结构用例`
- `853388c` `feat: 接入本地BGE嵌入并补充模型获取与回退机制`
- `9fa0571` `feat(indexing): 新增embedding可选依赖与BGE成功路径测试`

## 已知风险/限制（Known Risks / Limitations）
- 风险 1：当前 retrieval 主路径仍偏向 `manifest -> chunks` 的简化读取，尚未充分消费 BM25/FAISS 分数融合。
- 风险 2：本地 BGE 模型目录不存在或损坏时会回退到 `hash`，可用性有保障但语义召回质量下降。
- 限制 1：Windows 下 `pytest` 缓存目录可能出现权限噪声，当前通过 `-p no:cacheprovider` 规避。

## 建议下一迭代（Suggested Next Iterations）
- 下一迭代项 1（协作 `retrieval` 模块）：接入 BM25 + 向量双路召回与归一化融合，并统一 `hit/citation` 输出契约与打分解释字段。
- 下一迭代项 2（协作 `qa` 模块）：基于新的检索契约升级 grounded answer 组装逻辑，保证“有证据回答/无证据拒答”与 citation 一致性。
- 下一迭代项 3（协作 `report` 模块）：对接跨年聚合所需的稳定 chunk 元数据，优化 `single_year/cross_year` 的证据筛选与摘要输入。
- 下一迭代项 4（协作 `docker`/交付模块）：补齐容器内端到端链路验收（`ingest -> ask/report`），并将命令与结果回填到迭代文档。
- 下一迭代项 5（能力增强，非协作项）：补充 embedding 质量评估基准（命中率/召回率）并建立固定评测集。
- 下一迭代项 6（能力增强，非协作项）：完善“模型获取说明入库、模型本体不入库”的自动化校验（pre-commit/CI）。
