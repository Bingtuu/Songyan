# Task 194: urban Ch200 爬坡

> **阶段**: V10.2 跨体裁 Ch200 爬坡
> **类型**: Ch200 分段长跑 / 段边界审计 / 长窗口稳定性验证
> **优先级**: P0
> **依赖**: Task 189 / Task 190 / Task 191
> **状态**: ◐ 进行中；Ch147 health halt 已修复，下一步 Ch148→Ch150
> **预计工作量**: 大

---

## Goal

使用 Task 191 harness 从 urban clean Ch100 source 初始化 V10 Ch200 DB，并按 Ch125 / Ch150 / Ch175 / Ch200 分段推进，验证 urban 从 Ch100 拉到 Ch200 后仍满足 V10 五门、T9 和 segment audit。

---

## Context

Task 190 已判定 urban 为当前唯一 `CONTINUE_READY` 体裁：`.tmp/task172b_urban_ch100.db` 具备 100/100 accepted、five-gate PASS、segment audit PASS、T9=0。Task 191 已实现 V10 Ch200 harness，可从该 source 安全复制到 `.tmp/task_v10_urban_ch200.db`，并创建独立 V10 `project_runs`。

Task 194 在技术上是 V10.2 中唯一无需 Ch100 修复即可初始化的非 sci-fi Ch200 任务。但当前 goal 要求按编号推进，因此不得用 urban 的 ready 状态跳过 Task 192/193。进入本任务后仍必须遵守段边界早停：任一 checkpoint 审计失败时，冻结现场并开后缀修复，不继续推进下一段。

---

## 执行记录（2026-07-30）

- Task 191 dry-run / init-from-source 已完成；target DB：`.tmp/task_v10_urban_ch200.db`；project_id=`81e345042b124ee2a73094b82e4be555`；run_id=`run-v10-urban-743a979a`。
- Ch101→Ch125 使用真实 `--to 125 --genre urban --cost-budget 8` 推进；wrapper `run-20260730-052658782` 正常退出，但初次结果 `final_status=partial`、`failed=[123]`。
- 194.a 修复 Ch123 settlement JSON parse 后 accepted gap：Ch123 head=`fix-123-accept-194a`，run restored completed 1..125、failed=[]。
- 194.b 修复 Ch125 T9 artifact：Ch101 head=`clean-101-6-08a9d35b`，Ch102 head=`clean-102-5-19c5821f`。
- Ch125 checkpoint 最终 PASS：five-gate PASS（budget=0.9595、CED/1k=0.0905、overdue=108、health=9.5、gap=0）、segment audit PASS（critical_orphans=0、halt_would_fire=false）、T9=0。
- Ch125 continuity audit：`cont_400f76fd`，health=9.5，critical_orphans=0。
- Ch126→Ch150 使用真实 `--to 150 --genre urban --cost-budget 8` 推进；wrapper `run-20260730-081620942` 在 Ch147 accepted 后触发 `health_low_streak_halt`（Ch145-Ch147 窗口 P2_total=2）。
- 194.c 修复 Ch147 两个 overdue foreshadowings：Ch147 head=`fix-147-health-194c`，continuity audit `cont_979d3a7d` health=8.0、P1=0、P2=0、critical_orphans=0；run restored completed 1..147、failed=[]。
- 下一步：仅在 194.c DONE 基础上继续 Ch148→Ch150；真实 `--to` 必须继续带 cost budget。

---

## In Scope（必须完成）

- [x] 确认 `.tmp/190_ch100_source_inventory.json` 中 urban 仍为 `CONTINUE_READY`，source DB / project_id / run_id 与 Task 190 一致。
- [x] 使用 Task 191 harness dry-run 初始化计划，确认 allowed=true、target path 正确、baseline 为 Task 189。
- [x] 使用 Task 191 harness 初始化 V10 Ch200 target DB：

```powershell
python scripts/run_v10_ch200_climb.py --init-from-source --genre urban --format json
```

- [x] 初始化后执行 status，确认 target DB、project file、V10 run_id、accepted Ch1-Ch100。

```powershell
python scripts/run_v10_ch200_climb.py --status --genre urban --format json
```

- [ ] 使用 Task 191 harness 按 Ch125 / Ch150 / Ch175 / Ch200 分段推进：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 125 --genre urban
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 150 --genre urban
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 175 --genre urban
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 200 --genre urban
```

- [ ] 每个段边界执行审计，five-gate 必须显式绑定 Task 189 baseline：

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to <125|150|175|200> --baseline tasks/189-scifi-ch200-baseline.json
```

- [ ] 产出 `tasks/194-urban-ch200-climb-DONE.md`，并同步核心入口文档。

---

## Out of Scope（明确不做）

- 不修复 xuanhuan 或 wuxia；它们分别属于 Task 192 / 193。
- 不修改 urban profile，除非长跑证据证明必须另开后缀修复。
- 不修改 five-gate / segment audit / CED / T9 判定函数。
- 不把优秀度信号接入 Writer、CreativeDirector 或自动硬门。
- 不在任一段硬门失败后继续跑下一段。

---

## 数据与路径契约

