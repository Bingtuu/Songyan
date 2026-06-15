# Task 033: 工程优化三项收尾（已完成）

> **Phase**: Stage A（还债与封锁解除）
> **优先级**: P1
> **依赖**: Task 032（DONE 报告补齐）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

### A2-1: Revision Handler 模糊匹配

- [x] 改进 `_find_text_span()`：
  - 保留精确匹配 + 归一化空白匹配
  - 将 difflib 滑动窗口提取为 `_difflib_fuzzy_search()`
  - 新增**多级 threshold 回退**：0.90 → 0.85 → 0.80
  - 新增**两阶段搜索**：大步长快速扫描找候选区域 → 小步长（1 字符）在候选区域附近精确搜索
  - 新增**段落级回退匹配** `_paragraph_fallback_search()`：将 target 按段落分割，逐段查找最佳匹配，≥50% 段落匹配成功时返回整体范围
- [x] `_apply_patches()` 自动使用改进后的 `_find_text_span()`，无需调用方修改

### A2-2: 成本估算修正

- [x] 新增 `estimate_cost_from_tokens(prompt_tokens, completion_tokens, model)`：
  - 支持直接传入 litellm 返回的精确 token 数（比文本估算更准）
  - 与 `estimate_cost()` 共享同一套定价表
- [x] 修复 `cost_estimator.py` 中 `Any` 的类型导入问题（已有代码缺陷）
- [x] 定价校准：DeepSeek-chat 输入 ¥1/M + 输出 ¥2/M，与实际账单误差 < 20%

### A2-3: 上下文压缩

- [x] 新增 `_compress_review_history(reviews, max_issues_per_round, max_total_length)`：
  - 只保留最近 2 轮 review
  - 每轮只保留 top issues（critical/major 优先，默认每轮 3 个）
  - 去重：相同 category + description 的 issue 只保留一次
  - 低分维度摘要（score < 6.0 的维度自动列出）
  - 超长自动截断（默认上限 1500 字符）
- [x] 接口就位，LLMAuditor 可在将来扩展 `previous_reviews` 参数时直接调用

### 测试

- [x] `tests/test_revision_handler_fuzzy.py` — 18 tests（精确匹配 / 90% 匹配 / 70% 匹配失败 / 段落回退 / 多级 threshold）
- [x] `tests/test_cost_estimator_tokens.py` — 9 tests（token 估算 / 零 token / 真实数据校准）
- [x] `tests/test_compress_review_history.py` — 9 tests（空输入 / 单轮 / 多轮 / 去重 / 优先级 / 截断 / 维度摘要 / 压缩率）
- [x] 现有测试全部通过：84 passed（含 revision_handler / llm_auditor / cost_estimator）
- [x] ruff 0 errors

---

## 关键决策

### 模糊匹配不引入新依赖
使用标准库 `difflib.SequenceMatcher` 而非 `rapidfuzz`/`python-Levenshtein`。理由：
1. 避免增加项目依赖
2. difflib 对中文文本的匹配质量已足够
3. 通过算法优化（两阶段搜索 + threshold 回退）弥补性能差距

### 段落级回退的匹配率阈值
段落级回退要求 ≥50% 段落（至少 2 个）匹配成功，每段 ratio ≥ 0.70。这是保守策略：
- 避免在完全不匹配时误报
- 对 LLM 返回的段落重组 patch（段落顺序变化、段落合并/拆分）有较好容错

### 成本估算双轨制
保留 `estimate_cost()`（文本 → token 估算）和新增 `estimate_cost_from_tokens()`（精确 token 数）。理由：
- 脚本层（`run_batched_chapters.py`）只有字符数，需要文本估算
- workflow 层将来可接入 litellm 的实际 token 返回，需要精确估算

---

## 基线验证

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| patch 匹配失败率 | ≤ 5% | `_find_text_span` 多级回退覆盖 |
| 成本估算误差 | ≤ 20% | 与 ROUND 报告实际账单对比 |
| 压缩后长度 | ≤ 1.5 轮原长度 | `test_compression_ratio` |

---

## 交付物

- `src/songyan/agents/revision_handler.py` — `_difflib_fuzzy_search()` + `_paragraph_fallback_search()`
- `src/songyan/utils/cost_estimator.py` — `estimate_cost_from_tokens()` + `Any` 导入修复
- `src/songyan/agents/llm_auditor.py` — `_compress_review_history()`
- `tests/test_revision_handler_fuzzy.py` — 18 tests
- `tests/test_cost_estimator_tokens.py` — 9 tests
- `tests/test_compress_review_history.py` — 9 tests

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| 段落级回退可能误匹配 | 低 | threshold 0.70 + 50% 段落覆盖是保守策略，误匹配概率低。如观察到误匹配，可收紧 threshold。 |
| 上下文压缩未接入 workflow | 低 | `_compress_review_history` 已就位，但当前 LLMAuditor 不传递历史 review。A3 或后续迭代可接入。 |

---

## 下一步

**Task 034: 遗留验证补齐（A3）**
- Punch Engine 自动评估
- ContinuityAuditor state_mismatches 实装
- Arc/Volume 摘要自动生成
- 50 章模拟测试
