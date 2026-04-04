# retrieval 模块迭代记录

## 迭代目标（Iteration Goal）
- 实现 `BM25 + 向量` 的混合检索与融合排序，替代原先“按 chunks 顺序截断返回”的占位实现。
- 输出统一的 `hit/citation` 标准字段，同时兼容 `qa/report` 现有消费字段，保证检索结果可直接被下游调用。
- 提供可配置检索参数（`top_k`、权重、候选召回数量），支持后续调优。

## 本次迭代范围（Scope of This Iteration）
- 范围内（In scope）：
- `src/finqa/retrieval/hybrid.py`：混合检索主逻辑、分数计算、融合排序与结果结构化输出。
- `src/finqa/retrieval/__init__.py`：对外导出 `hybrid_search`。
- `tests/test_retrieval_hybrid.py`：字段契约与权重行为测试。
- 范围外（Out of scope）：
- `ingest/indexing` 的持久化索引格式与构建流程。
- `qa/report` 的主流程逻辑（仅保持向后兼容，不在本迭代修改）。
- 容器与部署流程。

## 已交付功能（Delivered Features）
- 功能 1：混合检索能力
- BM25 词法打分：基于 `rank_bm25.BM25Okapi`。
- 向量打分优先使用 embedding provider（与索引 `index_meta.json` 对齐），对 query + chunks 计算向量相似度。
- embedding 路径不可用时，回退到 FAISS（`faiss/index.faiss` + `id_map.json`）检索分数。
- 无 embedding key 或向量链路异常时，最终回退到 hash 向量方案。
- 双路候选集合合并后按融合分数排序。
- 功能 2：可配置与稳健性处理
- 支持 `top_k`、`bm25_weight`、`vector_weight`、`bm25_top_k`、`vector_top_k`。
- 权重自动归一化；负值会被钳制为 `0`；双权重都为 `0` 时回退默认值。
- 默认融合改为 embedding 优先（`vector_weight=0.6`，`bm25_weight=0.4`）。
- 功能 3：标准化返回契约
- 保留兼容顶层字段：`source_file/fiscal_year/section/paragraph_id/text`。
- 新增标准字段：`hit`、`citation`、`rank`、`score`、`bm25_score`、`vector_score`、`fusion_score`。

## 验收映射（Acceptance Mapping）
- 验收项 A（top-k、权重参数可配置） -> 已实现
- 证据：`hybrid_search(...)` 参数包含 `top_k`、`bm25_weight`、`vector_weight`、`bm25_top_k`、`vector_top_k`。
- 验收项 B（返回结果字段满足合并门槛） -> 已实现
- 证据：每条返回包含 `hit/citation` 标准字段，同时保留下游兼容顶层字段。
- 验收项 C（优先读取真实向量索引） -> 已实现
- 证据：在检索流程中可读取 `faiss/index.faiss`、`faiss/id_map.json`、`index_meta.json`，并以 embedding provider 对齐方式生成 query 向量。
- 验收项 D（无 embedding key 时可 fallback） -> 已实现
- 证据：embedding 模型路径异常时，先尝试 FAISS 路径，再回退 hash 向量打分。
- 验收项 C（至少 1 个检索测试/最小验证） -> 已实现
- 证据：`tests/test_retrieval_hybrid.py` 包含 4 个检索相关测试（字段契约 + 权重行为 + embedding 优先 + fallback）。

## 验证与结果（Validation and Results）
### 测试报告

#### 基础信息
- 分支：`feat/retrieval-hybrid`
- 提交：`8115de6`
- 模块：`retrieval`

#### 执行命令
1. `git status --short --branch`
2. `git rev-parse --short HEAD`
3. `$env:PYTHONPATH='src'; python -m pytest -q tests/test_smoke.py`
4. `$env:PYTHONPATH='src'; python -m pytest -q tests/test_retrieval_hybrid.py`
5. `$env:PYTHONPATH='src'; python -m finqa ask --q "Apple revenue" --out json`

#### 结果汇总
- 总结：`PASS`
- `test_smoke`：`PASS`（`1 passed`）
- `module_tests`：`PASS`（`4 passed`）
- `cli_validation`：`PASS`（命令退出码 `0`，返回 JSON）

#### 验收映射
- 功能可用性：`PASS`（smoke + retrieval 测试通过，CLI 可执行）
- 可追溯字段完整性：`PASS`（`test_retrieval_hybrid.py` 覆盖 `hit/citation` 契约）
- 容器可运行性：`N/A`（本次未执行 `docker-compose`）
- 文档完整性：`N/A`（本次仅执行测试回填）

#### 风险与备注
- 两个 pytest 命令均有 `PytestCacheWarning`（`.pytest_cache` 写入权限），不影响测试通过结论。

## 本迭代提交记录（Commits in This Iteration）
- `43ce817` `feat(检索): 新增 BM25+向量混合检索与融合排序`
- `bc2243e` `test(检索): 增加混合检索结果契约覆盖`
- `3fabc09` `feat(检索): embedding模型优先检索并保留FAISS与hash回退`
- `8115de6` `test(检索): 增加embedding优先与fallback检索测试`

## 已知风险/限制（Known Risks / Limitations）
- 风险 1：embedding 优先路径会在查询时对 chunks 批量向量化，数据量增大时延迟可能上升。
- 风险 2：本地缺少可用 embedding 模型或 key 时，会落回 FAISS/hash，检索质量取决于 fallback 路径。
- 限制 1：未在 retrieval 层引入向量缓存，重复 query 仍会重复计算部分向量。

## 建议下一迭代（Suggested Next Iterations）
- 下一迭代项 1：在 `indexing` 模块落地持久化向量索引（如 FAISS）并接入检索读取。
- 下一迭代项 2：补充检索评估基线（Recall@K / MRR）与参数调优文档。
- 下一迭代项 3：增加候选截断与融合日志，便于线上问题定位与效果回溯。
