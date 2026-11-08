# 236 · M4 技术方案前置调研（项目调研 / 技术分析 / review 资料收集）

| 项 | 内容 |
|---|---|
| 状态 | DONE（2026-11-08） |
| 关联 | 下一闸门 = M4+ 技术方案（STATUS/HANDOFF/AGENTS 已记）；owner 2026-11-08 授权调研，备料后启动草稿 |
| 预估 | 研究切片（无代码改动；产出调研报告） |

## 背景

M0–M3 代码验收 PASS @ `594144b`。M4 主要交付 `chapter continue` / `review`（作者主路径的续写与审读），开工前需 owner 书面接受技术方案；方案质量取决于本轮调研。四大前置设计问题（先期清单）：

1. chapter 状态机映射（`chapter_heads` 现状 → 可续写章）
2. continue ↔ variant 衔接（continue 与 M3 抽卡的关系）
3. review 输入并集（check / gate / LiteraryAuditor 聚合为人可读报告）
4. ContextEmergency 露出（Ch1–10 时 10/10 触发的代理信号是否人可见）

## 调研面（四路并行）

- [x] **A 需求面**：PRD M4 条目 / W0–W6 工作流 / P-draft·P-bench 路径 / §7.2 §9.3 / `[proposed]` 命令全集；M4 在 PRD 的边界内/外
- [x] **B 代码现状面**（explore 子代理）：chapter_heads / chapter_versions / chapter_variants 表结构与状态取值；canon CLI 面；`check` / plan_fact_gate / LiteraryAuditor 输出结构；ContextEmergency 触发链；`run` 管线与 variant 主路径的交集
- [x] **C 历史经验面**：2026-11-07 评审审计报告中对 M4 的前瞻观察；task 226/231 修复教训；Ch1–10 失败经验（DG-1、ContextEmergency 10/10、文学审查项）
- [x] **D 外部调研面**：同类长文写作工具的「续写 / 审读」交互做法（轻量 WebSearch，只取可借鉴模式，不引入依赖）

## 产出

- [x] `docs/reports/236-m4-preresearch.md`：四路发现 + 四大设计问题逐一深化（现状证据 → 约束 → 可选方案 → 建议）+ 新问题清单（N1–N7）
- [x] 只读 review → 归档 → STATUS/HANDOFF 同步 → 本地提交

## 验收标准

- [x] 四大设计问题每条有代码级证据指针（文件:行号）与至少两个可选方案。
- [x] 调研报告覆盖 A–D 四路；结论与 PRD 边界不冲突。
- [x] review 无 blocker；major（N1 证据失实：遗漏 import replay 自动 accepted 写径）已修订吸收，minor 5 条已同切片修入报告。

## 完成总结

**状态**：DONE（2026-11-08）。

**产出**：`docs/reports/236-m4-preresearch.md`（A 需求 / B 代码现状 / C 历史经验 / D 外部调研四路；Q1–Q4 深化各含 2–3 方案；新问题 N1–N7；tech-m4 草稿结构建议与四步草案；可复用零件清单 12 项）。

**关键发现（供 owner 快速决策）**：

1. M4 零件充足，主成本在语义衔接设计（§1 结论 1）。
2. N1+N7：人确认 accepted 写径仅 run 管线 human_confirm 一条；另有 import replay 自动 accepted 写径——M4 方案必须回答确认闸与 import 的并存口径。
3. N2：continue 复用 run 零件会按 accepted 判定「上一章」，picked 未确认时回头重写——必须设计确认闸。
4. N3：review 写库边界需拍板（建议默认纯只读，守 PRD :586 字面）。

**review**：agent-13 抽查 20+ 代码引用与 16 处 PRD 行号；major 1（N1 遗漏 import replay 写径，已修订入 §1/§3.2/§6 N7）；minor 5（profile 覆盖注记 / snapshot 查询方法需新建 / evals 复读信号可复用 / 行号微调 / Q4 措辞）已同切片修入。

**验证**：报告经只读 review 修订后无 blocker / 未修 major；无代码改动，无需回归。
