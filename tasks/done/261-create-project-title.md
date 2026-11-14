# 261 · create-project --title（dogfood 洞察 ③）

| 项 | 内容 |
|---|---|
| 状态 | TODO（dogfood Run A 实证：无 --title，书名恒为模板默认；owner 批准批次，2026-11-13） |
| 关联 | dogfood 复盘；`create-project` 现网命令 |
| 预估 | 一个选项小切片（TDD） |

## 目标

`create-project --template X --title "书名"` 可选传入书名，落入 `ProjectSetting.title`；缺省仍取模板默认。作者第一触点不再被迫用模板名。

## 步骤

- [ ] TDD：--title 落库 / 缺省模板名不变
- [ ] 全量回归 + ruff；归档；STATUS/HANDOFF 同步

## 验收标准

- [ ] 全量 pytest 绿 + ruff 绿；不 bump
- [ ] 归档 + 文档同步

## 完成总结

（待 DONE 时填写）