| 项 | 路径 / 口径 |
|----|-------------|
| Ch100 source DB | `.tmp/task172b_urban_ch100.db` |
| Ch100 source project_id | `81e345042b124ee2a73094b82e4be555` |
| Ch100 source run_id | `run-d22b1a44` |
| source verdict | `CONTINUE_READY` |
| V10 Ch200 target DB | `.tmp/task_v10_urban_ch200.db` |
| V10 project file | `.tmp/task_v10_urban_project.json` |
| V10 segment log | `.tmp/task_v10_urban_segments.jsonl` |
| five-gate report | `.tmp/v10_urban_seg<checkpoint>_five_gate.json` |
| segment audit report | `.tmp/v10_urban_seg<checkpoint>_audit.json` |
| metrics report | `.tmp/v10_urban_seg<checkpoint>_metrics.md` |
| final report | `.tmp/v10_urban_ch200_final.json` |
| baseline | `tasks/189-scifi-ch200-baseline.json` |

---

## 执行阶段

### A. 初始化前复核

必须先执行：

```powershell
python scripts/run_v10_ch200_climb.py --init-from-source --genre urban --dry-run --format json
```

通过线：

- `allowed=true`；
- source DB 为 `.tmp/task172b_urban_ch100.db`；
- project_id 为 `81e345042b124ee2a73094b82e4be555`；
- target DB 为 `.tmp/task_v10_urban_ch200.db`；
- baseline 为 `tasks/189-scifi-ch200-baseline.json`。

### B. 初始化 target DB

执行真实 init-from-source。若 target DB 已存在，不得直接 `--force`，必须先判断是否为本任务旧现场：

- 若为未使用的失败初始化，可备份后 force；
- 若已包含 Ch101+，不得覆盖，先冻结现场并 review。

### C. 分段长跑

1. Ch101-Ch125：完成后审计 Ch125。
2. Ch126-Ch150：仅在 Ch125 PASS 后继续。
3. Ch151-Ch175：仅在 Ch150 PASS 后继续。
4. Ch176-Ch200：仅在 Ch175 PASS 后继续。

长跑监控采用低频策略，默认每 30 分钟检查一次：

- accepted 数；
- halt；
- wrapper 状态；
- 成本；
- 最新 logs/app 与 logs/chapter_runs；
- 是否到达段边界。

### D. 段边界审计

每个 checkpoint 必须落盘：

- five-gate JSON；
- segment audit JSON；
- metrics/T9 Markdown；
- segment log 记录；
- human summary。

通过线：

- accepted 无 gap；
- budget peak < 1.0；
- consistency CED ≤ sci-fi 同章尺度 × 1.15；
- overdue ≤ sci-fi 同章尺度；
- health ≥ 8.0；
- T9=0；
- segment audit `critical_orphans=0` 且 `halt_would_fire=false`。

### E. 收口

DONE 文档至少记录：

- 初始化 evidence；
- V10 run_id / project_id / DB path；
- Ch125/150/175/200 每段指标；
- 成本与 wrapper 结果；
- T9 与 segment audit；
- 是否产生后缀修复任务；
- 与 sci-fi Ch200 baseline 的最终对比。

---

## 失败路由

| 失败点 | 处理 |
|--------|------|
| dry-run allowed=false | 停止，回查 Task 190 inventory 和 source DB，不手动复制 |
| target DB 已存在 | 先 status 与备份；含 Ch101+ 时不得覆盖 |
| `--to` 缺 project_id 或 run_id | 回查 project file / project_runs；必要时重新 init-from-source |
| wrapper 超时或成本熔断 | 记录 `WRAPPER_RESULT`、成本状态和 resume 命令，低频监控后继续 |
| Ch125/150/175/200 任一五门失败 | 冻结现场，开 `194.<suffix>` 修复，不推进下一段 |
| T9 > 0 | 定位正文证据；机制修复后 clean rerun，不解释性豁免 |

---

## Review 要求

完成前必须自查：

- 是否任何命令绕过了 Task 191 harness；
- 是否 `--init-from-source` source 与 Task 190 inventory 严格匹配；
- 是否所有 Ch125+ five-gate 都显式传入 Task 189 baseline；
- 是否段边界未跳审；
- 是否 CED 口径仍为 consistency-only、merged/source、正文证据；
- 是否未将优秀度、文学 craft、同质化或 AI 腔混入五门。

---

## 测试与验证要求

若无代码改动，至少执行：

```powershell
python scripts/run_v10_ch200_climb.py --init-from-source --genre urban --dry-run --format json
python scripts/run_v10_ch200_climb.py --status --genre urban --format json
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to <checkpoint> --baseline tasks/189-scifi-ch200-baseline.json --dry-run --format json
git diff --check
```

若有代码改动，必须执行：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 2400 -- python -m pytest tests/ -q
ruff check src/ tests/
git diff --check
```

影响 harness、five-gate、segment audit 或 Ch200 口径时，必须重放 Task 189 Ch125/150/175/200 baseline。

---

## 验收标准

- [ ] urban V10 target DB 初始化自 Task 190 `CONTINUE_READY` source。
- [ ] V10 project file 与 target DB `project_runs` 一致。
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
- `archive/v9/187-urban-ch100-climb-execution-DONE.md`
