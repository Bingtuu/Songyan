# 214 · M2 步3 W4 content_stale + confirm --hard / --mark-stale

| 项 | 内容 |
|---|---|
| 状态 | DOING |
| 关联 | PRD §6.5 / W4；tech-m2 §5 步 3 / B1–B2 / §3.1 / §4.2 |
| 预估 | 一个切片 |

## 目标

M2 步 3：窄迁移 `chapter_heads.content_stale`；`canon confirm attribute|entity` 支持 `--hard` / `--mark-stale`，按闭区间 valid 窗口（及证据章号并集；entity 无窗口时须显式 `--from-ch/--to-ch`）标脏。软确认默认不标；范围不可算且要求标脏时整命令失败（exit 2，不入典也不标）。不改 `ChapterHead.status` 枚举、不加 hardness、不改写 `chapter_versions.content`、不调 Writer。不做步 4+。

## 步骤

- [x] 测试先写：`tests/cli/test_canon_confirm_hard_stale.py`（硬属性 2–4 标脏；旧 version 不覆盖；软无旗不标；`--mark-stale` 可标；不可算 + `--hard` 整失败 exit 2）
- [x] 迁移 + `ChapterHead` / repo 读写 `content_stale`（可选 `stale_marked_at`）
- [x] `canon_write.py`：confirm attribute/entity 旗标 + 同事务入典与标脏
- [x] 轻量同步 STATUS / HANDOFF / tasks README；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] 覆盖 ch 2–4 的硬属性 → 2/3/4 `content_stale=1`，1 与 5 为 0
- [x] `chapter_versions` 旧行 content 不被覆盖；无 Writer 调用
- [x] 软确认无旗标 → 不标脏；`--mark-stale` 可显式标脏
- [x] 不可算范围 + `--hard` → 整命令失败 exit 2（不入典、不标脏）
- [x] 无 hardness 列；无 variant；包仍 `0.5.0`

## 完成总结（DONE 时填写）

（PR 合入后由文档对齐 PR 填写）
