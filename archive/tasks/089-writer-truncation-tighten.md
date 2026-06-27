# Task 089: Writer 截断阈值对齐（已调整）

> **Phase**: V4.0 Phase B — Agent 约束硬化
> **优先级**: P0
> **依赖**: Task 087（Phase A 通过决策门 0）
> **预计工作量**: 小（2 天）

---

## Goal

Writer 截断阈值收紧为 1.20x/0.80x，直接控制初稿字数。scene 结构保护逻辑不变。

> **V4.0 调整说明**：Task 090a 端到端验证显示原 1.5x/0.7x 阈值过宽，大量章节落在 1.2x~1.5x 灰色地带不被截断。收紧到 1.20x/0.80x（对应达标标准 ±20%），消除灰色地带。RevisionHandler 作为二次保护采用 1.25x/0.75x，略宽于 Writer。

## Context

V3.x（Task 076/081）中截断阈值 1.5x 太宽，导致大量 4000-5000 字章节（目标 3200）不被截断。本 Task 是纯参数调整，不改 Prompt、不改 scene 拆分逻辑、不新增代码路径。

## In Scope（必须完成）

- [ ] **`_enforce_word_count()` 阈值验证**：
  - `_upper = int(word_count_target * 1.20)`（收紧）
  - `_lower = int(word_count_target * 0.80)`（收紧）
- [ ] **scene 结构保护不变**：单 scene 不截断、fallback 逻辑不变
- [ ] **单元测试**：
  - 阈值计算正确（1.3x / 0.75x）
  - 边界：target=3200 → upper=4160, lower=2400
  - 场景结构保护仍生效
- [ ] **端到端验证**：4000+ 字章节占比下降

## Out of Scope（明确不做）

- 修改 Writer Prompt
- 修改 scene 拆分/解析逻辑
- 修改 `_count_chinese_words()` 实现
- 任何其他 Agent

## 接口契约

```python
# src/songyan/agents/writer.py（修改 _enforce_word_count）

def _enforce_word_count(
    content: str,
    scenes: list[dict],
    word_count_target: int,
    current_word_count: int,
) -> tuple[str, list[dict], int, bool, str]:
    """强制截断正文到目标字数范围内."""
    _upper = int(word_count_target * 1.20)  # 收紧
    _lower = int(word_count_target * 0.80)  # 收紧
    # ... 其余逻辑不变
```

## 测试要求

### Layer 2: 模块测试
- [ ] 阈值：target=3200 → upper=3840, lower=2560
- [ ] 内容 4000 字 → 触发截断（1.2x=3840，超过即截断）
- [ ] 单 scene 保护：内容 5000 字但只有 1 个 scene → 不截断

### Layer 3: 集成测试
- [ ] 端到端：达标率（±20%）> 60%（原基线 36.8%）

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/agents/test_writer.py -v` 全部通过
- [ ] 端到端 5500+ 字章节占比下降
- [ ] 生成了 `tasks/089-writer-truncation-tighten-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 5.2 节
- `src/songyan/agents/writer.py` — `_enforce_word_count()`
- `tasks/076-writer-forced-truncation-DONE.md` — 原截断实现
