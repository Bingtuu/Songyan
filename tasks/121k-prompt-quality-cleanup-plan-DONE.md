# Task 121k: Prompt Quality Cleanup Plan — DONE

> **状态**: DONE  
> **完成日期**: 2026-06-26  
> **执行承接**: Task 121r Prompt Quality Cleanup Execution

---

## 目标摘要

承接 Task 121g（`run-0fd1456e`）质量复盘暴露的正文机械化、HTML 元标记泄漏、短段落碎片化及说明文堆叠等问题，制定 V5.1 Prompt / 正文质量清理方案，明确 Writer、CreativeDirector、RuleAuditor 三处的修复方向、验证窗口与验收标准。

---

## 关键改动 / 交付物

- **规划交付**: `tasks/121k-prompt-quality-cleanup-plan.md` 已定稿，作为 Task 121r 的执行输入。
- **Writer Prompt 升级**（Task 121r 落地）:
  - `prompts/cards/writer/1.1.0.yaml` 设为默认版本。
  - 明确禁止正文输出 markdown 标题、`<!-- -->` 等 HTML 注释及元数据标签。
  - 场景切换改用空行分隔的自然叙事段落，不再使用 `Scene N` 机械标题。
  - 增加段落节奏与连续短段落控制约束。
- **CreativeDirector Prompt 升级**（Task 121r 落地）:
  - `prompts/cards/creative_director/1.0.5.yaml` 设为默认版本。
  - tension / forbidden patterns 改写为可执行约束。
  - 高概念信息释放要求“行动承载”，避免章节目标退化为设定说明清单。
- **RuleAuditor 观测增强**（Task 121r 落地）:
  - `src/songyan/agents/rule_auditor.py` 新增元标记泄漏检测、markdown 场景标题检测、短段落比例观测指标。
  - 新增检测为观测指标，未直接扩大阻断范围。

---

## 验证证据

- Task 121r 全量测试通过：`pytest 1764 passed`，`ruff check src/ tests/` 通过。
- 后续 Task 121q full single-run `run-a2bed648` 在 Prompt 清理后完成 Ch1-Ch150 全部 150/150 成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，无间隙。

---

## 遗留 / 后续

无。Prompt 质量清理专项已通过 Task 121r 完成并验证，后续质量迭代纳入常规 V5.1 调优流程。
