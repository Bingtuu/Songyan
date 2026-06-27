# Task 100c: 上下文压力优化（四信号系统调优）

> **Phase**: V4.0 Phase B — 修复收尾
> **优先级**: P1
> **依赖**: Task 100b
> **预计工作量**: 中

---

## Goal

将 `narrative_fullness` 从依赖 CreativeDirector LLM 输出的主观信号，改为基于 `token_budget` 的客观计算；优化焦段触发逻辑，缓解上下文过载导致的 Writer 压缩自保（如 Ch9 的 0.522x）。

## Context

Task 099 发现 Ch9 仅 1828/3500=0.522x，此时 `token_budget=0.998`（几乎触顶），`settings_active=45`，`foreshadowings_active=27`，`prompt_length=9388`。Writer 面对极满的上下文包选择了压缩叙事而非展开。

当前四信号系统的缺陷：
1. `narrative_fullness` 由 CreativeDirector LLM 输出，**如果 LLM 不输出或输出 0.0，系统不触发压缩保护**
2. `token_budget > 0.95` 时 Writer 行为异常，但四信号系统未感知此客观指标
3. `focal_distance` 的 `disruption` 是确定性截断（取前半部分），未实现真正的叙事断裂效果
4. 硬上限（MAX_CHARACTER_STATES=4 等）是固定值，不随项目规模缩放

## In Scope（必须完成）

- [ ] 在 `context_manager_node` 中增加 `token_budget` 客观计算：
  - 若 `ctx.budget_used > 0.95`：强制 `narrative_fullness = max(narrative_fullness, 0.9)`
  - 若 `ctx.budget_used > 0.90`：强制 `narrative_fullness = max(narrative_fullness, 0.7)`
- [ ] 当 `narrative_fullness >= 0.9` 时，自动触发 `focal_distance = "close"`（而非依赖 LLM 输出）
- [ ] 硬上限动态化：
  - `MAX_CHARACTER_STATES = max(4, min(8, total_characters // 3 + 1))`
  - `MAX_SOFT_REFS = max(10, min(16, total_settings // 5 + 2))`
  - 保留绝对上限防止无限制膨胀
- [ ] `disruption` 焦段改为随机截断（使用 `random` 模块，但固定 seed 保证可复现）
- [ ] 将 `context_pressure` 指标（token_budget, fullness_factor, focal_distance）写入 `generation_metadata` 供后期复盘
- [ ] 运行 5 章端到端验证（建议选择 Ch8-Ch12 区间，验证早期章节上下文过载保护）

## Out of Scope（明确不做）

- 不改造 ContextService 架构（属于 Phase C / Task 104+）
- 不修改 BudgetPruner 的逐层裁剪策略（保持现有优先级体系）
- 不增加新的 Agent 或 Workflow 节点

## 接口契约

```python
# context_manager/__init__.py
def _calculate_objective_fullness(
    narrative_fullness: float,
    budget_used: float,
) -> float:
    """基于 token_budget 客观计算 narrative_fullness.
    
    规则：
    - budget_used > 0.95 → fullness = max(fullness, 0.9)
    - budget_used > 0.90 → fullness = max(fullness, 0.7)
    - 否则保持 LLM 输出的 fullness
    """
    ...

# assemble_context_package 中调用
obj_fullness = _calculate_objective_fullness(_nf, ctx.budget_used)
```

## 数据模型

无新增模型，修改常量和 generation_metadata：

```python
# context_manager/__init__.py
# 硬上限改为动态计算函数
def _dynamic_max_character_states(total_characters: int) -> int: ...
def _dynamic_max_soft_refs(total_settings: int) -> int: ...

# generation_metadata 新增字段（自动写入）
{
    "context_pressure": {
        "token_budget": 0.998,
        "narrative_fullness_llm": 0.0,
        "narrative_fullness_objective": 0.9,
        "focal_distance": "close",
        "fullness_factor": 0.55,
    }
}
```

## 测试要求

### Layer 1: 单元测试
- [ ] `budget_used=0.96, fullness=0.0` → 预期 `objective_fullness=0.9`
- [ ] `budget_used=0.85, fullness=0.3` → 预期 `objective_fullness=0.3`
- [ ] 18 人物场景 → `MAX_CHARACTER_STATES=6`（max(4, min(8, 18//3+1))=6）

### Layer 2: 集成测试
- [ ] ContextPackage 组装后 `budget_used > 0.95` → 验证 `focal_distance` 被强制为 close

### Layer 3: 5 章验证
- [ ] 5 章端到端（Ch8-Ch12），检查 generation_metadata 中 context_pressure 记录完整
- [ ] 无 Ch9 类 token_budget=0.998 但 fullness=0.0 的失配情况

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_context_manager.py -v` 全部通过（新增客观 fullness 测试）
- [ ] 5 章端到端验证：
  - 无上下文过载导致的极端不足章节（<0.70x）
  - generation_metadata 中 context_pressure 字段完整
- [ ] ruff 检查无新增错误
- [ ] 生成 `tasks/100c-context-pressure-optimization-DONE.md` 交接文件

## 参考文档

- `tasks/099-ch71-ch100-extension-DONE.md` — Ch9 根因分析（token_budget=0.998）
- `src/songyan/agents/context_manager/__init__.py` — BudgetPruner + 四信号集成
- `src/songyan/agents/context_manager/_assemblers.py` — 角色快照组装
