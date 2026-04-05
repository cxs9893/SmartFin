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
- `report_zh`：中文总结文本（可选由 LLM 增强）
- `summary`：统计摘要（年份数、证据数、章节数、选中年份）
- `highlights`：证据高亮列表
- `yearly_breakdown`：按年度聚合的证据统计与 Top 章节
- `evidence`：证据明细（来源文件、年份、章节、段落 ID、片段）
- `pipeline`：embedding / llm 运行配置快照
- `llm_error`：LLM 调用失败时的错误信息（默认 `null`）

## Embedding + 本地 LLM 最小配置

### 新增配置项列表

可在 `.env`（或复制 `.env.example`）中配置以下项：

- `FINQA_EMBEDDING_PROVIDER`：embedding provider，默认 `bge`
- `FINQA_LLM_PROVIDER`：LLM provider，默认 `modelscope_local`
- `FINQA_ENABLE_LLM`：报告 LLM 开关（`0/1/auto`）
- `FINQA_LLM_MODEL`：本地模型路径（示例：`models/Qwen2___5-0___5B-Instruct`）
- `FINQA_LLM_LOCAL_FILES_ONLY`：是否仅本地加载（推荐 `true`）

### 最小运行步骤（本地）

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
```

```bash
# 可选：cp .env.example .env 后编辑 key
finqa ingest --data-dir data --out-dir .finqa
finqa report --mode cross_year --out json
finqa report --mode single_year --out json
```

说明：
- 快速模式（默认）：`FINQA_ENABLE_LLM=0`，直接使用本地启发式报告，启动快、资源占用低。
- 增强模式（本地模型）：`FINQA_ENABLE_LLM=1`，会尝试调用本地 LLM 增强 `report_zh`，若模型缺失或加载失败会回退。
- 自动模式（推荐稳妥）：`FINQA_ENABLE_LLM=auto`，仅当 `FINQA_LLM_MODEL` 路径存在时才启用本地 LLM；模型不存在时直接走启发式，不做无意义加载尝试。

## Docker 一键运行

```bash
docker-compose up --build
```

容器启动后会自动执行：

1. `finqa ingest --data-dir /app/data --out-dir /app/.finqa`
2. `finqa report --mode cross_year --out json`
3. 将报告写入 `/.finqa/report.json`（宿主机同目录可见）

## 一键运行命令清单

- 本地验证：
  - `python -m pytest -q tests/test_report_writer.py tests/test_container_config.py`
  - `python -m finqa report --mode cross_year --out json`
- 容器验证：
  - `docker-compose config`
  - `docker-compose up --build -d`

### Docker 启动失败排查（可操作）

若 `docker-compose up --build` 失败，可按以下顺序排查：

1. 环境检测（Docker daemon / compose）

```bash
docker version
docker-compose version
docker info
```

2. 网络与镜像仓库连通性检测（Windows PowerShell）

```powershell
nslookup auth.docker.io
Test-NetConnection auth.docker.io -Port 443
Test-NetConnection registry-1.docker.io -Port 443
```

3. 先手动拉取基础镜像再构建（降低首次构建失败率）

```bash
docker pull python:3.11-slim
docker-compose up --build -d
```

4. 若仍失败，检查容器与构建日志

```bash
docker ps -a
docker logs smartfin
docker-compose logs
```

5. 常见修复项
- 执行 `docker login` 重新刷新 Docker Hub 认证。
- 在 Docker Desktop 配置代理（Settings -> Resources -> Proxies）。
- 调整系统 DNS（如 `1.1.1.1` / `8.8.8.8`）后重启 Docker Desktop。

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
