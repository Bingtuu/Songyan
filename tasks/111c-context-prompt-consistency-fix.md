# Task 111c: Context 与 Prompt 一致性修复

> **Phase**: V5.0 Phase 4 前置修复 — Context Diet / Prompt 契约校准
> **优先级**: P1
> **依赖**: Task 111b 完成
> **预计工作量**: 1 天

---

## Goal

修复 Context Diet 2.0 与 Prompt 工艺卡中的一致性偏差，确保预算硬天花板、硬约束、human instruction、Craft Card 权重和字数策略在 Writer、Auditor、QualityGate 之间口径一致。

## Context

Task 110e 证明 Auditor 阈值校准有效，但整体 review 发现仍有若干 P1 风险会影响长跑稳定性：

1. `ContextEmergency` Level 1/2 仍保留 soft references、foreshadowing、arc/volume、多角色等软信息，与 “budget_used > 1.0 时只保留硬约束 + 主角档案 + ChapterGoal” 的硬天花板语义不一致。
2. `hard_constraints` 中的 human marks 会被 `_prune_hard_constraints()` 裁剪；一旦进入 hard constraints，语义上应不可裁剪。
3. rewrite 注入的 human instructions 使用 `type` 字段，而 Writer 1.0.9 prompt 渲染 `inst.action`，导致最高优先级人类指令动作标签为空。
4. Craft Card `weight` 排序只影响 `active_ids`，实际渲染仍按 YAML 原始顺序，权重无法控制 prompt 优先级。
5. Writer 动态字数策略、截断上限、RuleAuditor、ScoreAggregator 的 length 口径仍可能不完全一致。

这些问题不是当前最大阻断项，但会影响 Task 112 长跑的可解释性和参数稳定性。

## In Scope（必须完成）

- [ ] **统一 ContextEmergency 语义**
  - 若保留 Level 1/2 分级降级，应改名为 pre-emergency 或 soft-degrade
  - 真正 `budget_used > 1.0` 的 ContextEmergency 必须执行最终硬裁
  - emergency 后确保 `budget_used <= 1.0`

- [ ] **修复 hard_constraints 裁剪语义**
  - `hard_constraints` 不再裁剪
  - 可裁剪的人类标记应留在独立 soft/human_marks 分区
  - 更新测试覆盖 human mark 分区边界

- [ ] **统一 HumanInstruction 字段契约**
  - rewrite 注入使用 `action`
  - 或 Writer prompt 兼容 `inst.action or inst.type`
  - 测试确认 prompt 不再渲染 `- [] ...`

- [ ] **修复 Craft Card 权重渲染顺序**
  - `render_card()` 按 `get_active_sections()` 返回的 `active_ids` 顺序渲染
  - 增加测试断言高权重 section 前置

- [ ] **校准字数策略口径**
  - 梳理 Writer prompt、`enforce_word_count`、RuleAuditor、ScoreAggregator 的容差
  - 明确 chapter_type-aware 动态范围是否作为统一标准
  - 如本 Task 仅文档化差异，应在验收中记录剩余风险

## Out of Scope（明确不做）

- 不调 Writer 文学风格 prompt
- 不新增 Craft Card 版本，除非现有模板无法兼容
- 不改 Task 110e 的 coherence 阈值
- 不跑 Ch101-Ch150 长跑验证

## 接口契约

```python
def render_card(
    self,
    agent_name: str,
    variables: dict[str, Any],
    tags: list[str] | None = None,
) -> str:
    """按 section weight 排序后的 active_ids 渲染 Craft Card."""
    ...
```

```python
def normalize_human_instruction(raw: Mapping[str, Any]) -> HumanInstruction:
    """统一 action/type 字段，保证 Writer prompt 可稳定渲染."""
    ...
```

## 数据模型

优先复用 `HumanInstruction.action`。不新增 SQLite schema。

## 测试要求

### Layer 1: 单元测试
- [ ] Craft Card 高权重 section 在渲染结果中前置
- [ ] rewrite 注入的 instruction 渲染出非空 action 标签
- [ ] hard_constraints 不被 BudgetPruner 裁剪
- [ ] ContextEmergency 后 `budget_used <= 1.0`

### Layer 2: 模块测试
- [ ] Level 1/2 降级与真正 emergency 语义区分清晰
- [ ] dynamic length 策略在 Writer/RuleAuditor/ScoreAggregator 中有一致测试或明确文档

### Layer 3: 回归测试
- [ ] Task 110a-110e 的 context metrics 相关测试不回退
- [ ] Prompt loader 现有测试全部通过

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/ -v` 全部通过
- [ ] `pytest tests/ -q` 全量回归无新增失败
- [ ] `ruff check src/ tests/` 无新增 lint 错误
- [ ] 不违反 AGENTS.md P0 #31、#32、#35、#36 与 P1 #37、#40
- [ ] 生成 `tasks/111c-context-prompt-consistency-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考文档

- `AGENTS.md` — Context Diet 2.0 与 Prompt/状态规则
- `tasks/110c-loading-and-pruning-strategy.md` — 分级 ContextEmergency 来源
- `tasks/110e-coherence-major-fix-DONE.md` — 当前验证基线

## 下一 Task

**Task 112: Ch101-Ch150 流式验证 + 决策门 DG-2**
