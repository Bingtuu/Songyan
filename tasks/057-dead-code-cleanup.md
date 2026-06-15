# Task 057: 死代码清理

> **Phase**: V3.0 Layer 1 — 消解代码结构债
> **优先级**: P2
> **依赖**: 056（可与 056 并行）
> **预计工作量**: 小（0.5~1 天）

---

## Goal

删除已确认无引用的包装类、冗余类型守卫、过时的 TODO/FIXME，以及不明确的异常重试。

## Context

V2.x 快速迭代中积累了以下已知死代码：

| 位置 | 内容 | 确认无引用来源 |
|------|------|-------------|
| `genres/loader.py:93-110` | `GenreProfileLoader` 类包装 | Pass 9 P2-3 |
| `agents/goal_planner.py:162-194` | 冗余 `isinstance` 类型守卫 | Pass 8 P1-4（Pydantic 已有校验）|
| `src/songyan/llm/retry.py` | 裸 `Exception` 重试 | May 30 C5 |
| 全项目 | `# TODO` / `# FIXME` 注释扫描 | 需逐一评估 |

## In Scope（必须完成）

- [ ] **删除 `GenreProfileLoader` 包装**: 确认全项目无引用后删除
- [ ] **删除冗余 `isinstance` 守卫**: 确认 Pydantic 已覆盖后删除
- [ ] **收缩 `retry.py` 异常类型**: 将裸 `Exception` 改为明确的可重试异常列表（`TimeoutError`, `ConnectionError`, `RateLimitError`）
- [ ] **TODO/FIXME 扫描**: 全项目扫描，分类处理
  - 过时的 → 删除注释
  - 仍有效的 → 保留，但记录到 `docs/review/v3_todo_backlog.md`
  - 本 Task 可解决的 → 直接解决

## Out of Scope（明确不做）

- 不删除任何有测试覆盖的代码
- 不修改任何函数的签名或行为（只删除整个无引用函数/类）
- 不做大的重构（只删除，不移动或合并）

## 测试要求

- [ ] 删除后 `pytest tests/ -x -q` 全部通过
- [ ] `rg "GenreProfileLoader" src/ tests/` 返回空

## 验收标准

- [ ] 删除清单全部执行
- [ ] 被删代码有测试覆盖的测试保持通过
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/057-dead-code-cleanup-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 5.2 删除清单
