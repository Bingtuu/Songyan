# 255 · 方向 A：storyline 编辑 CLI（P-bench 补面）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-13；tech-post-m4 v2 §A 落地并归档；代码 @ `657d019`） |
| 关联 | `docs/tech-post-m4.md` §A / B2 / B3；PRD :17/:48 P-bench；task 252（标脏联动） |
| 预估 | 三个编码切片（TDD）+ tests/cli 套件 |

## 目标

`songyan storyline show | edit outline | edit arc | edit thread | remove arc | remove thread`：故事线人编辑写径，与 `canon` 命令族同形。直写 + 历史审计表（路线 B2）；软删 `archived` 标志列（B3）；改动自动联动 252 的 stale_vs_storyline 懒标定（下次 list/pick/generate 触发，无需本任务额外代码）。

## 步骤

- [x] TDD 切片 1：审计表 + edit outline upsert（读-改-写 + 审计同事务）。途中修一个 flake：审计行排序断言误用 created_at（秒级 ties）→ rowid
- [x] TDD 切片 2：edit arc / edit thread（upsert；范围/arc_index 唯一/幽灵引用拒绝 exit 2）。途中修真 bug：新 repo 方法误吞 `_row_to_arc` 的 @staticmethod → 调用签名错乱（测试逮住）
- [x] TDD 切片 3：remove 软删（archived 列、幂等 no-op、审计仅记状态迁移）+ show include_archived + 指纹排除实证 252 联动
- [x] 全量回归 3654 passed + tests/cli 292 passed（唯一失败既有 doctor flake）+ ruff 绿；完工同步 STATUS/HANDOFF；归档

## 验收标准

- [x] CRUD 全测（14 测）；审计表每行 edit/remove 留 before/after
- [x] 非法引用 exit 2 拒绝
- [x] 软删后指纹选择排除 archived（指纹变化实证）
- [x] exit 码 B11 同形；全量 pytest 绿 + ruff 绿；不 bump
- [x] 完工同步 STATUS/HANDOFF；归档 `tasks/done/`

## 完成总结

**状态**：DONE（2026-11-13）。`storyline show|edit outline|edit arc|edit thread|remove arc|remove thread` 落地：审计表 storyline_edit_history（同事务）、upsert 语义、窄校验（范围/arc_index 唯一/引用存在 → exit 2）、软删 archived 列（与 status 状态机正交）+ 指纹切片排除（252 标脏联动入口打通）。14 新测 TDD；全量绿。两处方级修正：审计排序断言 rowid、@staticmethod 归属。已知边界：软删行不参与 edit 查找（编辑软删弧等于重建视角），记录在案。
