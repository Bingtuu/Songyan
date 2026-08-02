# Task 213 - V11 run bundle 诊断包

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **依赖**: Task 210 doctor / preflight 增强；Task 212 失败恢复体验
> **目标**: 提供可分享、可脱敏的 run 诊断包，让外部技术用户能用一条命令生成复现问题所需的 JSON + Markdown 摘要。

---

## 任务目标

完成 V11 Task 213 run bundle 诊断包：

1. 新增一条 CLI 命令，基于 `run_id` 输出诊断包。
2. 诊断包包含机器可读 JSON 和人类可读 Markdown。
3. 聚合已有事实源：SQLite `project_runs`、`logs/chapter_runs/<run_id>.jsonl`、成本遥测、report 路径和日志索引。
4. 包含章节状态、失败分类、成本视图、质量门/候选门禁、health/overdue 现有信号，以及 CED/T9/five-gate 的可用性说明。
5. 默认脱敏或排除 API key、`.env` 原文、敏感 env、绝对路径、日志正文和正文内容。

---

## 范围

包含：

- `songyan bundle-run --run-id <run_id> --output bundles/`
- `bundle.json`
- `bundle.md`
- `logs/index.json`
- 缺 run log / artifact 时复用 Task 212 恢复建议。
- 文档说明 bundle 与 `report`、`backup`、`export` 的边界。

不包含：

- 不扩张核心生成能力。
- 不新增核心 Agent / Workflow 节点。
- 不修改 prompt、CED、T9、five-gate、segment audit 或质量 hard gate。
- 不实现 profile validate / rollback / history；该能力路由到 Task 214。
- 不实现 release checklist / wheel smoke；这些路由到 Task 215。
- 不把日志正文、`.env` 或完整书稿正文打进包。

---

## Bundle 格式

建议 zip 结构：

```text
songyan-run-bundle-<run_id>-<timestamp>.zip
├── bundle.json
├── bundle.md
└── logs/index.json
```

`bundle.json` 字段：

- `format`
- `format_version`
- `created_at`
- `run`
- `project`
- `chapters`
- `cost`
- `quality_signals`
- `artifacts`
- `logs`
- `redaction`
- `warnings`

`bundle.md` 字段：

- Run 摘要。
- Project 摘要。
- 章节成功 / 失败清单。
- 成本摘要。
- 质量与连续性信号摘要。
- 产物路径与脱敏说明。

---

## 验收标准

必须满足：

- 一条命令能生成 zip，内含 `bundle.json`、`bundle.md`、`logs/index.json`。
- 缺 `logs/chapter_runs/<run_id>.jsonl` 时 exit 1，并提示 Task 212 的恢复路径。
- bundle 包含 run 元信息、章节状态、成本视图、日志索引和失败分类。
- 脱敏测试证明 API key、敏感 env、绝对路径不进入 bundle。
- 不改变 `report` / `backup` / `export` 行为边界。

验证命令：

```powershell
python -m pytest tests/cli -q
python -m pytest tests/test_119_reporting_wrapper.py tests/test_175_cost_tracking.py tests/test_211_backup_restore.py -q
ruff check src/ tests/
python -m pytest tests/ -q
```

---

## 交付物

- `tasks/213-v11-run-bundle.md`
- `tasks/213-v11-run-bundle-DONE.md`
- `docs/reports/213-run-bundle-evidence.md`
- 相关代码和测试
- `README.md`
- `docs/quickstart.md`
- `docs/troubleshooting.md`
- `docs/STATUS.md`
- `docs/INDEX.md`
- `tasks/V11-README.md`
