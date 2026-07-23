# V8 归档索引

> 本目录收纳 V8 阶段（含 V8.5 验收后遗留收口）的全部任务文档与报告。V8 已全量闭环（2026-07-18）：P/C/Q/S/V 五维验收全绿，xuanhuan + wuxia 双体裁 Ch100 五门 PASS，V8.5 遗留项（172j/172k/172l）清零。当前事实入口以 `docs/STATUS.md`、`docs/INDEX.md` 为准；V8 历史事实总索引见 `tasks/V8-README.md`。

## 归档原则

- **V8 已收尾，任务文档与报告统一归档**：172/172a/172b/172c/172d 主线、全部撞墙定点修复（172a.p/172b.p/172b.q/172c.p–172c.t）、V8.4 技术债（172e-172i）、V8.5 收口（172j/172k/172l）均已迁出 `tasks/` 与 `docs/reports/`，只保留 `tasks/V8-README.md` 作为历史事实总索引。
- **归档文件保留原文件名**，便于从历史文档追溯；归档内容默认不读，仅在追溯设计边界时查阅。
- **归档文档内部交叉引用保持冻结**（与 v7 惯例一致）：文内 `tasks/172*.md`、`docs/reports/172*.md` 等相对路径指向的是归档前位置，阅读时请按本索引映射到 `archive/v8/` 下对应文件。
- **172 实施计划已归档**：`archive/superpowers/plans/2026-07-13-project-template-plugin-plan.md`（172-PLAN）。
- **外部调研报告保留为活跃入口**：`docs/reports/v8-literature-and-landscape-review.md` 仍作为 GenreRuntimeProfile 设计依据的活跃参考，未归档。

## 目录

| 路径 | 内容 |
|---|---|
| `archive/v8/tasks/` | V8 全部任务文档：172 模板化、172a 运行时画像、172d 文学护栏、172b/172c Ch100 爬坡、撞墙修复、172e-172i 契约补完、172j/172k/172l 收口 |
| `archive/v8/reports/` | V8 验证报告与证据附件：172a.1 常量审计、172a.4 预算解耦、172a.7 短窗口矩阵、172b/172c Ch100 验收报告 |

## 归档任务（tasks/）

| Task | 归档文档 |
|---|---|
| 172 项目模板化与体裁可插拔 | `archive/v8/tasks/172-project-template-plugin-DONE.md`、`archive/v8/tasks/172-project-template-plugin-TEST-PLAN.md` |
| 172a 体裁运行时画像总览（含 172a.1-172a.7 子任务规划） | `archive/v8/tasks/172a-v8-genre-runtime-profiles.md` |
| 172a.p 伏笔 horizon 下限（S 维度定点修复） | `archive/v8/tasks/172a.p-foreshadowing-horizon-floor.md` |
| 172d 文学护栏跨体裁化 | `archive/v8/tasks/172d-cross-genre-literary-guardrails.md`、`archive/v8/tasks/172d-cross-genre-literary-guardrails-DONE.md` |
| 172b xuanhuan Ch100 爬坡（V 维度） | `archive/v8/tasks/172b-xuanhuan-ch100-climb.md` |
| 172b.p xuanhuan 伏笔长窗口定点修复 | `archive/v8/tasks/172b.p-xuanhuan-foreshadowing-long-window.md` |
| 172b.q consistency CED 终段修复 | `archive/v8/tasks/172b.q-consistency-ced-repair.md` |
| 172c wuxia Ch100 爬坡（第二体裁） | `archive/v8/tasks/172c-wuxia-ch100-climb.md`、`archive/v8/tasks/172c-wuxia-ch100-clean-rerun.md`、`archive/v8/tasks/172c-wuxia-ch100-clean-rerun-DONE.md` |
| 172c.p wuxia 物品追踪粒度修复 | `archive/v8/tasks/172c.p-wuxia-forgotten-inventory-tracking.md` |
| 172c.q wuxia 物品身份语义补强 | `archive/v8/tasks/172c.q-wuxia-inventory-identity.md` |
| 172c.r wuxia 伏笔回收与 continuity 健康度修复 | `archive/v8/tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix.md`、`archive/v8/tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix-DONE.md` |
| 172c.s wuxia 长窗口伏笔 horizon 与 health 校准 | `archive/v8/tasks/172c.s-wuxia-long-window-foreshadowing-and-health-calibration.md` |
| 172c.t wuxia health overdue 权重校准 | `archive/v8/tasks/172c.t-wuxia-health-overdue-weight-calibration.md` |
| 172e ContextManager / BudgetPruner 字段接线 | `archive/v8/tasks/172e-context-manager-profile-wiring.md` |
| 172f SettingEvaporator / 伏笔排序字段接线 | `archive/v8/tasks/172f-evaporation-profile-wiring.md` |
| 172g 角色归档窗口字段接线 | `archive/v8/tasks/172g-character-decay-profile-wiring.md` |
| 172h 连续性审计字段接线 | `archive/v8/tasks/172h-continuity-profile-wiring.md` |
| 172i Profile 回退语义澄清 + 文档修复 | `archive/v8/tasks/172i-profile-fallback-semantics-and-docs.md` |
| 172j BudgetPruner max_* 生产路径遮蔽修复（V9 调参前置） | `archive/v8/tasks/172j-budget-pruner-max-shadowing-fix.md` |
| 172k C 维度判据证据补完（xuanhuan end10 / urban end15 / wuxia end20） | `archive/v8/tasks/172k-c-dimension-evidence-closure.md` |
| 172l V8 文档治理收口 | `archive/v8/tasks/172l-v8-docs-governance-closure.md` |

## 归档报告（reports/）

| 报告 | 归档路径 |
|---|---|
| 172a.1 Context Diet 常量审计 | `archive/v8/reports/172a.1-context-diet-constants-audit.md`（附件 `172a.1-scifi-baseline-profile.json`） |
| 172a.4 预算解耦验证 | `archive/v8/reports/172a.4-budget-decoupling-validation.md` |
| 172a.7 多体裁短窗口验证 | `archive/v8/reports/172a.7-genre-short-window-validation.md`（附件 `172a.7-regression-end10.json`） |
| 172b xuanhuan Ch100 验收报告 | `archive/v8/reports/172b-xuanhuan-ch100-climb.md` |
| 172c wuxia Ch100 验收报告 | `archive/v8/reports/172c-wuxia-ch100-climb.md` |

## 当前仍在主入口的 V8 文件

| 路径 | 用途 |
|---|---|
| `tasks/V8-README.md` | V8 历史任务总索引（已收尾，含 Task 编号治理规则与五维验收证据链） |
| `docs/reports/v8-literature-and-landscape-review.md` | V8 长调研报告：体裁差异与 GenreRuntimeProfile 设计依据，仍作为 V9 调参的活跃参考 |
| `archive/superpowers/plans/2026-07-13-project-template-plugin-plan.md` | 172 实施计划（172-PLAN） |
