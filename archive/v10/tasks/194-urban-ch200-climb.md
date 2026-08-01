# Task 194: urban Ch200 爬坡

> **阶段**: V10.2 跨体裁 Ch200 爬坡
> **类型**: Ch200 分段长跑 / 段边界审计 / 长窗口稳定性验证
> **优先级**: P0
> **依赖**: Task 189 / Task 190 / Task 191
> **状态**: ✅ 完成；urban Ch200 已 PASS，DONE：`tasks/194-urban-ch200-climb-DONE.md`
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
- Ch148→Ch150 resume 时曾以 `--cost-budget 4` 触发非质量 `cost_budget` pause（累计 cost 已高于新预算），随后用 `--cost-budget 12` 继续；wrapper `run-20260730-112317794` PASS_NORMAL_EXIT，run completed @150、failed=[]、total_cost=7.307357。
- Ch150 初判 five-gate PASS，但 segment audit `critical_orphans=1` / `halt_would_fire=true`，T9 meta/artifact=2、duplicate=1，已冻结并路由 194.d。
- 194.d 修复 Ch135/Ch139 T9 hard hits 与 Ch150 segment critical orphan：Ch135 head=`clean-135-4-3a31a17d`，Ch139 head=`clean-139-5-7b378d26`，Ch150 head=`fix-150-segment-194d`。
- Ch150 checkpoint 最终 PASS：accepted=150/150、failed=[]、five-gate PASS（budget=0.9595、CED/1k=0.0786、overdue=116、health=8.7、gap=0）、segment audit PASS（critical_orphans=0、halt_would_fire=false）、T9=0（timeline=2 report-only）。
- Ch151→Ch175 使用真实 `--to 175 --genre urban --cost-budget 16` 推进；wrapper `run-20260730-121831667` 中 Ch151-Ch161 accepted，Ch162 在 GoalPlanner 阶段触发 `LLM 返回内容无法解析为 JSON（标准解析和 repair 均失败）`，raw_response 为空。
- 为避免 isolate 继续形成更复杂 gap，在 Ch163 启动后人工中断 wrapper，并使用 `ProjectRunRepository.update()` 冻结 run：status=`paused`、pause_reason=`manual_freeze:ch162_goal_planner_json_parse`、current_chapter=162、completed_count=161、failed=[162]、total_cost=8.748416；冻结目录 `.tmp/backups/194e_urban_ch162_goal_planner_json_parse_20260730-1326/`。
- 194.e 使用 Task 191 harness resume `--to 175 --genre urban --cost-budget 16` 从 Ch162 重跑，Ch162 GoalPlanner 未复现，Ch162 accepted/current head=`v-345029d6`，随后继续生成 Ch163-Ch174。
- Ch174 后触发 `health_low_streak_halt` 硬门：window=Ch172-Ch174、P2_total=3 >= limit=2；run 已冻结为 status=`paused`、pause_reason=`auto_halt:health_low_streak_halt`、current_chapter=174、completed=1..174、failed=[]、total_cost=10.554465；Ch172=`v-bad824d1`、Ch173=`v-f52c35c6`、Ch174=`v-f5a8d2d8`；最新 continuity `cont_b8daaae4` health=7.9；冻结目录 `.tmp/backups/194f_urban_ch174_health_low_streak_halt_20260730-1501/`。
- 194.f 修复 3 条 overdue foreshadowing 状态并重跑 continuity @174：`cont_d2b52f65` health=8.0、P1=0、P2=0、overdue=0；Ch174 health hard gate 根因清除，DONE `tasks/194.f-urban-ch174-health-low-streak-halt-DONE.md`。
- Ch175 resume 使用真实 `--to 175 --genre urban --cost-budget 16` 完成，run completed 1..175、failed=[]、total_cost=10.710629，Ch175 accepted/current head=`v-2f8b36fe`。
- Ch175 checkpoint audit 显式绑定 Task 189 baseline 后 five-gate PASS、segment audit PASS（critical_orphans=0、halt_would_fire=false），但 T9 hard gate FAIL：meta=2（Ch171 protected directive `【保护内容 — 请勿修改】`，Ch175 pure ellipsis paragraph `...`）、duplicate=0、timeline=2 report-only；冻结目录 `.tmp/backups/194g_urban_ch175_t9_meta_hard_gate_20260730-1542/`。
- 194.g deterministic clean：Ch171 `v-5ac30ced` → `clean-171-5-c9c50b0a`；Ch175 `v-2f8b36fe` → `clean-175-4-d429a6b1`；两章 RAG chunks 已重建。
- Ch175 checkpoint post-clean PASS：run completed=1..175、failed=[]、total_cost=10.710629；five-gate PASS、segment PASS、T9 PASS（meta=0、duplicate=0、timeline=2 report-only）。
- Ch176→Ch200 使用真实 `--to 200 --genre urban --cost-budget 20` 推进；Ch176-Ch178 accepted（Ch176=`v-9e8700c1`、Ch177=`v-4fccf48d`、Ch178=`v-424077ac`）。
- Ch179 质量门后进入 SettlementExtractor，触发 numerical validation failure：`heartbeat_interval_ms closing_value (480.0) 不等于 公式值 (362.000)`；Ch179 未 accepted。pipeline 随后继续进入 Ch180，已人工中断并冻结 run：status=`paused`、pause_reason=`manual_freeze:ch179_settlement_numerical_validation`、current_chapter=179、completed=1..178、failed=[179]、total_cost=11.259048；冻结目录 `.tmp/backups/194h_urban_ch179_settlement_numerical_validation_20260730-1813/`。
- 194.h 使用 Task 191 harness resume（真实 `--to 200 --genre urban --cost-budget 20`）后 Ch179 retry 成功，Ch179 accepted/current head=`v-4b8815b0`，accepted gap 清除，DONE `tasks/194.h-urban-ch179-settlement-numerical-validation-DONE.md`。
- 同一 run 继续推进 Ch180-Ch198，Ch196 head=`v-06a477dc`，Ch197 head=`v-c4e6aad1`，Ch198 head=`v-ce44758d`，completed=1..198，failed=[]，total_cost=14.349237。
- Ch198 accepted 后自动触发 `health_low_streak_halt`：window=Ch196-Ch198、P2_total=13 >= limit=2；latest continuity `cont_523ceb63` health=7.7、overdue_foreshadowings=13；run 已冻结为 status=`paused`、pause_reason=`auto_halt:health_low_streak_halt`、current_chapter=198、completed=1..198、failed=[]；冻结目录 `.tmp/backups/194i_urban_ch198_health_low_streak_halt_20260730-2145/`。
- 194.i 修复完成：12 条已兑现 overdue foreshadowings resolved，保留 1 条开放目标；Ch182/186/187/196 T9 clean heads=`clean-182-t9-194i` / `clean-186-t9-194i` / `clean-187-t9-194i` / `clean-196-t9-194i`；Ch198 continuity patch head=`fix-198-segment-194i`；continuity @198 `cont_da02974e` health=8.1、P1=0、P2=1；segment audit @198 PASS；T9 @198 PASS；run restored running、completed=1..198、failed=[]。
- Ch199→Ch200 使用真实 `--to 200 --genre urban --cost-budget 20` resume；wrapper `run-20260731-121733537` PASS_NORMAL_EXIT，但 run final_status=partial、completed=1..198、failed=[199,200]。
- Ch199 Writer 返回 0 字，LiteraryAuditor 空响应 parse failed；Ch199 current draft=`v-199-1-8a64d8c8`、word_count=0、accepted=null。Ch200 GoalPlanner 空响应 parse failed，无 head。
- 已冻结 194.j：run status=`paused`、pause_reason=`manual_freeze:ch199_200_llm_empty_parse`、current_chapter=199、completed=1..198、failed=[199,200]、total_cost=14.43615；冻结目录 `.tmp/backups/194j_urban_ch199_200_llm_empty_parse_20260731-1225/`。
- 为 194.j 新增 Task 191 harness `--on-failure retry`（默认不变），聚焦测试 11 passed，ruff passed；`run-20260731-144318657` / `run-20260731-150024943` 使用 `--on-failure retry` 后仍因 LLM 空响应卡在 Ch199。
- 最新冻结：run status=`paused`、pause_reason=`manual_freeze:ch199_llm_empty_parse_retry_failed`、current_chapter=199、completed=1..198、failed=[199]、total_cost=14.666101；最新备份 `.tmp/backups/194j_retry_on_failure_still_failed_20260731-1504/`。
- 194.j 最终登记 fallback model：`deepseek/deepseek-v4-flash` 多次空响应未恢复，临时显式使用 `deepseek/deepseek-chat` 完成 Ch199/Ch200；Ch199 accepted/current head=`v-6635ac72`，Ch200 accepted/current head=`v-b687fc47`，run completed=1..200、failed=[]、total_cost=14.91622。DONE：`tasks/194.j-urban-ch199-200-llm-empty-parse-DONE.md`。
- Ch200 终点审计初判 five-gate PASS、segment PASS，但 T9 meta=1，命中 `Echo_Core心跳维持脚本/注释区`；已冻结并路由 194.k，备份 `.tmp/backups/194k_urban_ch200_t9_meta_hard_gate_20260731-1636/`。
- 194.k 创建 Ch200 deterministic clean version `clean-200-t9-194k`（parent=`v-b687fc47`），将 `Echo_Core心跳维持脚本/注释区` 改为 `Echo_Core心跳维持脚本的注释区`，Ch200 RAG chunks 已重建。
- Ch200 终点最终 PASS：run status=`completed`、current_chapter=200、completed=1..200、failed=[]、pause_reason=null；five-gate PASS（budget=0.9595、CED/1k=0.066、overdue=153、health=8.2、gap=0）、segment audit PASS（critical_orphans=0、halt_would_fire=false）、T9=0（timeline=3 report-only）；final DB SHA256 `08921291C3F9E3A5F42199CD7AA109A1164372150D42C08001A845DA9A212861`。DONE：`tasks/194.k-urban-ch200-t9-meta-hard-gate-DONE.md`。

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

