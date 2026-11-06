# 220 · M3 步1 chapter_variants 表 + fingerprint + 仓库

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §4.2 / M3；tech-m3 §5 步 1 / B1–B2；owner t104s937 接受 |
| 预估 | 一个切片 |

## 目标

M3 步 1：迁移 `chapter_variants`；`parent_canon_fingerprint` 纯函数 + 单测；repo 插入/列表/同章单 picked 守卫；可选注册真实可跑的 `variant list`（空章返回空列表）。无 generate/pick/abandon/stale 标记逻辑（字段默认即可）。

## 步骤

- [x] 测试先写：迁移可重复；指纹稳定；pending 不变指纹；双 picked 失败；`variant list` 空列表
- [x] 迁移 + 模型 + repo + fingerprint；注册 `variant list`
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tech-m3 接受注记；跑 ruff + 相关 pytest；开 PR，不合并、不 APPROVE

## 验收标准

- [x] `chapter_variants` 在 `_EXPECTED_TABLES` / init_schema；迁移可重复
- [x] 指纹对同一 approved 集合稳定；pending 变更不改变指纹
- [x] 同章双 `picked` 写入失败（`DuplicatePickedVariantError`）
- [x] `variant list` 对无槽章返回空；无「未实现」桩
- [x] 无步 2+；无 continue/review/branch；包仍 `0.5.0`

## 完成总结（DONE 时填写）

PR [#56](https://github.com/Bingtuu/Songyan/pull/56)；head `85b6bc7`；base tip `main` `5101555`（#55）。未 merge / 未 APPROVE。下一刀（仅 owner/parent 授权后）：M3 步 2 `variant generate`。
