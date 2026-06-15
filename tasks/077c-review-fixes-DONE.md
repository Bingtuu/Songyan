# Task 077c: 076/077a/077b Review 遗留修复 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **关联 Task**: 076-DONE, 077a-DONE, 077b-DONE
> **测试覆盖**: 54 个单元测试全部通过

---

## 修复清单

### 1. 077b — 补充 `initial_state` 缺失字段（P1）✅

**文件**: `src/songyan/workflows/phase1_graph.py`

- `run_chapter_pipeline()` 的 `initial_state` 字典中补充 `"_budget_was_enforced": False`
- 确保 LangGraph `Phase1State` 初始化完整，避免下游读取时 KeyError

```python
"_was_rewritten": False,
"_rewrite_reason": None,
"_budget_was_enforced": False,  # 新增
```

### 2. 076 — 修正 `_was_truncated` 语义 + 补充独立字段（P1+P2）✅

**文件**: `src/songyan/agents/writer.py`

**变更 a：`_enforce_word_count()` 返回语义修正**
- 单 scene 保护：`True` → `False`（保护放行 ≠ 物理截断）
- `no_scene_headers_found`：`True` → `False`

**变更 b：`write_chapter()` 区分物理截断与保护放行**
```python
_is_disallowed = _trunc_reason == "_disallowed_by_scene_structure"
_is_no_headers = _trunc_reason == "no_scene_headers_found"
_actually_truncated = _was_truncated and not _is_disallowed and not _is_no_headers
```

- `_actually_truncated` 为真时才更新 content/scenes/word_count 和 logger
- `_word_count_truncated` 只记录物理截断
- `_word_count_original` 只在物理截断时记录原始值

**变更 c：新增独立 metadata 字段**
```python
"_disallowed_by_scene_structure": _is_disallowed,
```

### 3. 077b — 删除测试冗余调用（P2）✅

**文件**: `tests/test_077b_budget_hard_enforcement.py`

- 删除 `test_triggers_when_over_threshold` 中重复的 `prune()` 调用

### 4. 076 — 修复 fallback 边界逻辑（P3）✅

**文件**: `src/songyan/agents/writer.py`

- 当处理最后一个 scene（`_i = len(_headers) - 1`）且截断后字数 < `_lower` 时
- 原逻辑：`break` → 进入激进 fallback（可能保留过少内容）
- 修复后：`continue` → 继续循环到前一个 scene，尝试更保守的截断点
- 避免"去掉最后一个 scene 后字数太低，fallback 到只保留第一个 scene"的过度截断

### 5. 076 — 测试同步更新 ✅

**文件**: `tests/test_076_word_count_truncation.py`

- `test_single_scene_marks_disallowed`: `result[3] is True` → `result[3] is False`
- `test_no_scene_headers`: `result[3] is True` → `result[3] is False`

---

## 未完成的项（P3 可选，本次未执行）

| # | 项 | 原因 |
|---|-----|------|
| 077a-6 | `assemble_context_package()` 端到端入站过滤测试 | 过滤逻辑内联在函数中，需要大量 mock（Character/GenreProfile/ProjectSetting 等）。底层函数（`_is_setting_critical`、`_build_soft_references`、常量 `MAX_SETTING_INPUT`）已单独测试覆盖。端到端测试收益/成本比低，推迟到 V3.2 上下文架构改造时统一补充。 |

---

## 验证结果

| 验证项 | 结果 |
|--------|:----:|
| `tests/test_076_word_count_truncation.py`（12 个） | ✅ 12 passed |
| `tests/test_077a_setting_library.py`（27 个） | ✅ 27 passed |
| `tests/test_077b_budget_hard_enforcement.py`（15 个） | ✅ 15 passed |
| 全量回归（排除预存在 embedding benchmark） | ✅ 173 passed，0 regression |

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/songyan/workflows/phase1_graph.py` | 修改 | `initial_state` 补充 `_budget_was_enforced: False` |
| `src/songyan/agents/writer.py` | 修改 | `_enforce_word_count` 语义修正 + fallback 边界 + metadata 字段补充 |
| `tests/test_076_word_count_truncation.py` | 修改 | 同步更新断言（单 scene/no_headers 返回 False） |
| `tests/test_077b_budget_hard_enforcement.py` | 修改 | 删除冗余 `prune()` 调用 |

---

## 不违反的 AGENTS.md 规则确认

- ✅ 规则 11：Writer 只做初稿——截断/保护不是修订
- ✅ 规则 24：自动修订最多 2 轮——无关
- ✅ 规则 58：类型标注——全部保留
- ✅ 规则 64：单文件 < 400 行——只做微量添加
- ✅ 规则 66：异步优先——不修改 async/await 边界

---

## 已知限制

- 077a 缺少 `assemble_context_package()` 端到端入站过滤集成测试（P3 可选项，不影响功能正确性）
- `_estimate_package()` 的 Token 估算与真实 tokenizer 有 10-20% 偏差（077b 原有已知限制）
- `last_mentioned_chapter` 是估计值而非精确值（077a 原有已知限制）
