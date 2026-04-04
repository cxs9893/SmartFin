# SmartFin 测试 Skill（标准版）

## 1. Skill 目标
- 面向任一模块迭代（`ingest` / `retrieval` / `qa` / `report`）提供统一测试执行方式。
- 输出可直接用于合并验收：步骤可复现、结果可追溯、结论可比较。

## 2. 输入约定
- 分支与模块：例如 `feat/retrieval-hybrid` + `retrieval`
- 本次改动范围：涉及文件列表
- 目标验收项：来自 `docs/development-flow.md` 的“完整合并验收门槛”
- 可执行命令：`pytest`、`finqa ...`、`docker-compose ...`

## 3. 测试步骤（必须按顺序）
1. 环境确认
- 确认当前分支与工作区干净度：`git status --short --branch`
- 记录当前提交：`git rev-parse --short HEAD`

2. 变更定位
- 列出改动文件：`git diff --name-only HEAD~1..HEAD`（或当前工作区改动）
- 识别受影响模块：`src/finqa/<module>/`、`tests/`

3. 快速回归
- 执行最小冒烟：`pytest -q tests/test_smoke.py`
- 若失败，立即输出阻塞并停止后续“通过结论”

4. 模块专项测试
- 根据模块执行对应测试：
- `ingest/indexing`：`pytest -q tests/test_ingest_index.py`
- `retrieval`：`pytest -q tests/test_retrieval_hybrid.py`
- `qa/report`：执行对应测试文件或最小验证命令

5. CLI 链路验证
- 至少执行 1 条模块相关 CLI 命令并记录结果
- 示例：`finqa ingest ...` / `finqa ask ...` / `finqa report ...`

6. 验收项映射
- 将测试结果映射到验收门槛（功能可用性、可追溯字段、容器可运行性等）
- 标注每一条的状态：`PASS` / `FAIL` / `N/A`

## 4. 执行规范
- 只报告真实执行结果，禁止“推测通过”。
- 测试失败时先给失败结论，再给日志要点。
- 每次测试报告必须包含：
- 运行命令
- 退出码
- 关键输出（摘要）
- 受影响文件
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

## 7. 使用方式（建议）
1. 在每个并行分支合并前执行本 Skill。
2. 将 Markdown 输出粘贴到对应 `docs/<module>-iteration.md` 的 `Validation and Results`。
3. 将 JSON 输出作为自动化流水线或后续报表输入。

## 8. 全量验收建议（Main Merge Gate）
在分支准备合入 `main` 前，建议按以下顺序执行一次全量验收：

1. 基础回归
- `git status --short --branch`
- `python -m pytest -q tests/test_smoke.py`

2. 模块专项
- ingest/indexing：`python -m pytest -q tests/test_ingest_index.py`
- retrieval：`python -m pytest -q tests/test_retrieval_hybrid.py`
- 其他模块按对应测试文件补齐执行。

3. CLI 链路最小可用验证
- `python -m finqa ingest --data-dir data --out-dir .finqa_ci`
- `python -m finqa ask --q "revenue" --out json`
- `python -m finqa report --mode cross_year --out json`

4. 容器链路（建议至少每日一次）
- `docker-compose up --build`
- 在容器内验证至少一条 ingest + ask/report 命令链路。

5. 验收门槛判定
- 功能可用性：PASS（CLI 命令可执行）
- 可追溯字段完整性：PASS（citation 至少含 `source_file/fiscal_year/section/paragraph_id/quote_en`）
- 容器可运行性：PASS（compose 可拉起并执行最小链路）
- 文档完整性：PASS（对应 `docs/<module>-iteration.md` 与 `docs/development-flow.md` 索引已更新）

6. 结果固化建议
- 将本次测试命令、退出码、关键输出摘要回填到 `docs/<module>-iteration.md` 的 `Validation and Results`。
- 若存在 FAIL/N/A，必须显式记录风险与阻塞项，禁止直接给出“全绿”结论。
