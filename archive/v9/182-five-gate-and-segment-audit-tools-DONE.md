# Task 182 DONE: 五门判定器与段审计收编

> 完成日期：2026-07-20
> 阶段：V9.3 爬坡工具链
> 对应任务书：`archive/v9/182-five-gate-and-segment-audit-tools.md`

## 结论

Task 182 已完成。V8 遗留在 `.tmp/` 的五门判定器与段审计工具已收编为正式 `scripts/` 工具，并拆出可测核心模块；sci-fi Ch100 baseline 已迁入包内资源，CED 字段使用 consistency-only 冻结口径。xuanhuan/wuxia 既有 Ch100 DB 重放结果与 V8 归档报告一致。

## 变更范围

- `src/songyan/evals/five_gate_acceptance.py`
  - 五门指标采集、baseline 插值、gate 判定、JSON/text report。
  - SQLite URI 只读模式，禁止历史 DB 被误创建或迁移。
  - budget gate 检测 `adaptive_halt_decisions` 与 `project_runs` halt 状态。
- `src/songyan/evals/segment_audit.py`
  - legacy evidence hotspot、next-audit orphan prediction、health trajectory。
  - `up_to` 边界校验，防止超出 accepted 证据范围。
- `src/songyan/evals/baselines/scifi_ch100_baseline.json`
  - 包内 sci-fi Ch25/50/75/100 baseline。
- `scripts/five_gate_check.py`
  - 参数化五门判定入口。
- `scripts/segment_audit.py`
  - 参数化段审计入口。
- `tests/test_182_five_gate_tools.py`
  - 10 个聚焦测试覆盖核心口径与 review 修复。

## 验收结果

| 项 | 结果 |
|---|---|
| xuanhuan Ch100 重放 | PASS：100/100、budget 0.9811、CED 0.4434、overdue 166、health 9.1 |
| wuxia Ch100 重放 | PASS：100/100、budget 0.9646、CED 0.1662、overdue 35、health 8.3 |
| `.tmp/vdim_compare.py` 对照 | xuanhuan/wuxia Ch100 均 PASS，逐门一致 |
| 聚焦测试 | `10 passed` |
| 全量默认 pytest | `2914 passed, 2 skipped, 1 xfailed, 7 warnings`；`WRAPPER_RESULT=PASS_NORMAL_EXIT` |
| CLI 测试 | `35 passed` |
| mypy | `Success: no issues found in 174 source files` |
| Ruff | All checks passed |
| Code review | 1 个 P2 + 1 个本地 review 问题，均已修复并补测 |

## 备注

- 正式 baseline JSON 同时保留 legacy 宽口径 CED 字段，仅用于审计追溯；五门判定只使用 corrected consistency-only CED。
- 本任务未接入 `songyan` 主 CLI；保持 `scripts/` 正式工具形态，符合 V9 A7 边界。
- 真实 `.tmp` DB 重放为本地验收，不纳入默认 CI。
