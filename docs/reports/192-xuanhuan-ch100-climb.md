# Task 192: xuanhuan Ch50 爬坡验证报告

- 生成时间: 2026-07-25T21:30:40.891713
- 项目: `d160a55a51de4a2bb82440ebc03ec23a`  体裁: `xuanhuan`  目标: Ch50
- Gate: enforce / abort / resume  Halt: None

## 分段指标

| up_to | accepted | budget_peak | before_emerg_peak | emerg | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 25 | 0.8632 | 0.0 | 0 | 0 | 9.1 | 2.0874 |
| 50 | 50 | 0.8632 | 0.0 | 0 | 1 | 9.4 | 2.2304 |

## 结论

Ch50 生成链路完成，50/50 accepted、failed=[]、无 halt。初次段边界 T9 复核发现 duplicate=1，已通过 Task 192.s 版本化清理 Ch8 重复段落并复核为 T9=0；Ch50 source 当前可继续推进 Ch75/Ch100。

## Ch50 段边界审计

- Wrapper: `run-20260725-183118441` / `PASS_NORMAL_EXIT`
- DB SHA256: `5422A2234F1965CD07DEBA1B20CF834E91BA920287203C927B74A467274E90CA`
- five-gate: PASS（`.tmp/192_xuanhuan_ch50_five_gate.json`）
- segment audit: `critical_orphans=0`、`halt_would_fire=false`（`.tmp/192_xuanhuan_ch50_segment_audit.json`）
- T9 初判: **FAIL**（`.tmp/192_xuanhuan_ch50_t9.json`）：`meta_artifact=0`、`duplicate=1`、`timeline=0`
- duplicate hit: Ch8 paragraph 37 duplicates paragraph 22, similarity=1.0
- Task 192.s 修复: Ch8 `v-d62aa178` -> `clean-8-6-cd06a7b7`（versioned clean，parent 保留）
- T9 复判: **PASS**（`.tmp/192s_xuanhuan_ch50_t9_after.json`）：`meta_artifact=0`、`duplicate=0`、`timeline=0`
- 修复后 DB SHA256: `E375918948D8467987FE25138DAD7D16A47EEB82D0E95D7FA22370B34D641926`

初判失败现场已冻结到 `.tmp/backups/192s_xuanhuan_ch50_t9_duplicate_20260725-2132/`。后续可继续 Ch75，但仍必须在 Ch75/Ch100 边界重复 T9/five-gate/segment audit。
