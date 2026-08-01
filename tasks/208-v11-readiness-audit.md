# Task 208: V11 Readiness Audit

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **任务类型**: 只读审计、证据采集、任务拆分
> **报告**: `docs/reports/208-v11-readiness-audit.md`

## 目标

从外部技术用户视角审计 Songyan 当前开源可用性，冻结 README、CLI、doctor、create-project、run、export、report、配置、安装与发布路径的真实缺口，并据此校准 Task 209-215 的范围和依赖。

Task 208 不实现 runtime 功能，不修改核心生成链路，不修改 prompt、CED、T9、five-gate 或 hard gate。

## 审计范围

- 入口文档：`README.md`、`docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md`、`tasks/V11-Plan.md`。
- CLI 能力：`doctor`、`create-project`、`run`、`report`、`export`、`profile`、`metrics`、`index`、`mark`。
- 安装与发布：`pyproject.toml`、console script、package data、CI、License、release 文件。
- 外部用户最短路径：非仓库 cwd 下的 `doctor -> create-project -> run -> report/export`。
- 错误体验：缺 key、非法 DB、非法 checkpointer、非法模板、缺 run log、无 accepted 章节导出。
- 资产与安全：backup/restore、run bundle、profile validate、敏感信息脱敏、发布前工作区清洁度。

## 禁止项

- 不新增或修改核心 Agent / Workflow 节点。
- 不新增生成能力。
- 不修 doctor、run、export、profile 等 runtime 功能。
- 不修改任何 prompt card。
- 不把 V10 report-only / spike 信号接入 CED、T9、five-gate 或 hard gate。
- 不把本次隔离审计产生的临时 DB、日志或 wrapper 输出提交进仓库。

## 证据命令

本次审计实际运行了以下命令或等价 Python Click 调用：

- `git status --short --branch`
- `python -c "from songyan.cli.main import cli; ... ['--help']"`
- `python -c "from songyan.cli.main import cli; cli()" doctor --json`
- `python -c "from songyan.cli.main import cli; cli()" doctor --json --init-db`
- `python -c "from songyan.cli.main import cli; cli()" create-project --template xuanhuan`
- `powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 90 -- python -c "from songyan.cli.main import cli; cli()" run ...`
- `python -c "from songyan.cli.main import cli; cli()" report --run-id run-ab257f3e`
- `python -c "from songyan.cli.main import cli; cli()" export --project-id ...`
- `python -m pytest tests/cli -q`
- `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_183_profile_cli.py tests/test_119_reporting_wrapper.py -q`

隔离审计目录为 Windows 临时目录：`%TEMP%/songyan-task208-audit`。该目录不属于仓库。

## 完成条件

- [x] Task 208 任务书落盘。
- [x] readiness audit Markdown 报告落盘。
- [x] V11 开源门槛矩阵逐项给出状态与证据。
- [x] Task 209-215 的范围、依赖、优先级被校准。
- [x] Task 208 DONE 文档落盘。
- [x] 未修改 runtime、prompt、CED、T9、five-gate 或 hard gate。

## 总结判断

Songyan 已具备进入 V11 开源可用化开发的基础：CLI 主入口、doctor、模板建项、report、export、profile 和资源枚举均存在，且在非仓库 cwd 下可部分运行。

但当前还不能标记为正式开源可用版本。主要缺口集中在四类：Quickstart 成功证据不足、doctor/preflight 还不能兜住所有配置错误、backup/restore 与 run bundle 缺失、发布纪律不足。

下一步可以进入 Task 209，但 Task 209 必须与 Task 210 的 doctor/preflight 增强形成紧密闭环。
