# report 模块迭代记录

## 迭代目标（Iteration Goal）
- 使 `finqa report` 在 `single_year` 与 `cross_year` 两种模式下稳定输出结构化结果。
- 保持报告链路可交付：本地 CLI 可执行，容器命令链路可复现。

## 本次迭代范围（Scope of This Iteration）
- 范围内（In scope）：
  - `src/finqa/report/writer.py` 的结构化输出契约验证与结果固化。
  - embedding + LLM 最小可运行链路（可选增强，默认可回退）。
  - 报告/容器相关测试与 CLI 验证。
  - report 迭代文档与验收映射补齐。
- 范围外（Out of scope）：
  - `ingest/indexing/retrieval/qa` 主体逻辑改造。
  - 引入新模型或重构检索/生成算法。

## 已交付功能（Delivered Features）
- 功能 1：报告双模式结构化输出
  - 支持 `single_year` 与 `cross_year`。
  - 输出字段包含：`mode/report_zh/summary/highlights/yearly_breakdown/evidence/pipeline/llm_error`。
- 功能 2：容器一键链路配置
  - `docker-compose` 命令链路覆盖 `ingest + report`。
  - 产物写入 `/app/.finqa/report.json`（宿主机 `.finqa/report.json` 可见）。
- 功能 3：embedding + LLM 最小链路
  - `docker-compose` 支持通过 `env_file + environment` 读取本地模型与 provider 配置。
  - `FINQA_ENABLE_LLM` 支持 `0/1/auto` 三档：
    - `0`：快速模式（默认，启发式）
    - `1`：增强模式（强制尝试本地 LLM）
    - `auto`：仅当本地模型目录存在时启用 LLM（离线优先）
  - `auto` 模式下模型不存在时直接走启发式，不做无意义加载尝试。
  - 本地模型不可用时自动回退本地启发式报告，不影响 `single_year/cross_year` 可执行性。
- 功能 4：文档与测试配套
  - README 补充 embedding/LLM 配置与最小运行步骤、Docker 排障与一键命令清单。
  - 增加并更新报告/容器相关测试以覆盖新链路配置与回退行为。

## 验收映射（Acceptance Mapping）
- 验收项 A（`finqa report` 可执行并产出结构化结果） -> 实现/证据：
  - `tests/test_report_writer.py` 通过；
  - `python -m finqa report --mode cross_year --out json` 与 `single_year` 命令均可执行并返回结构化 JSON。
- 验收项 B（`docker-compose up --build` 可启动） -> 实现/证据：
  - `tests/test_container_config.py` 覆盖 ingest/report 链路与产物路径；
  - `docker-compose.yml` 已配置 `env_file` 与本地 LLM 环境变量注入（`FINQA_LLM_PROVIDER/FINQA_LLM_MODEL` 等）；
  - `docker-compose config` 解析通过；
  - 代码与配置层面满足启动条件；当前主机执行 `docker-compose up --build -d` 时受 Docker Desktop 权限限制（`Access is denied`）。
- 验收项 C（README 文档完整） -> 实现/证据：
  - README 已包含 embedding/LLM 配置项、最小运行步骤、一键命令清单、容器排障说明。

## 验证与结果（Validation and Results）
### 测试报告

#### 基础信息
- 分支：`feat/report-docker-readme`
- 提交：`02d11a8`
- 模块：`report`

#### 执行命令
1. `PYTHONPATH=d:\mymaa\sf-D\src python -m pytest -q tests/test_report_writer.py tests/test_container_config.py tests/test_report_cli_encoding.py`（exit 0）
2. `PYTHONPATH=d:\mymaa\sf-D\src python -m finqa report --mode cross_year --out json`（exit 0）
3. `PYTHONPATH=d:\mymaa\sf-D\src FINQA_ENABLE_LLM=auto FINQA_LLM_PROVIDER=modelscope_local python -m finqa report --mode cross_year --out json`（exit 0）
4. `PYTHONPATH=d:\mymaa\sf-D\src FINQA_ENABLE_LLM=auto FINQA_LLM_PROVIDER=modelscope_local python -m finqa report --mode single_year --out json`（exit 0）
5. `docker-compose config`（exit 0）
6. `docker-compose up --build -d`（exit 1，环境权限）

#### 结果汇总
- 总结：`PARTIAL PASS`
- `module_tests`：`PASS`（`11 passed`）
- `cli_validation`：`PASS`
- `container_runtime`：`BLOCKED`（当前主机出现 `dockerDesktopLinuxEngine Access is denied`）

#### 验收映射
- 功能可用性：`PASS`（report 命令与报告测试通过）
- 可追溯字段完整性：`PASS`（`evidence` 保持 `source_file/fiscal_year/section/paragraph_id`）
- 容器可运行性：`PARTIAL PASS`（`docker-compose config` 通过；`up --build -d` 在当前主机被 Docker 权限阻塞，非代码错误）
- 文档完整性：`PASS`（README 已补 embedding/LLM 配置与最小运行步骤）

#### 风险与阻塞
- 风险：首次构建仍依赖外网拉取基础镜像，网络波动会影响构建耗时与稳定性。
- 阻塞：若历史环境存在同名容器 `smartfin`，需先执行 `docker rm -f smartfin` 再启动。

## 本迭代提交记录（Commits in This Iteration）
- `c3ce414` `feat(report): 实现 single_year/cross_year 结构化报告输出`
- `24f8921` `chore(docker-docs): 打通 compose 一键运行并完善交付文档`
- `2e845b4` `Merge remote-tracking branch 'origin/main' into feat/report-docker-readme`
- `9e70beb` `Merge remote-tracking branch 'origin/main' into feat/report-docker-readme`
- `862bb19` `feat(report): 打通embedding+llm最小可运行链路`
- `27cacf5` `docs(chore): 补充embedding-llm配置与容器验证说明`
- `6b839ab` `docs(report): 回填embedding-llm链路验证与验收映射`
- `02d11a8` `feat(report): 新增 llm auto mode with local model existence gate`

## 已知风险/限制（Known Risks / Limitations）
- 风险 1：新环境首次执行 `up --build` 仍依赖 Docker Hub 网络质量。
- 风险 2：Windows 主机若未获得 Docker Desktop 命名管道权限，会导致 `docker-compose up` 失败（`Access is denied`）。
- 限制 1：当前报告为启发式聚合，不包含模型级财务推理能力。
- 限制 2：若 Python 解释器优先命中其他工作树安装路径，需显式设置 `PYTHONPATH=d:\mymaa\sf-D\src` 或重新 `pip install -e .`。

## 建议下一迭代（Suggested Next Iterations）
- 下一迭代项 1：引入固定数据夹具，补充 `single_year/cross_year` 业务断言测试。
- 下一迭代项 2：在 CI 环境增加 Docker daemon 可用时段的 `docker-compose up --build` 冒烟验证。
- 下一迭代项 3（协作：`ingest` 模块）：优化 chunk 标准化与章节字段清洗，降低 `report` 命中噪声段落（如签名段）比例。
- 下一迭代项 4（协作：`retrieval` 模块）：增加面向报告场景的检索查询模板与重排策略，提升跨年对比证据相关性。
- 下一迭代项 5（协作：`qa` 模块）：统一 `report/qa` 的证据引用契约与可解释性字段，减少下游消费差异。
- 下一迭代项 6（协作：`docs`/CI）：将多模块联调验收（ingest -> retrieval -> report）固化为流水线检查项。
