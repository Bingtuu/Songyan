# Task 086: 动态预算 + 规则分组加载

> **Phase**: V4.0 Phase A — 数据生命周期 + 动态预算
> **优先级**: P0
> **依赖**: Task 083, 084, 085（生命周期字段就绪，repository 查询已过滤）
> **预计工作量**: 中（3 天）

---

## Goal

实现动态预算公式 `8000 + chapter_number * 80` 替代固定 8000 预算；Genre/Mode 规则按 `chapter_type` 分组加载，不再全量注入。两者都在 ContextManager/BudgetPruner 层完成，不修改任何 Agent 代码。

## Context

V3.x 中 budget 固定为 8000，Ch70 时 current_tokens=25288（budget_used=3.16）。静态基线（genre_rules + mode_rules + hard_constraints + arc/volume）约占 ~18K tokens，超过固定预算。动态预算让预算随章节线性增长，与数据增长率匹配。

## In Scope（必须完成）

- [ ] **动态预算公式**：
  - `DEFAULT_BASE_BUDGET = 8000`
  - `BUDGET_INCREMENT_PER_CHAPTER = 80`
  - `dynamic_budget = base + chapter_number * increment`
  - 验证：Ch1=8080, Ch50=12000, Ch70=13600, Ch100=16000
- [ ] **BudgetPruner 适配**：使用 dynamic_budget 替代硬编码 8000/9600/11200
- [ ] **Genre/Mode 规则分组加载**：
  - `GenreProfile` 中规则按 `chapter_type`（如 `setup`, `confrontation`, `resolution`）分组
  - ContextManager 只加载当前 chapter 类型对应的规则子集
  - 向后兼容：未分组的规则默认全量加载
- [ ] **单元测试**：
  - 动态预算公式边界值（Ch1, Ch50, Ch70, Ch100）
  - BudgetPruner 在 dynamic_budget 下正确裁剪
  - Genre 分组加载后 token 数下降

## Out of Scope（明确不做）

- 任何 Agent 代码修改
- 任何 Prompt 修改
- 数据生命周期策略本身（Task 083-085）
- ContextService 架构（Task 092-094，Phase C 门控）

## 接口契约

```python
# src/songyan/agents/context_manager/__init__.py（修改）

class BudgetConfig(BaseModel):
    base_budget: int = 8000
    increment_per_chapter: int = 80
    
    def calculate(self, chapter_number: int) -> int:
        return self.base_budget + chapter_number * self.increment_per_chapter

# src/songyan/genres/loader.py（修改）
class GenreProfile(BaseModel):
    # 现有字段不变
    writer_rules_by_type: dict[str, list[str]] = Field(default_factory=dict)
    # 如 {"setup": [...], "confrontation": [...], "resolution": [...]}
    
    def get_rules_for_chapter_type(self, chapter_type: str) -> list[str]:
        """返回当前 chapter_type 对应的规则子集。"""
        ...
```

## 测试要求

### Layer 2: 模块测试
- [ ] 动态预算：Ch1=8080, Ch50=12000, Ch70=13600, Ch100=16000
- [ ] BudgetPruner：在 dynamic_budget 下正确触发/不触发硬断言
- [ ] Genre 分组：未定义类型的章节回退到全量规则

### Layer 3: 集成测试
- [ ] ContextPackage 组装后，Ch50 的 final_tokens < 12000（理论值）

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/ -k "budget" -v` 全部通过
- [ ] `pytest tests/ -k "genre" -v` 全部通过
- [ ] 动态预算公式 4 个边界值验证正确
- [ ] 全量回归 `pytest -x -q` 通过
- [ ] 生成了 `tasks/086-dynamic-budget-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 4.2 节动态预算
- `src/songyan/agents/context_manager/__init__.py` — BudgetPruner 现有实现
