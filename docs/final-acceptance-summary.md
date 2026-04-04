# SmartFin A-D 模块总收束验收报告

## 1. 验收范围
- 分支基线：`main`
- 验收对象：A（ingest/index）/ B（retrieval）/ C（qa）/ D（report+docker+readme）
- 验收依据：
  - `docs/development-flow.md` 的“合并与收束策略”与“完整合并验收门槛”
  - `docs/testing-skill.md` 的强制执行项

## 2. 最终结论
- 总体结论：**A-D 模块功能链路验收通过，可进入里程碑发布阶段**
- 说明：
  - A/B/C 模块测试与 CLI 验证通过。
  - D 模块已修复 Windows 控制台 JSON 输出编码问题；`report` 双模式可执行。
  - 容器链路在本机可启动（`smartfin` 容器创建并可运行）后，D 模块容器项可判 `PASS`。

## 3. 分模块验收结果

### A 模块（ingest/index）
- 结论：`PASS`
- 关键证据：
  - `tests/test_ingest_index.py` 通过
  - `finqa ingest` 重复执行可用，索引产物稳定
  - 字段契约覆盖 `source_file/fiscal_year/section/paragraph_id/quote_en`

### B 模块（retrieval）
- 结论：`PASS`
- 关键证据：
  - `tests/test_retrieval_hybrid.py` 通过
  - `hybrid_search` 返回 `hit/citation` 标准结构
  - 参数化检索（top_k/权重）可用

### C 模块（qa）
- 结论：`PASS`
- 关键证据：
  - `tests/test_qa_grounded.py` 通过
  - 有证据回答、无证据拒答均覆盖
  - `finqa ask` 输出 `answer_zh/confidence/citations`

### D 模块（report/docker/readme）
- 结论：`PASS`
- 关键证据：
  - `tests/test_report_writer.py`、`tests/test_container_config.py`、`tests/test_report_cli_encoding.py` 通过
  - `finqa report --mode cross_year --out json` 通过
  - `finqa report --mode single_year --out json` 通过
  - README 已补充 Docker 启动失败排查

## 4. Gate 统一判定
- 功能可用性：`PASS`
- 问答可信性：`PASS`
- 可追溯字段完整性：`PASS`
- 容器可运行性：`PASS`
- 文档完整性：`PASS`
- 测试最低要求：`PASS`
- 分支与提交卫生：`PASS`
- 收束顺序与回归：`PASS`

## 5. 发布建议（Tag）
建议在 `main` 打里程碑标签，例如：`v0.1.0-mvp`。

```bash
git checkout main
git pull --ff-only origin main
git tag -a v0.1.0-mvp -m "SmartFin MVP: A-D modules accepted"
git push origin v0.1.0-mvp
```

## 6. 后续迭代建议
1. 引入检索评估集与自动化指标（Recall@K/MRR）。
2. 增强 QA 置信度与拒答阈值策略。
3. 将 `testing-skill` 固化到 CI，自动输出验收报告。
