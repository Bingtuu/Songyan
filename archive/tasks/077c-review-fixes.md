# Task 077c: 076/077a/077b Review 遗留修复

> **Phase**: V3.1 100章架构改造 — Phase A 止血收尾
> **优先级**: P1
> **依赖**: 076-DONE, 077a-DONE, 077b-DONE
> **预计工作量**: 小（0.5-1 小时）
> **来源**: Task 076/077a/077b Code Review 中发现的问题

---

## Goal

修复 Code Review 中发现的 076/077a/077b 规格偏差、语义误导和边界漏洞，确保三个 Task 的交付物与原始规格 100% 吻合，无已知遗留问题后进入 078。

---

## Context

Task 076（Writer 强制截断）、077a（分层 Setting 库）、077b（BudgetPruner 硬断言）的核心修复逻辑均已实现并通过测试，但在 Code Review 中发现以下问题：

| 来源 Task | 严重度 | 问题描述 |
|-----------|--------|---------|
| 076 | 🔴 P1 | `generation_metadata` 缺少独立的 `_disallowed_by_scene_structure` boolean 字段（规格明确要求） |
| 076 | 🟡 P2 | 单 scene 保护时返回 `_was_truncated=True`，内容未截断却标记为"已截断"，语义误导 |
| 076 | 🟡 P3 | "截断后字数 < target×0.5 保留末 scene" 在最后一个 scene 边界存在 fallback 漏洞 |
| 077b | 🔴 P1 | `Phase1State` 的 `initial_state` 缺少 `_budget_was_enforced: False` 初始化 |
| 077b | 🟡 P2 | 测试 `test_triggers_when_over_threshold` 中存在冗余的第二次 `prune()` 调用 |
| 077a | 🟢 P3 | 缺少 `assemble_context_package()` 端到端入站过滤测试 |

本 Task 只做修复，不引入新功能。

---

## In Scope

### 1. 076 — 补充 `_disallowed_by_scene_structure` 独立字段（P1）

**文件**: `src/songyan/agents/writer.py`

- `generation_metadata` 中新增 `"_disallowed_by_scene_structure": <bool>` 字段
- 值为 `_trunc_reason == "_disallowed_by_scene_structure"`
- 该字段独立于 `_truncation_reason` 字符串，便于下游直接判断

### 2. 077b — 补充 `initial_state` 缺失字段（P1）

**文件**: `src/songyan/workflows/phase1_graph.py`

- `run_chapter_pipeline()` 的 `initial_state` 字典中补充 `"_budget_was_enforced": False`
- 确保 LangGraph state 初始化完整，避免下游 `.get()` 以外的读取方式出错

### 3. 076 — 修正单 scene 保护的 `_was_truncated` 语义（P2）

**文件**: `src/songyan/agents/writer.py`

- `_enforce_word_count()` 单 scene 保护分支返回 `False` 而非 `True`
- 语义：`_was_truncated` 仅表示"内容被物理截断"，保护放行 ≠ 截断
- 同步调整 `write_chapter()` 中的 logger 和 metadata 逻辑，确保保护场景不记录 `word_count_truncated`

### 4. 077b — 删除测试冗余调用（P2）

**文件**: `tests/test_077b_budget_hard_enforcement.py`

- 删除 `test_triggers_when_over_threshold` 中重复的 `prune()` 调用

### 5. 076 — 修复截断后 < lower 的 fallback 边界（P3，可选）

**文件**: `src/songyan/agents/writer.py`

- 当最后一个 scene 被截断后字数 < `_lower` 时，当前逻辑直接 `break` 进入 fallback，可能产生低于下限的结果
- 修正为：若去掉最后一个 scene 后字数低于下限，则**保留该 scene**（即回退到不截断该 scene），而非继续向前截断更多 scenes

### 6. 077a — 补充端到端入站过滤测试（P3，可选）

**文件**: `tests/test_077a_setting_library.py`

