# Task 113: Ch101 收敛回滚与 Settlement 阻断修复

> **文档状态**: 历史规划稿。Task 113 已完成，最终交付与验证结果见 `tasks/113-ch101-convergence-settlement-blocker-fix-DONE.md`。
>
> **Phase**: V5.0 Phase 4 — 150 章规模化验证前置修复
> **优先级**: P0
> **依赖**: Task 112 完成；Task 113 首次长跑 incident `run-6b462cb9`
> **预计工作量**: 1-2 天

---

## Goal

修复 Task 113 首次启动时 Ch101 暴露的收敛回滚与 settlement 边界阻断：系统在出现 `revision_rebound_detected` 后没有稳定选择已知最佳版本，最终 head 停在 draft 且 `accepted_version_id=NULL`，导致 settlement/summary 被正确阻断但长跑无法继续。

本 Task 的目标不是绕过 QualityGate，也不是让 skipped settlement 伪装成功，而是让修复耗尽后的版本选择、HumanGate、QualityGate、SettlementExtractor 和 run logger 的状态契约保持一致。

## Incident Context

Task 113 原计划执行 Ch101-Ch150 流式验证。按防卡协议先启动 Ch101-Ch110 窗口，运行在 Ch101 熔断：

- Run ID: `run-6b462cb9`
- JSONL: `logs/chapter_runs/run-6b462cb9.jsonl`
- Stdout: `logs/task113/songyan-101-110-20260619-220058.out.log`
- Stderr: `logs/task113/songyan-101-110-20260619-220058.err.log`
- DG-2 最小报告: `logs/task113/report-run-6b462cb9.md`
- Incident 记录: `logs/task113/incident-run-6b462cb9.md`

已观察到的关键状态：

- `rev-101-3-6997f443` 曾达到 `overall=0.9155`
- 后续 `v-101-4-7dbe616a` 降到 `overall=0.7258`，`readability=0.4885`
- 日志出现 `revision_rebound_detected`
- 随后 `quality_gate.convergence_failed`
- `settlement_extractor_node.skipping_settlement`
- JSONL 记录 `success=false`, `error_stage=settlement_review`
- DB 中 Ch101 为 `status=draft`, `accepted_version_id=NULL`

这符合 Task 111d 的事实源保护：`_skip_settlement=True` 不能被当作 accepted/done。真正需要修的是收敛失败后的 final version/head 选择与状态合约。

## In Scope（必须完成）

- [ ] **复盘 Ch101 失败路径**
  - 读取 `run-6b462cb9` 的 stdout/stderr/JSONL/DB 现场。
  - 对比 `v-101-1-f917de2e`、`rev-101-2-6848832b`、`rev-101-3-6997f443`、`v-101-4-7dbe616a` 的 score card、review reports、head 更新顺序。
  - 明确 `revision_rebound_detected` 后为何 head 最终指向低分/abandoned 版本。

- [ ] **修复版本选择契约**
  - 修复耗尽或 rebound 后必须稳定选择最高可接受 best version。
  - 不允许 abandoned version 成为 `chapter_heads.current_version_id` 的最终候选。
  - `current_version_id`、`_best_version_id`、`_score_card`、`_quality_gate_passed` 必须指向同一个最终候选。

- [ ] **修复 QualityGate/HumanGate/Settlement 状态契约**
  - HumanGate auto-confirm 不得把 `_skip_settlement=True` 的状态推进为可落库成功。
  - 若 best version 可接受，应走正常 settlement + accept + summary 边界。
  - 若 best version 仍不可接受，应停在 `settlement_review` 或明确的人审状态，不得产生 accepted/settlement/summary 半提交。
  - run logger 必须准确区分：
    - QG 通过并完成 settlement/summary
    - QG 收敛失败但有人审阻断
    - settlement validation failed

- [ ] **补齐回归测试**
  - 增加 Ch101 incident 级别的单元/集成测试，覆盖 rebound 后 best version 不被劣化版本覆盖。
  - 覆盖 `_skip_settlement=True` 不会被误记为 success。
  - 覆盖 accepted 后 settlement + summary 仍保持原子边界。

- [ ] **恢复 Ch101 基线**
  - 修复后只重跑 Ch101。
  - 验证 Ch101 `accepted_version_id` 非空。
  - 验证 Ch101 settlement 成功或按契约明确阻断。
  - 验证 Ch101 summary 存在，除非明确进入人审阻断且未 accepted。

## Out of Scope（明确不做）

- 不启动 Ch102-Ch150 长跑。
- 不调整评分阈值或 Prompt 以掩盖 Ch101。
- 不绕过 Task 111d 的 settlement 事实源保护。
- 不清理历史旧数据，除非它直接阻断 Ch101 修复验证。

## 代码关注点

- `src/songyan/workflows/_nodes.py`
  - `quality_gate_node`
  - `human_gate_node`
  - `settlement_extractor_node`
  - rebound/best version 相关状态字段
- `src/songyan/workflows/phase2_graph.py`
  - `_run_single_chapter`
  - success/failure 判定
  - `error_stage` 和 retry/熔断行为
- `src/songyan/workflows/_run_logger.py`
  - `settlement_success`
  - `quality_gate_passed`
  - `convergence_failed`
  - `skip_settlement`
- DB 表：
  - `chapter_heads`
  - `chapter_versions`
  - `review_reports`
  - `project_runs`

## 测试要求

### Layer 1: 聚焦测试

- [ ] 新增/更新 workflow 节点测试，复现 Ch101 rebound 后 head 选择问题。
- [ ] 新增/更新 run logger 测试，验证 `_skip_settlement=True` 记录为失败/阻断而非成功。
- [ ] 新增/更新 settlement 边界测试，确保 invalid/skipped settlement 不产生 accepted 半提交。

### Layer 2: 回归测试

- [ ] 按 `AGENTS.md` Windows 防卡协议运行相关测试。
- [ ] 按防卡协议运行 `pytest tests/ -q`。
- [ ] `ruff check src/ tests/` 无本 Task 新增 lint；历史存量 lint 记录到 DONE 文档。

### Layer 3: 业务回放

- [ ] 只重跑 Ch101：

```bash
songyan run --project-id proj-e74ef1e4 --chapters 101-101 --mode-id webnovel_intense --auto-confirm
```

- [ ] 记录 run id、stdout/stderr、JSONL。
- [ ] 查询并记录 Ch101 head、accepted version、settlement、summary 状态。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| rebound 后 final head | 指向最高可接受 best version，不指向 abandoned/劣化版本 |
| `_skip_settlement=True` | 不会被误判为 successful accepted chapter |
| accepted + settlement + summary | 原子一致，无半提交 |
| Ch101 重跑 | 不再因 `settlement_review / unknown_error` 阻断 |
| JSONL | 能准确表达 QG、settlement、summary、convergence 状态 |
| 测试 | 聚焦测试 + 全量 pytest 按防卡协议通过 |

## 完成后交付

- [ ] 生成 `tasks/113-ch101-convergence-settlement-blocker-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] 更新 `README.md`
- [ ] 更新 `docs/INDEX.md`
- [ ] 若 Ch101 恢复，通过状态文档声明 Task 114 可重新启动
- [ ] Git commit 包含代码修复、测试、DONE 文档和状态更新

## 后续任务

Task 114 继续承担原 Task 113 的 Ch101-Ch150 流式验证 + DG-2。Task 114 只能在本 Task 完成并恢复 Ch101 accepted/settlement/summary 基线后启动。
