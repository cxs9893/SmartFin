# SmartFin

本项目是一个本地运行的财报智能问答系统（MVP骨架），用于 AAPL 10-K JSON 数据的导入、检索、问答与简要报告生成。

## 目录结构

- `src/finqa/ingest`：数据导入与标准化
- `src/finqa/indexing`：索引构建（BM25 + 向量，占位）
- `src/finqa/retrieval`：混合检索（占位）
- `src/finqa/qa`：问答生成（占位）
- `src/finqa/report`：报告生成（占位）
- `tests`：测试目录
- `data`：输入数据目录
- `.finqa`：本地索引与中间产物目录

## 快速开始

### 1) 本地运行

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e .
```

```bash
finqa ingest --data-dir data --out-dir .finqa
finqa ask --q "Apple 2024 risk factors" --out json
finqa report --mode cross_year --out json
```

### 2) Docker 运行

```bash
docker-compose up --build
```

## 当前状态

当前为第0阶段项目骨架：

- 命令行和模块结构已就绪
- 支持 JSONL 级别导入与占位检索
- 已预留可追溯引用字段
- 下一步将接入真实 embedding、FAISS、BM25 和本地开源生成模型

## AI-Coding 协作说明（初版）

- 使用 Codex 完成项目结构初始化与基础命令骨架。
- 后续每个里程碑建议拆分为独立提交（ingest / retrieval / qa / report / docker / docs）。
