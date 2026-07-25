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

Ch50 生成链路完成，50/50 accepted、failed=[]、无 halt；但段边界 T9 复核未通过，不能作为 clean source 继续推进。

## Ch50 段边界审计

- Wrapper: `run-20260725-183118441` / `PASS_NORMAL_EXIT`
- DB SHA256: `5422A2234F1965CD07DEBA1B20CF834E91BA920287203C927B74A467274E90CA`
- five-gate: PASS（`.tmp/192_xuanhuan_ch50_five_gate.json`）
- segment audit: `critical_orphans=0`、`halt_would_fire=false`（`.tmp/192_xuanhuan_ch50_segment_audit.json`）
- T9: **FAIL**（`.tmp/192_xuanhuan_ch50_t9.json`）：`meta_artifact=0`、`duplicate=1`、`timeline=0`
- duplicate hit: Ch8 paragraph 37 duplicates paragraph 22, similarity=1.0

现场已冻结到 `.tmp/backups/192s_xuanhuan_ch50_t9_duplicate_20260725-2132/`。后续必须先完成 `tasks/192.s-xuanhuan-ch50-t9-duplicate-clean.md`，清到 T9=0 后再继续 Ch75/Ch100。
