# Task 111c DONE: Context 与 Prompt 一致性修复

> **完成日期**: 2026-06-19
> **状态**: ✅ 已完成
> **提交范围**: ContextEmergency / hard_constraints / HumanInstruction / Craft Card / 字数策略

---

## 完成内容

1. **统一 ContextEmergency 语义**
   - `budget_used > 1.0` 后的 `ContextEmergency` 改为最终硬裁。
   - emergency 后清空 soft references、foreshadowing、open threads、permanent scenes、arc/volume、human marks、dialogue style cards。
   - 只保留硬约束、规则、章节目标、creative brief 与最高优先级角色状态。
   - 更新测试确认可裁分区被清空，reducible 场景下 `budget_used <= 1.0`。

2. **修复 hard_constraints 裁剪语义**
   - `_build_hard_constraints()` 不再把 `human_marks` 转成 `HardConstraint(type="human_mark")`。
   - `_prune_hard_constraints()` 变为 no-op，hard constraints 一旦进入上下文即不可裁剪。
   - 人类标记继续通过 `ContextPackage.human_marks` 独立分区进入 Writer prompt，允许在 emergency 中被软裁。

3. **统一 HumanInstruction 字段契约**
   - 新增 `normalize_human_instruction()`，兼容旧字段 `type` 与标准字段 `action`。
   - Writer 渲染前统一规范化 human instructions。
   - Writer 1.0.9 prompt 兼容 `inst.action or inst.type`，避免渲染 `- [] ...`。

4. **修复 Craft Card 权重渲染顺序**
   - `PromptLoader.render_card()` 按 `get_active_sections()` 返回的权重排序渲染内容。
   - 新增测试确认高权重 section 在 prompt 中前置，而不只是 `active_sections` ID 有序。

5. **校准字数策略口径**
   - 新增 `word_count_bounds()`，集中定义 Writer/RuleAuditor 共用的 chapter_type-aware 字数边界。
   - Writer 截断逻辑改用统一边界。
   - RuleAuditor 支持 `chapter_type` 参数，并在 workflow 节点中从 `ChapterGoal` 透传。
   - 新增测试确认 transition/conflict 的动态上限差异。

---

## 修改文件

- `prompts/cards/writer/1.0.9.yaml`
- `src/songyan/agents/context_manager/__init__.py`
- `src/songyan/agents/context_manager/_assemblers.py`
- `src/songyan/agents/rule_auditor.py`
- `src/songyan/agents/writer.py`
- `src/songyan/models/human_instruction.py`
- `src/songyan/prompts/loader.py`
- `src/songyan/utils/truncation.py`
- `src/songyan/workflows/_nodes.py`
- `tests/test_104_budget_hard_ceiling.py`
- `tests/test_context_manager.py`
- `tests/test_prompt_loader.py`
- `tests/test_rule_auditor.py`
- `tests/test_writer.py`
- `docs/STATUS.md`

---

## 验证结果

```bash
pytest tests/ -v
```

结果：`1635 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
pytest tests/ -q
```

结果：`1635 passed, 4 skipped, 1 xfailed, 4 xpassed, 10 warnings`

```bash
ruff check src/songyan/agents/context_manager/__init__.py src/songyan/agents/context_manager/_assemblers.py src/songyan/agents/rule_auditor.py src/songyan/agents/writer.py src/songyan/models/human_instruction.py src/songyan/prompts/loader.py src/songyan/utils/truncation.py src/songyan/workflows/_nodes.py tests/test_104_budget_hard_ceiling.py tests/test_prompt_loader.py tests/test_rule_auditor.py
```

结果：`All checks passed!`

```bash
ruff check src/ tests/ --statistics
```

结果：仍有历史 lint `130 errors`，主要为未触及测试文件的 E501/F401/E402/F841/F821 等；本 Task 未扩大到历史 lint 清理。

---

## 已知限制

- 如果硬约束、规则、章节目标、creative brief 本身已经超过预算，ContextEmergency 会记录 irreducible warning；此时不能通过裁剪硬约束强行满足预算，否则会违反 P0。
- `tests/test_context_manager.py` 与 `tests/test_writer.py` 仍包含历史 E501 行，本 Task 只避免新增 lint。
- Task 111c 不包含 Ch101-Ch150 长跑验证，该验证进入 Task 112。

---

## 下一步

进入 **Task 112: Ch101-Ch150 流式验证 + 决策门 DG-2**。
