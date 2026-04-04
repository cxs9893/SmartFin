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

5. CLI 链路验证
- 至少执行 1 条本模块相关 CLI 命令
- 示例：`finqa ingest ...` / `finqa ask ...` / `finqa report ...`

6. 验收映射
- 将结果映射到验收门槛，逐条标注：`PASS` / `FAIL` / `N/A`

## 4. 执行规范
- 只报告真实执行结果，禁止“推测通过”。
- 失败先给结论，再给日志摘要。
- 每次报告必须包含：运行命令、退出码、关键输出、受影响文件。
- 不跨模块补测试：仅补本任务相关测试。
- 若改动 `src/finqa/<module>/`，必须同步更新 `docs/<module>-iteration.md`。

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

### 验收映射
- 功能可用性：`PASS/FAIL/N/A`（证据：...）
- 可追溯字段完整性：`PASS/FAIL/N/A`（证据：...）
- 容器可运行性：`PASS/FAIL/N/A`（证据：...）
- 文档完整性：`PASS/FAIL/N/A`（证据：...）

### 风险与阻塞
- 风险：
- 阻塞：

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
    "cli_validation": "PASS"
  },
  "acceptance_mapping": [
    {"item": "功能可用性", "status": "PASS", "evidence": "finqa ask 命令返回 0"},
    {"item": "可追溯字段完整性", "status": "PASS", "evidence": "citations 包含 source_file/fiscal_year/section/paragraph_id/quote_en"}
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

4. 容器链路（建议每日至少一次）
- `docker-compose up --build`

5. 合并判定
- 功能可用性：PASS
- 可追溯字段完整性：PASS
- 文档完整性：PASS
- 容器能力：PASS 或已登记 `N/A`（含替代验证与补测计划）
