# Task 00X: [任务名称]

> **Phase**: [Phase 1/2/3/4]
> **优先级**: [P0/P1/P2]
> **依赖**: [上游 Task 编号，如 Task 001, Task 002]
> **预计工作量**: [小/中/大]

---

## Goal

一句话描述本 Task 的目标。

## Context

本 Task 在整体流程中的位置，以及为什么现在做它。

## In Scope（必须完成）

- [ ] 具体交付物 1
- [ ] 具体交付物 2
- [ ] 具体交付物 3

## Out of Scope（明确不做）

- 不在本 Task 范围内的事项 1
- 不在本 Task 范围内的事项 2

## 接口契约

```python
# 本 Task 需要实现的公共接口
async def function_name(arg: Type) -> ReturnType:
    """功能简述."""
    ...
```

## 数据模型

```python
# 本 Task 新增或修改的 Pydantic 模型
class NewModel(BaseModel):
    field: str
```

## 测试要求

### Layer 1: 模型测试
- [ ] 新增模型可正确实例化
- [ ] 边界条件验证

### Layer 2: 模块测试
- [ ] 正向用例：正常输入 → 预期输出
- [ ] 异常用例：错误输入 → 预期异常
- [ ] Mock 策略：[Mock DB / Mock LLM / Mock 文件系统]

### Layer 3: 集成测试（如适用）
- [ ] 跨模块调用验证

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_xxx.py -v` 全部通过
- [ ] 代码符合 AGENTS.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 更新了 docs/STATUS.md
- [ ] 生成了 tasks/00x-xxx-DONE.md 交接文件

## 参考文档

- `docs/architecture/xxx.md` — [相关设计文档]
- `archive/v5/context-docs/system_prompt/development-tech-plan-v2.md` — [技术方案相关章节]
