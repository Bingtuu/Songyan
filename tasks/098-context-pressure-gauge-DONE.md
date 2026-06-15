# Task 098: 上下文压力计 + Accept 守卫 — 交接报告

> **状态**: ✅ 完成
> **完成日期**: 2026-06-12
> **负责人**: Agent

---

## 1. 任务目标

在 Task 096 数据基础上（达标率 70.2%，超标率 29.8%，最大超标 1.757x），实施三项系统级优化：

1. **上下文压力计（四信号系统）**: `narrative_fullness`、`character_focus`、`foreshadowing_urgency`、`focal_distance`
2. **Craft Card 措辞回调**: 1.0.8 → 1.0.9，明确"1.3x 可以，1.4x 不行"的数值边界
3. **Accept 路径字数守卫**: 超标 > 1.40x 且修订 < 2 轮 → 自动触发 rewrite
4. **删除 min_scenes=2 截断保护**: 改为纯字数保护

---

## 2. 改动清单

### 2.1 四信号系统

| 文件 | 改动 |
|------|------|
| `src/songyan/agents/creative_director/_brief_builder.py` | 解析 LLM 返回的四信号字段并传入 `CreativeBrief` |
| `src/songyan/agents/context_manager/__init__.py` | `BudgetPruner.prune()` 集成动态上限 + `_rank_foreshadowings()` + `_apply_focal_distance()` 增强 |
| `src/songyan/agents/context_manager/_assemblers.py` | `_build_character_snapshots()` 支持 `character_focus` 的 `full/compressed/skip` 粒度 |
| `src/songyan/workflows/_helpers.py` | `assemble_context_package` 已透传四信号参数（上一轮完成） |

#### 动态上限公式

```python
fullness_factor = 1.0 - (narrative_fullness * 0.5)
dynamic_max_soft = max(1, round(MAX_SOFT_REFS * fullness_factor))
dynamic_max_fore = max(1, round(MAX_FORESHADOWING * fullness_factor))
dynamic_max_char = max(1, round(MAX_CHARACTER_STATES * fullness_factor))
```

#### 焦段逻辑

| 焦段 | soft_references | character_states | permanent_scenes | open_threads | foreshadowing |
|------|----------------|------------------|------------------|--------------|---------------|
| `close` | ≤3 | 默认 | ≤1 | ≤1 | 默认 |
| `mid` | 默认 | 默认 | 默认 | 默认 | 默认 |
| `wide` | 默认 | ≤2（主角+1重要角色） | 默认 | 默认 | 默认 |
| `disruption` | 截断一半 | 默认 | 默认 | 默认 | 只保留首尾各1条 |

### 2.2 Craft Card 1.0.9

**文件**: `prompts/cards/writer/1.0.9.yaml`

输出要求第 3 条修改为：

```yaml
- 如果场景需要更多篇幅来充分展开，可以接受适度的超标（1.3x 以内）
- 但 1.4x 以上的超标会被视为结构缺陷——意味着你在这一章中放了太多内容
- 如果你发现自己正在接近 1.4x，考虑将部分内容移到下一章
- 不足 0.8x 同样不可接受——字数不足意味着情节展开不够
```

### 2.3 Accept 路径字数守卫

**文件**: `src/songyan/workflows/_nodes.py`

- 守卫从 `settlement_extractor_node` 移至 `human_gate_node` 的 `accept` 分支
- 触发条件：`word_count > target * 1.40` AND `revision_round < 2` AND `not _was_rewritten`
- 触发结果：`human_decision = "word_count_guard"`，路由到 `rewrite`

**文件**: `src/songyan/workflows/phase1_graph.py`

- `human_confirm_router` 新增 `word_count_guard` → `"word_count_guard"` 分支
- `add_conditional_edges("human_confirm", ...)` 新增 `"word_count_guard": "rewrite"`

### 2.4 min_scenes 移除

`utils/truncation.py` 中 `min_scenes=2` 保护已在上一轮移除，当前为纯字数保护（`len(_ns) >= 1`）。

### 2.5 Bug 修复

**文件**: `src/songyan/workflows/phase1_graph.py`

- 修复 `revision_router` 中 `project_id`、`chapter_number`、`mode_id` 未定义变量错误（使用 `state.get()` 替代）。

---

## 3. 测试

### 3.1 新增测试

| 测试文件 | 测试类 | 用例数 | 覆盖内容 |
|----------|--------|--------|----------|
| `tests/test_context_manager.py` | `TestRankForeshadowings` | 4 | 伏笔紧迫性排序（due_list、overdue、due_chapter、无due） |
| `tests/test_context_manager.py` | `TestBudgetPrunerFourSignals` | 4 | narrative_fullness 动态上限、close/wide/disruption 焦段 |
| `tests/test_context_manager.py` | `TestCharacterFocusSnapshots` | 4 | full/compressed/skip 粒度 + 无 focus 回退 |
| `tests/test_phase1_graph.py` | `TestHumanGateNodeWordCountGuard` | 4 | 触发条件、不触发条件（<1.40x、已rewrite、≥2轮） |
| `tests/test_phase1_graph.py` | `TestHumanConfirmRouter` | +1 | word_count_guard 路由 |

### 3.2 测试结果

```
pytest tests/test_context_manager.py tests/test_phase1_graph.py
         tests/test_076_word_count_truncation.py tests/test_creative_director.py

127 passed in 17.63s
```

### 3.3 代码检查

- 修改文件经 ruff 检查，无新增错误（31 个 pre-existing 错误未引入）。

---

## 4. 验证方式

```bash
# 运行核心测试
pytest tests/test_context_manager.py tests/test_phase1_graph.py -v

# 运行全部测试（排除 eval_runner 的缩进错误）
pytest tests/ --ignore=tests/test_eval_runner.py -q

# ruff 检查修改文件
ruff check src/songyan/agents/context_manager/__init__.py \
          src/songyan/agents/context_manager/_assemblers.py \
          src/songyan/agents/creative_director/_brief_builder.py \
          src/songyan/workflows/_nodes.py \
          src/songyan/workflows/phase1_graph.py
```

---

## 5. 已知限制

1. **四信号目前由 CreativeDirector LLM 输出解析获得**，如果 LLM 不输出这些字段，系统回退到默认值（fullness=0.0, focal_distance="mid"），行为与之前一致。
2. **Accept 守卫仅在人工 accept 时触发**，`--auto-confirm` 模式下同样生效（因为 `human_gate_node` 会模拟 accept 决策）。
3. ** `_was_rewritten` 标志防止已 rewrite 的章节无限循环**，但如果 rewrite 后仍 >1.40x 且 <2 轮，守卫不会再次触发（符合设计意图）。
4. **焦段 `disruption` 的随机性目前为确定性截断**（取前半部分），未使用真随机，保证可复现性。

---

## 6. 交接检查清单

- [x] 代码实现完成
- [x] 测试通过（pytest -v）
- [x] 不违反 AGENTS.md 任何规则
- [x] 更新了 docs/STATUS.md
- [x] 生成了 tasks/098-context-pressure-gauge-DONE.md 交接文件
- [x] ruff 检查无新增错误

---

## 7. 下一步建议

**Task 099: Ch71-Ch100 扩展验证**

在 Task 098 优化基础上，运行 Ch2-Ch100（或至少 Ch51-Ch100）全自动验证，检验四信号系统 + Accept 守卫对达标率的实际提升效果。目标：达标率 > 78%。
