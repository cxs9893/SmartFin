# Ingest + Index 迭代记录（阶段一）

## 1. 迭代目标
本阶段聚焦 `finqa ingest/index` 的可落地能力，目标如下：

1. JSON 导入可重复执行，不因已有索引报错。
2. chunk 结构标准化，支持后续 citation 字段消费。
3. BM25 + FAISS 索引可持久化，产物目录结构稳定。
4. 补充最小验证，确保流程可回归。

## 2. 本阶段已完成实现

### 2.1 稳定 JSON 导入（`src/finqa/ingest/pipeline.py`）
1. 支持多种 JSON 载荷形态（list / dict + 常见列表键）。
2. 跳过非法 JSON 文件，避免中断整批 ingest。
3. 文本归一化（空白折叠、去首尾空白）。
4. 统一输出字段：
   - `chunk_id`
   - `doc_id`
   - `source_path`
   - `source_file`
   - `fiscal_year`
   - `section`
   - `paragraph_id`
   - `text`
   - `quote_en`
5. 通过稳定排序与去重（按 `chunk_id`）保证重复运行输出一致。
6. 输出路径固定为：`.finqa/chunks/chunks.jsonl`。

### 2.2 BM25 + FAISS 持久化（`src/finqa/indexing/builder.py`）
1. 从 `chunks.jsonl` 加载标准化 chunk。
2. 构建并持久化 BM25：
   - `index/bm25/bm25.pkl`
   - `index/bm25/documents.jsonl`
3. 构建并持久化 FAISS：
   - `index/faiss/index.faiss`
   - `index/faiss/id_map.json`
4. 写入稳定 manifest（兼容现有 retrieval）：
   - `index/manifest.txt`
5. 写入索引元信息：
   - `index/index_meta.json`

### 2.3 类型扩展（`src/finqa/common/types.py`）
1. `Citation` 增补可选字段：`chunk_id/source_path/doc_id`。
2. 新增 `Chunk` dataclass，统一 chunk 数据契约。

### 2.4 最小验证（`tests/test_ingest_index.py`）
覆盖点：
1. ingest + build 连续执行两次结果一致（幂等性）。
2. 索引目录结构完整存在。
3. `manifest.txt` 指向绝对 `chunks` 路径。
4. retrieval 可读取结果，且命中项包含 citation 所需关键字段。

## 3. 当前稳定产物结构

```text
.finqa/
  chunks/
    chunks.jsonl
  index/
    manifest.txt
    index_meta.json
    bm25/
      bm25.pkl
      documents.jsonl
    faiss/
      index.faiss
      id_map.json
```

## 4. 已执行验证命令与结果

1. 安装测试工具：`python -m pip install pytest`
2. 运行测试：`$env:PYTHONPATH='src'; python -m pytest -q`
3. 结果：`2 passed`（含新增 ingest/index 验证）

## 5. 关联提交

1. `a027613` feat(ingest): stabilize json chunks and persist bm25-faiss indices
2. `65958df` test(ingest): verify idempotent build and stable index layout

## 6. 已知风险与后续迭代建议

1. 现有 retrieval 仍以 `manifest -> chunks.jsonl` 的简化读取为主，尚未接入 BM25/FAISS 实际打分融合。
2. 当前向量为本地哈希 embedding，优先保证稳定可运行；后续可替换为语义 embedding 模型提升效果。
3. 建议下一阶段在 `retrieval` 增加：BM25 分数 + 向量分数融合、top-k 重排、可解释命中原因输出。
