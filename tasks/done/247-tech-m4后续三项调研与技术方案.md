# 247 · tech-m4 §9 后续三项：调研与技术方案

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-12；方案 v1 被 owner 接受——拍板「开工」，B1–B8 原样） |
| 关联 | tech-m4 §9「以后的技术方案」；PRD §9.2 命令树；task 236 前置调研（N1–N7）；task 243（M4 §6–7 PASS） |
| 预估 | 调研 + 方案文档一版（本文档）；拍板后再拆编码任务 |

## 目标

把 tech-m4 §9 留后的三项落成一版可拍板的技术方案：**步 1 `chapter status`（只读章进度，不承载 ContextEmergency）→ 步 2 导入后再续写验收（真实模型冒烟）→ 步 3 `review --deep`（显式 LLM 深审，成本前置提示）**。owner 已预拍板：①一案三步按此顺序；②--deep 成本门 = 交互确认 + `--yes` + `--budget-cny`；③chapter status 字段面 = 中薄面。

## 步骤

- [x] 重读 tech-m4 §9 原文、task 236 调研（N1–N7）、PRD §9.2 分工句。
- [x] 现状面取证：`status` / `review` / `import replay` / `chapter_progress` 服务。
- [x] owner 预拍板三个方向性问题（立项形态 / --deep 成本门 / status 字段面）。
- [x] 产出 `docs/tech-m4-followup.md`（调研结论 + B 决策点 + 三步设计 + 验收分列）@ `928de90`，owner 已接受（「开工」，B1–B8 原样）。
- [x] owner 书面接受后拆编码任务：248 chapter status / 249 导入验收 / 250 review --deep（已建，见 tasks/ 平铺）。

## 验收标准

- [ ] 方案文档覆盖三项，每项有：命令面、字段/输入/输出口径、exit 码、写库边界、费用口径、验收标准
- [ ] B 决策点逐条可单独拍板（仿 tech-m4 B1–B12 格式）
- [ ] N7 口径（import 自动 chapter accepted vs 无自动 Canon approved）在步 2 验收中分列写明
- [ ] 不做清单显式排除：自动选优 / chapter status 变写操作 / --deep 自动改稿 / 题材检查器
- [ ] owner 书面接受（或点名修改后轮转），此后才建编码任务

## 完成总结

**状态**：DONE（2026-11-12）。方案 `docs/tech-m4-followup.md` v1 @ `928de90`；owner 拍板「开工」，B1–B8 原样接受。编码任务 248/249/250 已建。
