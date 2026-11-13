# 255 · 方向 A：storyline 编辑 CLI（P-bench 补面）

| 项 | 内容 |
|---|---|
| 状态 | TODO（tech-post-m4 §A；路线 B1–B7 已接受，2026-11-13） |
| 关联 | `docs/tech-post-m4.md` §A / B2 / B3；PRD :17/:48 P-bench；task 252（标脏联动） |
| 预估 | 三个编码切片（TDD）+ tests/cli 套件 |

## 目标

`songyan storyline show | edit outline | edit arc | edit thread | remove arc | remove thread`：故事线人编辑写径，与 `canon` 命令族同形。直写 + 历史审计表（路线 B2）；软删 `archived` 标志列（B3）；改动自动联动 252 的 stale_vs_storyline 懒标定（下次 list/pick/generate 触发，无需本任务额外代码）。

## 步骤

- [ ] TDD 切片 1：审计表 `storyline_edit_history` 迁移 + 仓库方法 + edit outline upsert（含审计行同事务）
- [ ] TDD 切片 2：edit arc / edit thread（upsert；字段校验：start<=end、thread 引用存在性拒绝 exit 2；arc_index 冲突口径）
- [ ] TDD 切片 3：remove arc/thread（archived 列迁移、软删、指纹选择排除 archived）+ storyline show --json + 全量回归
- [ ] 完工同步 STATUS/HANDOFF；归档

## 验收标准

- [ ] CRUD 全测；审计表每行 edit/remove 留 before/after
- [ ] 非法引用（弧引用不存在线索）exit 2 拒绝
- [ ] 软删后指纹选择排除 archived（252 切片口径测试复用断言）
- [ ] exit 码 B11 同形；全量 pytest 绿 + ruff 绿；不 bump
- [ ] 完工同步 STATUS/HANDOFF；归档 `tasks/done/`

## 完成总结

（待 DONE 时填写）
