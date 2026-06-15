# Task 022: 多题材种子真实 LLM 评测 — DONE

> **完成日期**: 2026-05-30
> **测试状态**: 681 passed, 0 failed

---

## 已完成项

- [x] 玄幻种子（xuanhuan_webnovel）真实 LLM 端到端评测：pipeline_success=1, overall_score=8.1~8.48
- [x] 都市种子（urban_hybrid）真实 LLM 端到端评测：pipeline_success=1, overall_score=8.31
- [x] 三题材横向对比报告写入 `evals/output/MULTI_GENRE_REPORT.md`
- [x] MetricsCollector `_setting_key_accuracy` 修复：分母排除种子阶段无 source_quote 的 setting
- [x] `evals/runner.py` `_build_settlement_output` 输出完整 setting 字段
- [x] `evals/__main__.py` 增加 `init_schema()` 避免首次运行报 `no such table`
- [x] SettlementExtractor `CharacterUpdate` 类型容错：`old_value`/`new_value` 强制 `str()`
- [x] `RevisionOutput.new_version_id` 增加默认值 `''`
- [x] Writer `call_llm` 传入 `max_tokens=6000`
- [x] 更新 `docs/STATUS.md` 评测历史表
- [x] 更新 `README.md` 当前阶段描述

---

## 评测结果摘要

| 题材 | is_pass | overall_score | ai_tell | fatigue | setting_key* |
|------|---------|---------------|---------|---------|-------------|
| 科幻 | ✅ | 8.36 | 1 | 0 | 1.0 |
| 玄幻 | ❌ | 8.1~8.48 | 3 | 2 | 0.23 (旧逻辑) |
| 都市 | ❌ | 8.31 | 1 | 0 | 0.125 (旧逻辑) |

\* 旧逻辑下 setting_key_accuracy 分母包含种子阶段无 source_quote 的 setting，导致被系统性稀释。metrics 计算逻辑已修正。

---

## 未达标项与后续 Task

| 问题 | 根因 | 后续 Task |
|------|------|----------|
| 玄幻 ai_tell_count=3 | 玄幻设定解释易触发 AI 腔 | Task 024: Writer 反 AI 腔规则调优 |
| 玄幻 fatigue_word_count=2 | 玄幻特有词汇被通用列表命中 | Task 024: Genre Profile 疲劳词豁免 |
| Settlement source_quote 精度 | LLM 编造不存在的原文引用 | Task 024: SettlementExtractor prompt 强化 |

---

## 遗留问题

- 需复测玄幻/都市以验证 metrics 修复后 is_pass 恢复
- scenes_count=1 问题仍存在（Writer 未生成多场景）
- dialogue_subtext 评分仍有提升空间

---

*交接人可继续进入 Task 023（多章编排层）或 Task 024（Prompt 细节打磨）。*
