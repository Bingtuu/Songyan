# Task 192: xuanhuan Ch200 爬坡

> **阶段**: V10.2 跨体裁 Ch200 爬坡
> **类型**: Ch100 起点重建 / Ch200 分段长跑 / 段边界审计
> **优先级**: P0
> **依赖**: Task 189 / Task 190 / Task 191
> **状态**: ◐ Ch200 target 已初始化并推进到 Ch125；Ch111 `health_low_streak_halt` 已由 192.ad 修复；Ch120 `health_low_p1_halt` 与 failed_chapters=[112,117,118] 已由 192.ae 修复；Ch125 five-gate / segment audit / T9 PASS；下一步继续 Ch126→Ch150，并在 Ch150 执行 five-gate / segment audit / T9
> **预计工作量**: 大

---

## Goal

恢复或重建 xuanhuan clean Ch100 起点，并在通过 Task 190 同口径复核后，使用 Task 191 harness 推进 Ch101-Ch200，最终完成 xuanhuan Ch200 五门 + T9 + segment audit 验收。

---

## Context

Task 190 已判定 xuanhuan 为 `REBUILD_REQUIRED`：当前 `.tmp/task172b_xuanhuan_ch100.db` 已被覆盖，仅含 1 章、0 accepted，不能作为 Ch200 continuation source。归档报告 `archive/v8/reports/172b-xuanhuan-ch100-climb.md` 只保留历史终判指标，不能替代 SQLite source DB。

因此 Task 192 不能直接执行 `scripts/run_v10_ch200_climb.py --init-from-source --genre xuanhuan`。本任务必须先恢复或 clean rerun 到 Ch100，再按 Task 190 的 T9=0 / accepted Ch1-Ch100 / source inventory 口径提升为可用 source。

---

## In Scope（必须完成）

- [ ] 保护当前 `.tmp/task172b_xuanhuan_ch100.db` 现场：若需重建，先复制为带时间戳的诊断备份，不直接覆盖未记录样本。
- [ ] 选择并记录 Ch100 起点策略：
  - 优先：恢复原始 xuanhuan Ch100 DB 备份；
  - 备选：使用现有 Ch100 harness clean rerun 到 Ch100。
- [ ] 对恢复或重建后的 Ch100 source 执行 Task 190 同口径复核：accepted Ch1-Ch100、five-gate、segment audit、T9 meta/duplicate/timeline、profile effective/diff。
- [ ] 更新 `.tmp/190_ch100_source_inventory.json` 的 xuanhuan 记录，且在 DONE 文档中明确 canonical 事实。
- [ ] 使用 Task 191 harness 初始化 V10 Ch200 target DB：

```powershell
python scripts/run_v10_ch200_climb.py --init-from-source --genre xuanhuan --format json
```

- [ ] 使用 Task 191 harness 按 Ch125 / Ch150 / Ch175 / Ch200 分段推进：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 125 --genre xuanhuan
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 150 --genre xuanhuan
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 175 --genre xuanhuan
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 200 --genre xuanhuan
```

- [ ] 每个段边界执行审计，five-gate 必须显式绑定 Task 189 baseline：

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre xuanhuan --up-to <125|150|175|200> --baseline tasks/189-scifi-ch200-baseline.json
```

- [ ] 产出 `tasks/192-xuanhuan-ch200-climb-DONE.md`，并同步 `docs/STATUS.md`、`tasks/V10-README.md`、`docs/INDEX.md`、`README.md`、`AGENTS.md`。

---

## Out of Scope（明确不做）

- 不修改 five-gate / segment audit / CED / T9 判定函数。
- 不把优秀度信号接入 Writer、CreativeDirector 或自动硬门。
- 不为 xuanhuan 单独新增 Agent / Workflow 节点。
- 不使用历史归档报告替代 SQLite source DB。
- 不在任一段硬门失败后继续跑下一段。

---

## 数据与路径契约

| 项 | 路径 / 口径 |
|----|-------------|
| Ch100 source DB | `.tmp/task172b_xuanhuan_ch100.db`（恢复或重建后） |
| V10 Ch200 target DB | `.tmp/task_v10_xuanhuan_ch200.db` |
| V10 project file | `.tmp/task_v10_xuanhuan_project.json` |
| V10 segment log | `.tmp/task_v10_xuanhuan_segments.jsonl` |
| five-gate report | `.tmp/v10_xuanhuan_seg<checkpoint>_five_gate.json` |
| segment audit report | `.tmp/v10_xuanhuan_seg<checkpoint>_audit.json` |
| metrics report | `.tmp/v10_xuanhuan_seg<checkpoint>_metrics.md` |
| final report | `.tmp/v10_xuanhuan_ch200_final.json` |
| baseline | `tasks/189-scifi-ch200-baseline.json` |
| source inventory | `.tmp/190_ch100_source_inventory.json` 工作副本；DONE 文档记录 canonical 结论 |

