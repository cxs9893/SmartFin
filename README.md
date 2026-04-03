# SmartFin

本项目是一个本地运行的财报智能问答系统（MVP骨架），支持 AAPL 10-K JSON 数据的导入、检索、问答与报告生成。

## 目录结构

- `src/finqa/ingest`：数据导入与标准化
- `src/finqa/indexing`：索引构建（BM25 + 向量，占位）
- `src/finqa/retrieval`：混合检索（占位）
- `src/finqa/qa`：问答生成（占位）
- `src/finqa/report`：报告生成（`single_year` / `cross_year`）
- `tests`：测试目录
- `data`：输入数据目录（可为空）
- `.finqa`：本地索引与中间产物目录

## Report 输出结构

`finqa report --out json` 返回结构化结果，包含：

- `mode`：报告模式（`single_year` 或 `cross_year`）
- `report_zh`：中文总结文本
- `summary`：统计摘要（年份数、证据数、章节数、选中年份）
- `highlights`：证据高亮列表
- `yearly_breakdown`：按年度聚合的证据统计与 Top 章节
- `evidence`：证据明细（来源文件、年份、章节、段落 ID、片段）

## 快速开始

### 1) 本地运行

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
```

```bash
finqa ingest --data-dir data --out-dir .finqa
finqa report --mode cross_year --out json
finqa report --mode single_year --out json
```

### 2) Docker 一键运行

```bash
docker-compose up --build
```

容器启动后会自动执行：

1. `finqa ingest --data-dir /app/data --out-dir /app/.finqa`
2. `finqa report --mode cross_year --out json`
3. 将报告写入 `/.finqa/report.json`（宿主机同目录可见）

## 评估指标（MVP）

当前报告能力建议用以下指标评估：

- `Schema Completeness`：结构化字段完整率（`mode/summary/highlights/yearly_breakdown/evidence`）
- `Evidence Coverage`：`evidence_count` 与命中段落覆盖情况
- `Year Aggregation Accuracy`：`single_year` 是否仅聚焦最新年度、`cross_year` 是否覆盖多年度
- `Section Diversity`：`section_count` 与 Top 章节分布
- `Traceability`：证据可追溯字段完整率（`source_file/fiscal_year/section/paragraph_id`）

## AI-Coding 协作说明

本仓库采用 AI-Coding 协作开发，建议使用如下流程：

- 明确任务边界：提前声明可修改路径与禁止改动模块
- 小步提交：按功能拆分提交（如 `feat(report)`、`chore(docker)`、`docs(readme)`）
- 每步可验证：每次改动后至少执行一条可复现命令
- 结果可交付：输出中包含命令、产物路径、风险说明

## 迭代文档规范

- 统一规范与脚本用法见：
  - `docs/development-flow.md` 的“规范与自动化”章节

## 当前状态

当前为第 0 阶段 MVP：

- CLI 与模块结构已就绪
- 导入、检索、问答、报告均可独立执行
- 已预留可追溯引用字段
- 容器支持一键 ingest + report 产物落盘
- 后续可接入真实 embedding、FAISS、BM25、LLM 生成能力