- [x] 使用 Task 191 harness 按 Ch125 / Ch150 / Ch175 / Ch200 分段推进：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 125 --genre urban --cost-budget <budget>
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 150 --genre urban --cost-budget <budget>
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 175 --genre urban --cost-budget <budget>
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -- python scripts/run_v10_ch200_climb.py --to 200 --genre urban --cost-budget <budget>
```

- [x] 每个段边界执行审计，five-gate 必须显式绑定 Task 189 baseline：

```powershell
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to <125|150|175|200> --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json
```

- [x] 产出 `tasks/194-urban-ch200-climb-DONE.md`，并同步核心入口文档。

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
| baseline | `archive/v10/artifacts/189-scifi-ch200-baseline.json` |

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
- baseline 为 `archive/v10/artifacts/189-scifi-ch200-baseline.json`。

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
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to <checkpoint> --baseline archive/v10/artifacts/189-scifi-ch200-baseline.json --dry-run --format json
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

- [x] urban V10 target DB 初始化自 Task 190 `CONTINUE_READY` source。
- [x] V10 project file 与 target DB `project_runs` 一致。
- [x] Ch1-Ch200 全 accepted。
- [x] Ch125 / Ch150 / Ch175 / Ch200 four checkpoints 五门 PASS。
- [x] Ch200 T9=0；segment audit PASS。
- [x] DONE 文档和核心入口已更新。
- [ ] 验证命令通过，提交一次，不 push。

---

## 参考文档

- `archive/v10/tasks/189-ch200-baseline-and-checkpoints-DONE.md`
- `archive/v10/artifacts/189-scifi-ch200-baseline.json`
- `archive/v10/tasks/190-ch100-terminal-source-inventory-DONE.md`
- `archive/v10/tasks/191-ch200-harness-preparation-DONE.md`
- `archive/v9/187-urban-ch100-climb-execution-DONE.md`
