# 261 · create-project --title（dogfood 洞察 ③）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-13；goal loop 批次第三项闭环） |
| 关联 | dogfood 复盘；`create-project` 现网命令 |
| 预估 | 一个选项小切片（TDD） |

## 目标

`create-project --template X --title "书名"` 可选传入书名，落入 `ProjectSetting.title`；缺省仍取模板默认。作者第一触点不再被迫用模板名。

## 步骤

- [x] TDD：--title 落库（夜班回声实测入库）/ 缺省模板名不变（2 测）
- [x] 全量 3654 passed + tests/cli 325 全绿 + ruff 绿；归档；STATUS/HANDOFF 同步

## 验收标准

- [ ] 全量 pytest 绿 + ruff 绿；不 bump
- [x] 归档 + 文档同步

## 完成总结

**状态**：DONE（2026-11-13）。`create-project --title` 落库（模板建项后 UPDATE；缺省行为不变）。goal loop 批次（259/260/261）全部闭环。