- 新增测试用例验证 `assemble_context_package()` 中的去重 + Top-N 过滤逻辑
- 覆盖场景：
  - 84 条 setting → 去重后 60 条 → critical 5 条 + non-critical 55 条 → 最终 15 条（5+10）
  - critical 被错误计入上限的防御
  - 同 setting_key 去重保留最新版本

---

## Out of Scope

- 不修改任何 Prompt
- 不修改 DB schema
- 不修改 076/077a/077b 的核心算法逻辑（只做修复，不做重构）
- 不新增功能

---

## 修复计划

### 步骤 1: 077b initial_state 补充（5 分钟）

```python
# src/songyan/workflows/phase1_graph.py:279-280
    "_was_rewritten": False,
    "_rewrite_reason": None,
    "_budget_was_enforced": False,  # 新增
```

### 步骤 2: 076 语义修正 + 字段补充（15 分钟）

修改 `_enforce_word_count()` 返回语义：
- 单 scene 保护：返回 `(content, scenes, wc, False, "_disallowed_by_scene_structure")`
- `no_scene_headers_found`：同样返回 `False`（未实际截断）

修改 `write_chapter()` 的 metadata 构建：
```python
"_word_count_truncated": _was_truncated and _trunc_reason not in ("_disallowed_by_scene_structure", "no_scene_headers_found"),
"_disallowed_by_scene_structure": _trunc_reason == "_disallowed_by_scene_structure",
```

修改 logger：只在实际截断时输出 `writer.word_count_truncated`。

### 步骤 3: 077b 测试清理（2 分钟）

删除 `tests/test_077b_budget_hard_enforcement.py` 中的冗余行。

### 步骤 4: 076 fallback 边界修复（10 分钟，可选）

调整 `_enforce_word_count()` 循环末尾逻辑，确保低于 `_lower` 时正确回退。

### 步骤 5: 077a 端到端测试补充（15 分钟，可选）

新增 1-2 个集成测试用例。

### 步骤 6: 回归测试

```bash
pytest tests/test_076_word_count_truncation.py tests/test_077a_setting_library.py tests/test_077b_budget_hard_enforcement.py -v
pytest tests/ -x -q  # 全量回归
```

---

## 测试要求

- [ ] 076 测试：`test_single_scene_marks_disallowed` 断言 `_word_count_truncated=False` 且 `_disallowed_by_scene_structure=True`
- [ ] 076 测试：新增 `test_generation_metadata_has_disallowed_flag`
- [ ] 077b 测试：`test_triggers_when_over_threshold` 无冗余调用
- [ ] 077b 测试：新增 `test_initial_state_has_budget_enforced_field`（或检查 `Phase1State` 完整 key 集合）
- [ ] 077a 测试（可选）：新增端到端过滤测试
- [ ] 全量回归测试通过，无新增失败

---

## 验收标准

- [ ] 076 `_disallowed_by_scene_structure` 作为独立 boolean 存在于 `generation_metadata`
- [ ] 076 单 scene 保护时 `_word_count_truncated=False`，内容未被物理截断
- [ ] 077b `initial_state` 完整包含所有 `Phase1State` 定义的 key
- [ ] 077b 测试无冗余调用
- [ ] 076 fallback 边界不产生低于 `target×0.5` 的结果（可选）
- [ ] 077a 端到端过滤有测试覆盖（可选）
- [ ] 全量回归通过
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 077c-DONE.md 交接报告
- [ ] 更新 STATUS.md（077c 行标记为完成）

---

## 不违反的 AGENTS.md 规则确认

- 规则 11：Writer 只做初稿——截断/保护不是修订
- 规则 24：自动修订最多 2 轮——无关
- 规则 53-57：数据访问边界——仅修改已有文件的已有路径
- 规则 58：类型标注——Python 3.11+ 语法
- 规则 64：单文件 < 400 行——只做微量添加
- 规则 66：异步优先——不修改 async/await 边界
- 规则 68：Layer 0 不修完不进下一层——077c 是收尾修复，不阻塞 078
