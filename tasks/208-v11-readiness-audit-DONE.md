# Task 208 DONE: V11 Readiness Audit

> **完成时间**: 2026-08-01
> **报告**: `docs/reports/208-v11-readiness-audit.md`
> **结论**: 可以进入 Task 209；尚不能标记为正式开源可用版本。

## 完成内容

- 读取并复核 `AGENTS.md`、`docs/STATUS.md`、`docs/INDEX.md`、`README.md`、`tasks/V11-README.md`、`tasks/V11-Plan.md`。
- 盘点 CLI 主入口和命令能力：`doctor`、`create-project`、`run`、`report`、`export`、`profile`、`metrics`、`index`、`mark`。
- 在非仓库 cwd 下完成隔离审计：
  - `doctor --json` 缺 key 场景。
  - `doctor --json --init-db` schema 初始化。
  - `create-project --template xuanhuan` 模板建项。
  - `run --chapters 1-3` 空 key 失败样本。
  - `report --run-id run-ab257f3e` 失败 run 报告生成。
  - `export` 无 accepted 章节失败样本。
- 审计错误体验：非法 DB URL、非法 checkpointer、非法模板、缺 run log、无 accepted export。
- 审计发布纪律：console script、package data、CI、License、CHANGELOG、CONTRIBUTING、issue templates、release checklist、wheel smoke。
- 产出 readiness audit 报告并校准 Task 209-215。

## 关键发现

| 编号 | 发现 | 影响 | 路由 |
|------|------|------|------|
| F1 | README 的最短路径有命令，但缺 Ch1-3 外部成功证据或 dry-run smoke | 外部用户路径未闭环 | 209 |
| F2 | `run` 在缺 key 业务失败后 exit code 仍为 0 | 自动化和用户会误判成功 | 210/212 |
| F3 | 非法 `CHECKPOINTER_MODE` 在导入期 traceback，doctor 接不住 | preflight 体验不稳定 | 210 |
| F4 | `backup` / `restore` 不存在 | 长期项目资产不可迁移、不可恢复 | 211 |
| F5 | run bundle 不存在，`report` 只有 Markdown | 问题复现和脱敏分享不足 | 213 |
| F6 | `profile validate`、rollback/history 不存在 | 配置安全不足 | 214 |
| F7 | 缺 CHANGELOG、CONTRIBUTING、issue templates、release checklist、wheel smoke | 发布物可信度不足 | 215 |
| F8 | `pyproject.toml` 版本为 2.0.0，但当前 editable 安装元数据为 0.1.0 | 发布版本纪律风险 | 215 |

## 验证结果

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/cli -q` | 35 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_183_profile_cli.py tests/test_119_reporting_wrapper.py -q` | 40 passed |
| `songyan --help` | exit 0 |
| 隔离 cwd `doctor --json --init-db` | exit 0，schema complete |
| 隔离 cwd `create-project --template xuanhuan` | exit 0 |
| 隔离 cwd `run --chapters 1-3` 空 key | 业务失败但进程 exit 0 |
| 隔离 cwd `report --run-id run-ab257f3e` | exit 0 |
| 隔离 cwd `export` 无 accepted | exit 1 |

## Task 209-215 路由

| Task | 优先级 | 校准后目标 |
|------|--------|------------|
| 209 | P0 | 重写 Quickstart 和用户文档闭环，所有步骤绑定可执行命令和证据 |
| 210 | P0 | 强化 doctor/preflight，兜住非法配置、run 前环境、日志路径、预算和 exit code |
| 211 | P1 | 建立 backup/restore 或等价资产包，并明确 export 与 backup 边界 |
| 212 | P1 | 标准化至少 5 类失败恢复路径 |
| 213 | P1 | 生成可脱敏分享的 run bundle：JSON + Markdown + 日志索引 |
| 214 | P2 | 增加 profile validate、危险项提示、rollback/history 或等价机制 |
| 215 | P2 | 补 release checklist、wheel smoke、版本一致性、CHANGELOG、CONTRIBUTING、issue templates |

## 守护确认

- 未修改 `src/` runtime。
- 未修改 prompt card。
- 未修改 CED、T9、five-gate、segment audit 或 hard gate。
- 未把 V10 report-only / spike 信号接入生成链路。
- 隔离审计 DB 与日志保留在 `%TEMP%/songyan-task208-audit`，不进入仓库。
