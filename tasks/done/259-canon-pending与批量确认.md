# 259 · canon pending 列出 + batch 批量确认（dogfood 洞察 ①）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-13；goal loop 批次首项闭环） |
| 关联 | dogfood 复盘（每章 settlement 产 8–16 条 pending，逐条 confirm 是最大高频摩擦）；tech-m4 B11；B4 成本门交互先例 |
| 预估 | 一个编码切片（TDD） |

## 目标

① `songyan canon pending --project-id [--json]`：列出 pending 提案（entity/attribute 分节，attribute 带 key=value 预览，便于人逐条过目）；② `songyan canon confirm batch --project-id [--yes] [--json]`：批量确认全部 pending——摘要打印（N entity + M attribute）→ 交互 y/N（默认确认软行为，人仍拍板）→ `--yes` 跳过 → **非 TTY 无 `--yes` 拒绝 exit 2**（B4 同形）。空 pending exit 0 明示「无 pending」。

## 口径决策（owner 批准批量时授权助手定）

- 命名为子命令 `batch`（不动 confirm 组的组级语义，避免 invoke_without_command 风险）。
- 只覆盖 entity/attribute 两表（events/clues/anchors 的 pending 目前 settlement 不产）。
- 每行确认走既有 `_confirm_entity/_confirm_attribute`（不带 --hard/--mark-stale：批量只做软确认；要标脏请单条命令）。
- 人确认语义不稀释：批量前必须 y/N 或 --yes，且提示先 `canon pending` 过目。

## 步骤

- [x] TDD：pending 列出（分节 + key=值预览 + --json）；batch --yes 全确认 + approved 集增长断言（7 测）
- [x] TDD：交互 y 过 / n 拒（exit 2 零写入）；非 TTY 无 --yes exit 2（B4 同形）；空 pending exit 0。部分失败逐条隔离报错 exit 1 已确认的保留（实现含，夹具未构造失败例——记录在案）
- [x] 全量 3654 passed + tests/cli 325 全绿 + ruff 绿；归档；STATUS/HANDOFF 同步

## 验收标准

- [x] batch 仍是显式人写径；Canon 三态零变化（复用 _confirm_entity/_confirm_attribute 软确认）
- [x] 部分失败 exit 1 已确认保留（代码路径；无夹具构造）
- [x] 全量 pytest 绿 + ruff 绿；不 bump
- [x] 归档 + 文档同步

## 完成总结

**状态**：DONE（2026-11-13）。`canon pending`（分节列出 + key=值预览）+ `canon confirm batch [--yes]`（摘要 y/N / --yes / 非 TTY 拒绝 exit 2；逐条隔离失败 exit 1 已确认保留）。7 新测；**真实库实证**：dogfood Run A 积压 26 条 pending 一条命令全确认（confirmed=26 failed=0）——本任务要消灭的摩擦原地演示。tests/cli 325 全绿 + 全量 3654 passed。
