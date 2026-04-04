# SmartFin CI 方案（含每步理由）

## 目标
- 将 A-D 模块验收门槛固化到自动化流程。
- 保证“代码、测试、CLI、容器、文档规范”在合并前可验证。

## 流程步骤与理由

1. 触发策略（`pull_request`/`push main`/`workflow_dispatch`）
- 理由：覆盖日常开发门禁、主分支稳定性和手动重跑场景。

2. 安装运行环境（Python 3.11 + `pip install -e .`）
- 理由：与本地开发保持一致，避免“本地可跑、CI 不可跑”。

3. 迭代文档校验（`scripts/validate_iteration_docs.ps1`）
- 理由：约束“改模块代码必须同步模块迭代文档”，防止交付断层。

4. 快速冒烟测试（`tests/test_smoke.py`）
- 理由：以最小成本快速发现致命回归，缩短失败反馈时间。

5. 模块测试集合（A/B/C/D）
- 理由：直接映射模块验收门槛，保证核心行为不回退。

6. CLI 冒烟链路（`ingest -> ask -> report`）
- 理由：验证用户可感知的交付能力，而不是只验证单测。

7. Windows 专项作业（编码/路径）
- 理由：历史上存在 Windows 控制台编码问题，需持续门禁。

8. Docker 配置校验（`docker compose config`）
- 理由：提前发现 compose 语法与挂载错误，降低运行失败概率。

9. Docker 运行验收（`docker compose up --build -d`）
- 理由：容器是交付路径之一，必须验证“可构建、可启动、可产出”。

10. 产物归档（`.finqa_ci`、容器产物）
- 理由：失败时可追溯，评审时有证据，便于复盘与复现。

11. 清理资源（`docker compose down -v`）
- 理由：避免 Runner 污染和磁盘膨胀，保证后续任务稳定。

## 已落地配置
- 工作流文件：`.github/workflows/ci.yml`
- 主要作业：
  - `test-linux`
  - `test-windows`
  - `docker-main`（仅 `main`/手动触发）
