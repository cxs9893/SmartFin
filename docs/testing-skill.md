# SmartFin 测试 Skill（标准版）

## 1. Skill 目标
- 面向模块迭代（`ingest` / `retrieval` / `qa` / `report`）提供统一测试流程。
- 保障测试结果可复现、可追溯、可用于合并验收。

## 2. 输入约定
- 分支与模块：例如 `feat/retrieval-hybrid` + `retrieval`
- 改动范围：涉及文件列表
- 验收依据：`docs/development-flow.md` 中“完整合并验收门槛”
- 可执行命令：`pytest`、`finqa ...`、`docker-compose ...`

## 3. 测试步骤（按顺序）
1. 环境确认
- `git status --short --branch`
- `git rev-parse --short HEAD`
- 若涉及本地 LLM：
  - 依赖检查：`python -c "import torch, transformers, modelscope; print('ok')"`
  - 模型目录检查：确认 `FINQA_LLM_MODEL` 指向路径存在（或模型 ID 可下载）
  - 代理检查：确认 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` 不会阻断模型下载

2. 变更定位
- `git diff --name-only HEAD~1..HEAD`（或当前工作区改动）
- 识别受影响模块：`src/finqa/<module>/`、`tests/`

3. 快速回归
- `pytest -q tests/test_smoke.py`
- 若失败，标记阻塞并停止“通过结论”输出

4. 模块专项测试
- `ingest/indexing`：`pytest -q tests/test_ingest_index.py`
- `retrieval`：`pytest -q tests/test_retrieval_hybrid.py`
- `qa/report`：执行对应测试文件或最小验证命令
- 若改动包含 embedding/provider，必须补充：
- Provider 正常路径验证（本地模型可用）
- Fallback 路径验证（模型缺失或依赖缺失时流程不中断）
- `qa(本地LLM)`：至少覆盖两条路径
  - 路径 A：本地模型可用（真实目录或 mock 调用）
  - 路径 B：本地模型不可用时 fallback 模板回答
- `qa(拒答)`：无有效证据时必须拒答，且结构不变（`answer_zh/confidence/citations`）

5. CLI 链路验证
- 至少执行 1 条本模块相关 CLI 命令
- 示例：`finqa ingest ...` / `finqa ask ...` / `finqa report ...`
- 若模块接入本地 LLM，CLI 建议按场景执行：
  - 场景 A：`FINQA_LLM_PROVIDER=modelscope_local` 且本地模型目录可用
  - 场景 B：本地模型不可用（或禁用），验证 fallback 路径

6. 验收映射
- 将结果映射到验收门槛，逐条标注：`PASS` / `FAIL` / `N/A`
- 若模块接入本地 LLM，新增验收项：
  - `本地模型可用性`
  - `降级稳定性（fallback + 拒答）`

## 4. 执行规范
- 只报告真实执行结果，禁止“推测通过”。
- 失败先给结论，再给日志摘要。
- 每次报告必须包含：运行命令、退出码、关键输出、受影响文件。
- 不跨模块补测试：仅补本任务相关测试。
- 若改动 `src/finqa/<module>/`，必须同步更新 `docs/<module>-iteration.md`。
- 若改动包含 embedding/provider，报告必须包含 `index_meta.json` 关键字段校验结果。

## 5. 标准输出结构（Markdown）
```md
## 测试报告

### 基础信息
- 分支：
- 提交：
- 模块：
- 测试时间：

### 执行命令
1. `<command-1>`
2. `<command-2>`

### 结果汇总
- 总结：`PASS` / `FAIL`
- 明细：
- `test_smoke`：
- `module_tests`：
- `cli_validation`：
- `embedding_provider_path`：
- `embedding_fallback_path`：

### 验收映射
- 功能可用性：`PASS/FAIL/N/A`（证据：...）
- 可追溯字段完整性：`PASS/FAIL/N/A`（证据：...）
- 本地模型可用性：`PASS/FAIL/N/A`（证据：模型加载或最小推理命令）
- 降级稳定性：`PASS/FAIL`（证据：fallback 命令/测试结果）
- 容器可运行性：`PASS/FAIL/N/A`（证据：...）
- 文档完整性：`PASS/FAIL/N/A`（证据：...）

### 风险与阻塞
- 风险：
- 阻塞：
- 环境变量快照（脱敏）：
- `FINQA_EMBEDDING_PROVIDER`
- `FINQA_EMBEDDING_BGE_MODEL`
- `FINQA_EMBEDDING_BGE_LOCAL_FILES_ONLY`
- `FINQA_EMBEDDING_HASH_DIM`

