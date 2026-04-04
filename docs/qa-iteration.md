# qa 模块迭代记录

## 迭代目标（Iteration Goal）
- 本次迭代聚焦重新完成 grounded QA 的初始开发闭环：仅基于检索证据生成答案、无证据时拒答，并输出可追溯 citations。
- 预期收益：`finqa ask` 在可追溯性与可信性上满足最小合并门槛，为后续报告与评估提供稳定 QA 基线。

## 本次迭代范围（Scope of This Iteration）
- 范围内（In scope）：
  - `src/finqa/qa/generator.py`：证据门控、英文证据过滤、拒答路径与回答结构化输出。
  - `tests/test_qa_grounded.py`：有证据回答与无证据拒答测试覆盖。
  - `docs/qa-iteration.md`：新增 QA 迭代记录。
  - `docs/development-flow.md`：补充 QA 迭代文档索引。
- 范围外（Out of scope）：
  - ingest/indexing/retrieval/report/docker 主体逻辑改动。
  - 语义相关性重排与复杂推理链路。

## 已交付功能（Delivered Features）
- 功能 1：grounded 证据门控
  - 问答仅消费 retrieval 传入 `hits`，不引入外部事实。
  - 仅当证据字段完整时生成 citation：`source_file/fiscal_year/section/paragraph_id/quote_en`。
- 功能 2：英文证据约束与拒答
  - 对证据文本增加英文字符检查（`A-Z/a-z`）。
  - 无有效证据时返回统一拒答：`answer_zh` 拒答文案、`confidence=0.0`、`citations=[]`。
- 功能 3：中文回答 + 英文引用输出
  - 回答内容以中文输出，按 `证据[1..n]` 列出年份/章节/段落。
  - 引用字段 `quote_en` 保留英文原文片段（截断到 300 字符）。

## 验收映射（Acceptance Mapping）
- 验收项 A（仅基于 retrieval 证据回答） -> 实现/证据：
  - `generate_answer` 仅遍历 `hits` 构建 citations；
  - `tests/test_qa_grounded.py` 验证有证据场景可回答。
- 验收项 B（citations 字段完整） -> 实现/证据：
  - citation 生成前校验必填字段完整；
  - 测试断言 `source_file/fiscal_year/section/paragraph_id/quote_en` 全部存在且值符合预期。
- 验收项 C（无证据时拒答） -> 实现/证据：
  - 空 hits 或无效 hits（缺字段/非英文证据）均触发拒答；
  - `tests/test_qa_grounded.py` 验证拒答返回 `confidence=0.0` 与空 citations。

## 验证与结果（Validation and Results）
- 命令：
  - `$env:PYTHONPATH='src'; python -m pytest -q tests/test_smoke.py`
  - `$env:PYTHONPATH='src'; python -m pytest -q tests/test_qa_grounded.py`
  - `$env:PYTHONPATH='src'; finqa ask --q "Apple 2024 risk factors" --out json`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_iteration_docs.ps1`
- 结果：
  - `test_smoke.py`：`1 passed`
  - `test_qa_grounded.py`：`2 passed`
  - `finqa ask ... --out json`：返回 0，当前索引证据不足时正确拒答
  - 迭代文档校验：通过
  - 环境提示：pytest 产生缓存目录权限 warning，不影响本轮通过结论

## 本迭代提交记录（Commits in This Iteration）
- 尚未提交（working tree changes pending）。

## 已知风险/限制（Known Risks / Limitations）
- 风险 1：英文证据判定采用字符规则，无法覆盖更复杂语种混合与编码噪声场景。
- 限制 1：当前回答为证据模板化汇总，不包含深层语义推理与跨证据冲突消解。

## 建议下一迭代（Suggested Next Iterations）
- 下一迭代项 1：增加 evidence-query 相关性过滤，降低偏题召回导致的误答风险。
- 下一迭代项 2：增加多证据冲突检测与置信度衰减机制，提升回答稳健性。
- 协作项 A（需要 retrieval 模块）：在 `hybrid_search` 输出中补充可用于 QA 判定的相关性阈值信号（如最小分数门槛、候选分布），用于“回答/拒答”决策。
- 协作项 B（需要 ingest 模块）：进一步规范 `text/quote_en` 的英文清洗与字段完整性，减少脏数据导致的证据丢弃。
- 协作项 C（需要 report 模块）：统一 QA 与 report 的 citation 展示约定（字段命名、截断策略、排序规则），保证跨命令输出一致性。
