# Task 190: Ch100 终点事实源盘点 — DONE

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 只读盘点 / 事实源审计 / continuation 准入
> **优先级**: P0（决定 192-194 是续跑还是重建起点）
> **状态**: ✅ 完成
> **日期**: 2026-07-24

---

## 任务边界

本任务只判断 xuanhuan / wuxia / urban 三个体裁的 Ch100 终点是否可作为 Ch200 起点，不启动 Ch101，不修改 DB，不改 profile，不做修复。

---

## 盘点结论

| 体裁 | 判定 | 说明 |
|------|------|------|
| xuanhuan | **REBUILD_REQUIRED** | DB 已被覆盖：当前 `.tmp/task172b_xuanhuan_ch100.db` 仅含 1 章 0 accepted，project_id 已变。原终判 project_id 为 `1e7ce6279b224e7f8e476f6f4e963417`（见 `archive/v8/reports/172b-xuanhuan-ch100-climb.md`）。该报告登记 Ch100 终判指标（100/100 accepted, budget 0.9811, CED 0.4434, overdue 166, health 9.1），但 DB 本身已不可用。 |
| wuxia | **BLOCKED_DIRTY_SAMPLE** | 100/100 accepted，five-gate PASS，segment audit PASS。但 T9=1（Ch28 省略号占位段 `……`），不满足验收判据 #2 "T9=0" 的硬要求。需在 Ch200 启动前对 Ch28 执行 deterministic clean 后重判。 |
| urban | **CONTINUE_READY** | 100/100 accepted，five-gate PASS，segment audit PASS，T9=0。 |

---

## 事实源明细

### xuanhuan — REBUILD_REQUIRED

| 字段 | 值 |
|------|----|
| db_path | `.tmp/task172b_xuanhuan_ch100.db` |
| project_id（当前） | `beaeb146f1a3489ab3018183e92ee6fe` |
| project_id（原终判） | `1e7ce6279b224e7f8e476f6f4e963417`（来源：`archive/v8/reports/172b-xuanhuan-ch100-climb.md`） |
| run_id（当前） | `run-da59168d`（running，仅 Ch1） |
| accepted_count | 0 |
| 原因 | DB 被覆盖，原 Ch100 数据已丢失 |
| 路由 | 重建 clean Ch100 或恢复原始 DB；Task 192 不可在恢复前启动 |
| 审计说明 | 因 DB 无 accepted 章节，五门复算、段审计、T9 复算、profile 查询均跳过。`.tmp/task172b_xuanhuan_segments.jsonl` 仅保留段 1（Ch1-25）的重复快照数据，不是 Ch100 终判口径；Ch100 终判指标以归档报告 `archive/v8/reports/172b-xuanhuan-ch100-climb.md` 为准。 |

### wuxia — BLOCKED_DIRTY_SAMPLE

| 字段 | 值 |
|------|----|
| db_path | `.tmp/task172b_wuxia_ch100.db` |
| project_id | `273a8408be8e4caf8cbc1e91954da600` |
| run_id | `run-82968662`（completed） |
| accepted | 100/100 |
| five-gate | PASS（budget 0.9646, CED 0.1662, overdue 35, health 8.3, gap 0） |
| segment audit | critical_orphans=0, halt_would_fire=false |
| T9 | meta=1（Ch28 省略号占位段 `……`）, dup=0, timeline=0 |
| 阻塞原因 | T9=1 不满足验收判据 #2 "T9=0"。1 处 meta artifact 为 Ch28 的省略号占位段落，非系统性，但 V10 守护项规定 T9 不接受解释性豁免。 |
| 路由 | 在 Task 193（wuxia Ch200 爬坡）启动前对 Ch28 执行 deterministic clean，clean 后重跑 T9 确认 T9=0 即可转为 CONTINUE_READY；无需完整 rebuild。 |
| profile | registry（base_budget=10500, foreshadowing_horizon_floor=48），DB 无 override |

### urban — CONTINUE_READY

