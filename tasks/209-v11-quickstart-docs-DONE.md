# Task 209 DONE: Quickstart 与用户文档闭环

> **完成时间**: 2026-08-02
> **证据**: `docs/reports/209-quickstart-evidence.md`
> **结论**: Quickstart 文档闭环完成；下一步进入 Task 210 doctor / preflight 增强。

## 完成内容

- 更新 `README.md`：
  - Quickstart 改为 V11 外部用户最短路径。
  - `songyan doctor` 改为 `songyan doctor --init-db`。
  - 生成范围从 Ch1-5 改为 Ch1-3。
  - 增加 `run_id`、`songyan report --run-id <run_id>` 和 accepted export。
  - 增加 preview 限制和后续任务路由。
- 新增 `docs/quickstart.md`：
  - 安装、配置、自检、模板建项。
  - Ch1-3 短窗口运行。
  - 10 章教程。
  - 成本预算、日志路径、Windows wrapper。
  - 当前限制和后续任务路由。
- 新增 `docs/troubleshooting.md`：
  - 缺 key、DB、非法 checkpointer、run 失败、report、export、Windows wrapper。
  - 手动问题分享和脱敏注意事项。
- 新增 `docs/reports/209-quickstart-evidence.md`：
  - 记录隔离目录 smoke 命令、project_id、run_id、失败样本和未执行项。
- 同步 `docs/STATUS.md`、`docs/INDEX.md`、`tasks/V11-README.md`。

## 证据摘要

| 命令 | 结果 |
|------|------|
| `songyan --help` | exit 0；列出核心 CLI 命令 |
| `songyan doctor --json` 缺 key | exit 1；结构化 fail；`llm.key` 有 hint |
| `songyan doctor --json --init-db` dummy key | exit 0；schema complete；resources package pass |
| `songyan create-project --template xuanhuan` | exit 0；project_id=`44e8054f0cef46b096b10bab858da2c9` |
| `songyan run --chapters 1-3` 空 key | wrapper 正常退出，业务失败；run_id=`run-0781e756` |
| `songyan report --run-id run-0781e756` | exit 0；生成 `logs/reports/report-run-0781e756.md` |
| `songyan export` 无 accepted | exit 1；提示没有可导出的 accepted 章节 |
| `songyan list-projects` | exit 0；可找回 project_id |

## 收尾验证

| 命令 | 结果 |
|------|------|
| `git diff --check -- README.md docs/STATUS.md docs/INDEX.md tasks/V11-README.md` | pass，仅 Windows CRLF 提示 |
| `Select-String ... -Pattern '\s+$'` | 新增文档无行尾空白 |
| `python -m pytest tests/cli -q` | 35 passed |
| `python -m pytest tests/test_177_export_service.py tests/test_178_resource_loading.py tests/test_183_profile_cli.py tests/test_119_reporting_wrapper.py -q` | 40 passed |
| `ruff check src/ tests/` | pass |

## 未完成但已路由

| 缺口 | 路由 |
|------|------|
| 真实 LLM Ch1-3 成功 smoke | Task 210/215 |
| `run` 业务失败 exit code 0 | Task 210/212 |
| 非法 `CHECKPOINTER_MODE` traceback | Task 210 |
| backup/restore | Task 211 |
| 失败恢复分类和演练 | Task 212 |
| run bundle 与脱敏诊断包 | Task 213 |
| profile validate / rollback / history | Task 214 |
| wheel smoke、CHANGELOG、CONTRIBUTING、issue templates、release checklist | Task 215 |

## 守护确认

- 未修改 `src/` runtime。
- 未修改 prompt card。
- 未修改 CED、T9、five-gate、segment audit 或 hard gate。
- 未把 V10 report-only / spike 信号接入生成链路。
- 隔离目录 `%TEMP%/songyan-task209-quickstart` 不属于仓库，生成的 DB 和日志不提交。