---

## 执行阶段

### A. Ch100 source 恢复或重建

1. 记录当前 DB hash、project_id、accepted_count 和备份路径。
2. 如存在可信备份，恢复到 `.tmp/task172b_xuanhuan_ch100.db`。
3. 如无可信备份，执行 clean rerun 到 Ch100；重跑期间按既有 Ch100 harness 纪律分段监控，任何 halt 先冻结并开 `192.p` 后缀修复。
4. Ch100 source 达到 100/100 accepted 后，进入 B 阶段。

### B. Ch100 source 复核

必须重跑：

- `scripts/five_gate_check.py --genre xuanhuan --up-to 100`
- `scripts/segment_audit.py --up-to 100`
- `songyan metrics --chapters 1-100`
- `songyan profile show/diff --genre xuanhuan`

通过线：

- accepted 100/100，gap=0；
- budget peak < 1.0；
- CED 使用 consistency-only、merged/source、正文证据；
- T9 meta/artifact=0、duplicate=0、timeline=0；
- segment audit `critical_orphans=0` 且 `halt_would_fire=false`；
- profile 无意外 DB override。

### C. Ch200 初始化与分段推进

1. 使用 `scripts/run_v10_ch200_climb.py --init-from-source --genre xuanhuan` 初始化 V10 DB。
2. 依次推进 Ch125、Ch150、Ch175、Ch200。
3. 每段结束先审计再决定是否继续。

### D. 收口

生成 DONE 文档，至少记录：

- Ch100 source 恢复/重建方式；
- Ch100 复核证据；
- Ch200 每段 accepted、budget、CED、overdue、health、T9、segment audit；
- 成本、wrapper 结果、run_id；
- 是否有后缀修复任务；
- 与 sci-fi Ch200 baseline 的最终对比。

---

## 失败路由

| 失败点 | 处理 |
|--------|------|
| 无法恢复原始 Ch100 DB | clean rerun 到 Ch100；记录原 DB 覆盖事实，不继续依赖归档报告 |
| Ch100 rerun halt | 冻结 DB/日志/报告，开 `192.p` 后缀修复 |
| Ch100 T9 > 0 | deterministic clean 后 clean rerun 或局部修复，重判 T9=0 |
| `--init-from-source` 拒绝 source | 修复 source inventory / genre / T9 / accepted head，不绕过 harness |
| Ch125/150/175/200 任一五门失败 | 冻结现场，开 `192.<suffix>` 修复，不推进下一段 |
| wrapper 超时或成本熔断 | 记录 `WRAPPER_RESULT`、成本状态和 resume 命令，低频监控后继续 |

---

## Review 要求

完成前必须自查：

- 是否仍存在用归档报告替代 SQLite source 的路径；
- 是否任何命令绕过了 Task 191 harness；
- 是否所有 Ch125+ five-gate 都显式传入 Task 189 baseline；
- 是否 T9=0 是 clean rerun 后结果；
- 是否 source inventory 与 DONE 文档一致；
- 是否未污染 CED 口径。

---

## 测试与验证要求

常规代码改动必须执行：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 2400 -- python -m pytest tests/ -q
ruff check src/ tests/
git diff --check
```

若只做长跑和文档、无代码改动，至少执行：

```powershell
python scripts/run_v10_ch200_climb.py --status --genre xuanhuan --format json
python scripts/run_v10_ch200_climb.py --audit --genre xuanhuan --up-to <checkpoint> --baseline tasks/189-scifi-ch200-baseline.json --dry-run --format json
git diff --check
```

影响 harness、five-gate、segment audit 或 Ch200 口径时，必须重放 Task 189 Ch125/150/175/200 baseline。

---

## 验收标准

- [ ] xuanhuan clean Ch100 source 可复核，T9=0。
- [ ] `.tmp/190_ch100_source_inventory.json` 与 DONE 文档同步登记 xuanhuan 可用 source。
- [ ] `.tmp/task_v10_xuanhuan_ch200.db` 初始化自 clean Ch100 source，且 V10 `project_runs` 独立。
- [ ] Ch1-Ch200 全 accepted。
- [ ] Ch125 / Ch150 / Ch175 / Ch200 four checkpoints 五门 PASS。
- [ ] Ch200 T9=0；segment audit PASS。
- [ ] DONE 文档和核心入口已更新。
- [ ] 验证命令通过，提交一次，不 push。

---

## 参考文档

- `tasks/189-ch200-baseline-and-checkpoints-DONE.md`
- `tasks/189-scifi-ch200-baseline.json`
- `tasks/190-ch100-terminal-source-inventory-DONE.md`
- `tasks/191-ch200-harness-preparation-DONE.md`
- `archive/v8/reports/172b-xuanhuan-ch100-climb.md`
