# Task 212 - V11 失败恢复体验

> **阶段**: V11 开源可用化收尾
> **状态**: DONE
> **依赖**: Task 210 doctor / preflight 增强；Task 211 backup / restore / schema ledger
> **目标**: 标准化 Songyan 常见失败的分类、提示和恢复动作，让外部技术用户在命令失败后知道下一步该执行什么。

---

## 任务目标

完成 V11 Task 212 失败恢复体验：

1. 标准化常见失败分类。
2. 增强 CLI 失败输出中的恢复建议。
3. 让外部技术用户在 `doctor`、`run`、`report`、`export`、`backup`、`restore` 失败后能看到可执行下一步。
4. 至少覆盖 5 类常见失败，并有测试或命令演练证据。

---

## 范围

包含：

- 缺 LLM key / endpoint / 非法配置。
- DB/schema 问题。
- run preflight 失败。
- pipeline 已启动后的章节失败。
- report 缺 run log。
- export 无 accepted 章节。
- backup / restore 资产问题。
- `docs/troubleshooting.md` 失败恢复手册。

不包含：

- 不扩张核心生成能力。
- 不新增核心 Agent / Workflow 节点。
- 不修改 prompt、CED、T9、five-gate、segment audit 或质量 hard gate。
- 不实现 run bundle / 脱敏诊断包；该能力路由到 Task 213。
- 不实现 profile validate / rollback / history；该能力路由到 Task 214。
- 不实现 wheel smoke、release checklist、CHANGELOG、CONTRIBUTING 或 issue templates；这些路由到 Task 215。

---

## 失败分类

| 分类 | 典型场景 | 恢复方向 |
|------|----------|----------|
| `config_error` | 缺 key、非法 endpoint、非法 checkpointer、非法预算 | 修正 `.env` / env 后运行 `doctor --json --init-db` |
| `database_error` | DB 不存在、schema 缺失、非法 `DATABASE_URL` | 运行 `doctor --json --init-db` 或修正 DB 路径 |
| `preflight_failed` | `songyan run` 在进入 pipeline 前失败 | 按 preflight fail 项修复后重跑 |
| `run_failed` | pipeline 已启动且输出 `run_id` 后失败 | 运行 `songyan report --run-id <run_id>`，再按报告恢复 |
| `missing_artifact` | report 缺 JSONL / run_id 错误 | 检查 `logs/chapter_runs/` 和 run 输出 |
| `no_accepted_content` | export 没有 accepted 章节 | 先生成并 accepted 章节，再导出 |
| `asset_restore_error` | backup project 缺失、坏 zip、restore 覆盖冲突 | `list-projects`、重新生成 backup、或显式 `--force` |

---

## 验收标准

必须满足：

- 至少 5 类失败有 CLI 输出或 troubleshooting 文档中的恢复命令。
- `report` 缺 run log 时不再安静成功，必须 exit 1 并提示检查路径 / run_id。
- `run` pipeline 已启动失败时保留 `run_id` 并提示 `songyan report --run-id <run_id>`。
- `run` preflight fail 输出恢复建议。
- `export` 无 accepted 章节输出恢复建议。
- `backup` 缺 project 输出恢复建议。
- `restore` 目标 DB 已存在或坏 zip 输出恢复建议。
- 不消耗真实 LLM 预算。

验证命令：

```powershell
python -m pytest tests/cli -q
python -m pytest tests/test_177_export_service.py tests/test_211_backup_restore.py tests/test_119_reporting_wrapper.py -q
ruff check src/ tests/
python -m pytest tests/ -q
```

---

## 交付物

- `tasks/212-v11-failure-recovery.md`
- `tasks/212-v11-failure-recovery-DONE.md`
- `docs/reports/212-failure-recovery-evidence.md`
- 相关代码和测试
- `docs/troubleshooting.md`
- `docs/quickstart.md`
- `docs/STATUS.md`
- `docs/INDEX.md`
- `tasks/V11-README.md`
