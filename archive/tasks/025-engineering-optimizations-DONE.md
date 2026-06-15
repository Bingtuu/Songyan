# Task 025: 工程优化 — DONE

**目标**: 修复 3 个工程层面的体验问题（patch 匹配率 / 成本估算 / 上下文膨胀）。

**完成日期**: 2026-05-30

---

## 1. Revision Handler Patch 匹配率提升

### 问题
真实 LLM 验证中，`fuzzy_match ratio=0.905` 的 patch 仍报 `patch_not_found`。

### 根因
`_apply_patches` 的两阶段匹配逻辑不一致：
1. 第一阶段 `_span_in_original` 使用 fuzzy match（threshold 0.85）在原始 `content` 中定位
2. 第二阶段替换循环中使用 `result.rfind(patch.original_text)` 精确匹配在 `result` 中重新定位

当 `patch.original_text` 与正文有微小差异时，第一阶段通过但第二阶段失败。

### 修复
- 提取 `_find_text_span(text, target, issue_id, fuzzy_threshold)` 通用函数
- 替换循环中也使用 `_find_text_span(result, patch.original_text)` 重新定位
- 新增日志 `patch_not_found_in_result` 区分两阶段的失败

### 验证
- `test_fuzzy_match_90_percent`：90% 相似度文本正确找到
- `test_fuzzy_match_70_percent_should_fail`：70% 相似度正确拒绝
- `test_apply_patch_with_fuzzy_match`：端到端 patch 应用成功

---

## 2. LLM 调用成本估算修正

### 问题
脚本 hardcode 预估 "~¥0.5-3"，实际成本仅 "~¥0.11-0.15"，误差达 3-20 倍。

### 根因
旧估算使用 `1 token ≈ 1.5 中文字符` 的粗略假设，未使用精确 tokenizer。

### 修复
- 新增 `songyan/utils/cost_estimator.py`：
  - `count_tokens(text, model)`：使用 tiktoken (`cl100k_base`) 精确计数
  - `estimate_cost(prompt_text, response_text, model)`：基于 DeepSeek 定价计算
  - `estimate_cost_from_calls(calls)`：从调用记录批量估算
  - `format_cost_estimate(cost)`：格式化输出
- DeepSeek 定价：输入 ¥1/M tokens，输出 ¥2/M tokens
- 更新 `scripts/run_real_llm_scifi.py` 和 `scripts/run_real_llm_multi_chapter.py`

### 验证
- `test_chinese_text`：中文字符 token 计数 > 0
- `test_deepseek_chat_cost`：成本计算合理（< ¥0.1 / 次典型调用）

---

## 3. Multi-turn 上下文膨胀控制

### 问题
Task 文档指出 "3 轮 revision 后 LLMAuditor prompt 字符数从 8393→8598→9448 持续增长"。

### 现状
当前版本（v1.0.3 + 回滚保护）实测 prompt 长度在多轮 revision 中**无增长**甚至下降（6658→6633，-0.4%），因为 revision 反弹保护阻止了内容膨胀。

### 预防性修复
- `context_manager.py` 的 `_build_recent_plot` 新增 `MAX_SUMMARY_LENGTH = 200`
- 超过 200 字符的 `summary` 自动截断为 `...` 后缀
- 防止未来 Settlement 积累大量长 summary 后 context_info 膨胀

### 验证
- `test_summary_truncated_when_too_long`：300 字符 summary → 203 字符
- `test_summary_unchanged_when_short`：短 summary 不受影响
- `test_key_events_preserved`：截断不丢失 key_events

---

## 4. 测试与回归

```
pytest tests/ -x
# 719 passed in ~33s
```

新增测试: 21 个
- `tests/test_revision_handler_patch.py`：8 个
- `tests/test_cost_estimator.py`：8 个
- `tests/test_context_compression.py`：5 个

修复现有测试: 1 个（`test_settlement_extractor.py` 适配 `list_by_project` 白名单检查）

---

## 5. 文件变更

| 文件 | 变更 |
|------|------|
| `src/songyan/agents/revision_handler.py` | 提取 `_find_text_span`，替换循环使用 fuzzy re-locate |
| `src/songyan/utils/cost_estimator.py` | 新增：tiktoken 计数 + DeepSeek 定价 |
| `src/songyan/agents/context_manager.py` | `_build_recent_plot` 截断长 summary |
| `scripts/run_real_llm_scifi.py` | 使用 `cost_estimator` |
| `scripts/run_real_llm_multi_chapter.py` | 使用 `cost_estimator` |
| `tests/test_revision_handler_patch.py` | 新增 |
| `tests/test_cost_estimator.py` | 新增 |
| `tests/test_context_compression.py` | 新增 |
| `tests/test_settlement_extractor.py` | 修复 mock 适配 |