| 字段 | 值 |
|------|----|
| db_path | `.tmp/task172b_urban_ch100.db` |
| project_id | `81e345042b124ee2a73094b82e4be555` |
| run_id | `run-d22b1a44`（completed） |
| accepted | 100/100 |
| five-gate | PASS（budget 0.9595, CED 0.11, overdue 100, health 8.6, gap 0） |
| segment audit | critical_orphans=0, halt_would_fire=false |
| T9 | meta=0, dup=0, timeline=0 |
| profile | registry（base_budget=14000 after 187.p），DB 无 override |
| 备注 | segment_audit health_trajectory 截断在 Ch99（health 8.6），缺少 Ch100 最终检查点；不影响结论（health 值一致），属审计工具边界行为。 |

---

## 产物

| 文件 | 内容 |
|------|------|
| `.tmp/190_ch100_source_inventory.json` | 三体裁统一盘点表与准入结论 |
| `.tmp/190_wuxia_ch100_five_gate.json` | wuxia Ch100 五门复算 |
| `.tmp/190_urban_ch100_five_gate.json` | urban Ch100 五门复算 |
| `.tmp/190_wuxia_ch100_segment_audit.json` | wuxia Ch100 段审计 |
| `.tmp/190_urban_ch100_segment_audit.json` | urban Ch100 段审计 |
| `.tmp/190_wuxia_ch100_metrics.md` | wuxia T9 复算报告 |
| `.tmp/190_urban_ch100_metrics.md` | urban T9 复算报告 |
| `.tmp/190_wuxia_profile_view.json` | wuxia profile effective 视图（12KB+，registry 全字段，DB 无 override） |
| `.tmp/190_wuxia_profile_diff.json` | wuxia profile DB override 差异（空 rows） |
| `.tmp/190_urban_profile_view.json` | urban profile effective 视图（12KB+，registry 全字段，DB 无 override） |
| `.tmp/190_urban_profile_diff.json` | urban profile DB override 差异（空 rows） |
| `tasks/190-ch100-terminal-source-inventory-DONE.md` | 本文件 |

> xuanhuan 因 DB 无 accepted 章节，未产出五门/段审计/T9/profile 文件；历史终判指标以归档报告为准。

---

## 验证命令

### five-gate + segment audit

```powershell
python .tmp/_190_run_audit.py
```

结果：wuxia PASS（100/100, budget 0.9646, CED 0.1662, overdue 35, health 8.3），urban PASS（100/100, budget 0.9595, CED 0.11, overdue 100, health 8.6）。xuanhuan 跳过（DB 无 accepted 章节）。

### T9 复算

```powershell
python .tmp/_190_t9.py
```

结果：wuxia meta=1（Ch28 省略号占位段）, dup=0, timeline=0；urban meta=0, dup=0, timeline=0。xuanhuan 跳过。

### T9 详情（wuxia Ch28 定位）

```powershell
python .tmp/_190_t9_detail.py
```

结果：确认 wuxia Ch28 的 1 处 meta artifact 为省略号占位段落（`……`），非系统性。

### profile

```powershell
python .tmp/_190_profile2.py
```

结果：wuxia/urban profile view 均 12KB+（registry 全字段，DB 无 override），diff 均空 rows（无 DB override 差异）。

---

## 后续依赖

- Task 191（Ch200 harness 准备）：以本任务输出的 `CONTINUE_READY` 体裁（urban）和 `BLOCKED_DIRTY_SAMPLE` 体裁（wuxia，需 pre-clean）为准。
- Task 192（xuanhuan Ch200 爬坡）：必须先恢复或重建 xuanhuan Ch100 DB，不可在当前 DB 上续跑。
- Task 193（wuxia Ch200 爬坡）：需在 Ch101 启动前对 Ch28 执行 deterministic clean 并重跑 T9 确认 T9=0；其余章节可直接续跑。
- Task 194（urban Ch200 爬坡）：可从当前 DB 的 Ch101 开始。