### 建议下一步
1. ...
2. ...
```

## 6. 标准输出结构（JSON）
```json
{
  "branch": "feat/xxx",
  "commit": "abc1234",
  "module": "retrieval",
  "timestamp": "2026-04-04T00:00:00+08:00",
  "commands": [
    {"cmd": "pytest -q tests/test_smoke.py", "exit_code": 0},
    {"cmd": "pytest -q tests/test_retrieval_hybrid.py", "exit_code": 0}
  ],
  "summary": {
    "status": "PASS",
    "smoke": "PASS",
    "module_tests": "PASS",
    "cli_validation": "PASS",
    "local_model_path_check": "PASS",
    "local_model_infer_check": "PASS",
    "fallback_path_check": "PASS",
    "proxy_env_check": "PASS"
  },
  "acceptance_mapping": [
    {"item": "功能可用性", "status": "PASS", "evidence": "finqa ask 命令返回 0"},
    {"item": "可追溯字段完整性", "status": "PASS", "evidence": "citations 包含 source_file/fiscal_year/section/paragraph_id/quote_en"},
    {"item": "本地模型可用性", "status": "PASS", "evidence": "模型路径存在且可完成最小推理"},
    {"item": "降级稳定性", "status": "PASS", "evidence": "本地模型不可用时仍可 fallback 与拒答"}
  ],
  "risks": [],
  "blockers": [],
  "next_steps": ["补充边界用例", "执行容器链路验证"]
}
```

## 7. 使用方式（细化：强制 vs 建议）
### 7.1 强制执行（必须）
- 触发条件：
- 改动命中 `src/finqa/<module>/` 任意代码文件。
- 改动命中 `tests/` 且会影响既有测试结论。
- 分支准备合并到 `main`。

- 必做项：
1. 执行第 3 节的 `1~6` 全流程。
2. 在对应 `docs/<module>-iteration.md` 更新 `Validation and Results`。
3. 在结果中给出命令、退出码、关键输出摘要。
4. 对验收门槛逐条给出 `PASS/FAIL/N/A`。
5. 若存在 `FAIL`，必须写入“风险与阻塞”，禁止标注“可直接合并”。
6. 若改动 embedding/provider，必须在报告中校验 `index_meta.json`：
- `embedding_provider`
- `embedding_model`
- `embedding_dim`
- `embedding_requested_provider`
- 若 fallback：`embedding_fallback_from` / `embedding_fallback_reason`

### 7.2 建议执行（推荐）
- 触发条件：
- 仅文档改动（`docs/`）或注释改动，不影响运行逻辑。
- 非合并节点的中间开发自测。

- 推荐项：
1. 至少执行 `test_smoke`。
2. 模块专项测试可按风险抽样执行。
3. JSON 结构化输出可选（用于自动化流水线时再启用）。

### 7.3 例外处理（需显式说明）
- 不可执行项（例如本机无 Docker、外部服务不可达）允许标记 `N/A`。
- 但必须写清：
- 无法执行原因
- 影响范围
- 替代验证方式（如最小 CLI 验证）
- 后续补测计划
- 对于本地模型下载/加载失败，必须额外写清：
- 是否网络/代理导致
- 是否已验证 fallback 可用
- 后续如何恢复 provider 正常路径（例如本地模型目录预置）
- 若本地模型下载受网络或代理限制，可将“本地模型可用性”标记 `N/A`，
  但必须提供 fallback/拒答路径通过证据与后续补测计划。

## 8. 全量验收建议（Main Merge Gate）
1. 基础回归
- `python -m pytest -q tests/test_smoke.py`

2. 模块专项
- `python -m pytest -q tests/test_ingest_index.py`
- `python -m pytest -q tests/test_retrieval_hybrid.py`
- 其他模块按对应测试补齐

3. CLI 最小链路
- `python -m finqa ingest --data-dir data --out-dir .finqa_ci`
- `python -m finqa ask --q "revenue" --out json`
- `python -m finqa report --mode cross_year --out json`

4. Embedding 元信息校验（改动 embedding/provider 时强制）
- 校验 `index_meta.json` 含 `embedding_provider/model/dim/requested_provider`
- 若 provider 与 requested_provider 不一致，必须登记 fallback 原因
- Provider/Fallback 双路径至少覆盖其一，另一条可标注 `N/A` 但需说明

5. 容器链路（建议每日至少一次）
- `docker-compose up --build`

6. 合并判定
- 功能可用性：PASS
- 可追溯字段完整性：PASS
- 文档完整性：PASS
- 容器能力：PASS 或已登记 `N/A`（含替代验证与补测计划）
