# 206 · canon edit 写入 pending

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD 6.3；tech-m1 §4.1–4.2 / §5 步 2；W0 |
| 预估 | 一个切片 |

## 目标

人可通过 `songyan canon edit` 写入/改写计划行（至少 entity + attribute）；默认 `pending`；attribute 强制 `source=human`；`canon show` Pending 可见；`list_canon_*` 与圣经不可见。本切片不做 confirm / dismiss / check / today 文案。

## 步骤

- [x] 测试先写：edit entity/attribute 后 Pending 可见、Canon/圣经不可见；缺库/缺项目/非法参数 exit 1；输出写明尚未入典
- [x] 实现 `canon edit`（entity + attribute）；注册不破坏 M0 只读命令
- [x] 跑 tech-m1 第 7 节相关命令；开 PR，不合并

## 验收标准

- [x] `songyan canon edit entity|attribute` 写入 pending；attribute `source=human`
- [x] 未 confirm 前不在 `list_canon_*` 与 `load_chapter_plan_bible`（S8）
- [x] `canon show` Pending 可见该 id；输出含尚未入典
- [x] 缺库 / 缺项目 / 非法参数 exit 1；缺库不建空库
- [x] 不改 workflows / settlement_extractor；不升包版本；不做步 3+

## 完成总结（DONE 时填写）

PR [#36](https://github.com/Bingtuu/Songyan/pull/36) squash 进 `main` 为 `5a260a9`。`canon edit` 支持 entity + attribute，写入 pending，attribute 强制 `source=human`；未做 confirm / dismiss / check。下一刀（仅 owner/parent 授权后）：步 3 confirm + dismiss。
