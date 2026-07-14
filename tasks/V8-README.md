# V8 Task 总索引

> **阶段**: 多体裁可插拔质量 → 多体裁章数爬坡  
> **当前口径**: V7 在 sci-fi 单一体裁下达成 Ch200 后收尾。V8 的目标不是再做一轮类似 Task 170 的"文学性专项 prompt 工程"，而是把支撑 sci-fi 长跑的**工程底盘**（Context Diet 2.0、门禁、结算、连续性审计）从科幻隐式画像解耦，建立 `GenreRuntimeProfile`，让 xuanhuan/wuxia/urban 等体裁也能达到与 sci-fi **同等的完成度和质量基线**，再向中篇（Ch100/Ch150）爬坡。  
> **最后整理**: 2026-07-14（V7 收尾，V8 启动，历史报告归档）

本文是 V8 阶段任务文档的事实入口。V7 历史事实入口见 `tasks/V7-README.md`；V6 见 `tasks/V6-README.md`；V5 见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。

---

## 一句话目标

> **V8 让系统从"只会写科幻"变成"每个体裁都能写到科幻的质量水位"。核心抓手是 `GenreRuntimeProfile`：把 Context Diet 2.0 的预算分配、门禁阈值、状态压缩、伏笔蒸发等运行时契约从 sci-fi 默认值中解耦，使玄幻、武侠、都市等体裁在 accepted 率、文本洁净、事实一致性、连续性、health 等维度上达到与 sci-fi 同等的基线，再逐步把验证窗口从短章拉向中篇。**

---

## 阶段验收判定

V8 通过 = 同时满足以下五项：

| 维度 | 判据 |
|------|------|
| **P（可插拔）** | `GenreRuntimeProfile` 机制可插拔：新增体裁只需新增 Profile 文件/记录，不修改核心逻辑；无 Profile 体裁 100% 回退旧行为 |
| **C（完成度）** | xuanhuan/wuxia/urban 短窗口验证 accepted 率达到 sci-fi 同级：**--end 10 全 accepted，--end 15 全 accepted，--end 20 gap ≤1 且有明确 isolate 记录** |
| **Q（质量同标）** | 各体裁短窗口质量指标对齐 sci-fi 基线：T9 hard issue = 0；ContextEmergency 不连续触发；budget_used 峰值 < 1.0；health 不持续退化；连续性审计 critical mismatch = 0；**一致性错误密度 CED ≤ sci-fi 同级** |
| **S（状态可控）** | xuanhuan end 15/20 中 overdue foreshadowing < 5（基线 13），伏笔回收链不崩；角色/设定状态膨胀受控 |
| **V（中篇爬坡）** | 至少一个非 sci-fi 体裁稳定推进到 Ch100，且前 100 章质量指标不劣于 sci-fi Ch1-Ch100 基线 |

### 外部调研支撑

长调研报告见 `docs/reports/v8-literature-and-landscape-review.md`。核心结论：

1. **体裁差异本质上是状态动力学差异**（CreAgentive、DOME、ConStory-Bench 共同支持），不存在单一上下文策略能覆盖所有体裁。
2. **GenreRuntimeProfile 与外部最佳实践一致**：CreAgentive 的 genre-agnostic Story Prototype + style realization 解耦、AI Dungeon/NovelAI 的 Memory/Lorebook、DOME 的 hierarchical outline + memory weights 都指向“运行时按体裁定制上下文”是必然的工程路径。
3. **一致性评估需要专用密度指标**：ConStory-Bench 的 Consistency Error Density (CED) 可跨体裁公平比较，V8 应将其纳入验收。
4. **sci-fi baseline 必须显式化**：V7 的成功依赖于一组未文档化的默认参数，V8 第一步应把当前默认值固化为 `scifi` profile，避免后续调参回退旧行为。

---

## Task 状态

> 状态口径：`◻ 规划中`（有规划稿，未开工）/ `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成` / `⚠️ 条件未通过` / `⏳ 占位`（骨架占位，详细文档待前置数据出炉后写）。

### V8.1：体裁运行时画像（GenreRuntimeProfile）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 173 | 体裁运行时画像总览 | 🔄 进行中 | `tasks/173-genre-runtime-profiles.md` |
| 173a | 现状审计与常量提取 | ◻ 规划中 | 待 173 开工后写 |
| 173b | `GenreRuntimeProfile` 数据模型 + 数据库表 | ◻ 规划中 | 待 173a 后写 |
| 173c | 按体裁加载 Profile | ◻ 规划中 | 待 173b 后写 |
| 173d | Context Diet 预算分配按体裁 | ◻ 规划中 | 待 173c 后写 |
| 173e | 硬门禁阈值按体裁 | ◻ 规划中 | 待 173d 后写 |
| 173f | 状态压缩与伏笔蒸发按体裁 | ◻ 规划中 | 待 173e 后写 |
| 173g | 多体裁短窗口验证 | ◻ 规划中 | 待 173f 后写 |
| 173p | GenreRuntimeProfile 撞墙定点修复（占位） | ⏳ 占位 | 待 173g 实跑后确定 |

### V8.2：多体裁章数爬坡

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 174 | 非 sci-fi 体裁 Ch100 爬坡验证（候选：xuanhuan / wuxia） | ⏳ 占位 | 待 173 完成后写 |
| 174p | Ch100 撞墙定点修复（占位） | ⏳ 占位 | 待 174 实跑后确定 |
| 175 | 第二个非 sci-fi 体裁 Ch100 爬坡验证 | ⏳ 占位 | 待 174 完成后写 |
| 175p | Ch100 撞墙定点修复（占位） | ⏳ 占位 | 待 175 实跑后确定 |

---

## 关键数据

### xuanhuan 短窗口现状（V8 启动基线）

| 指标 | `--end 3` | `--end 15` |
|---|---|---|
| 完成章节 | 3/3 | 7/15（Ch8 被 halt） |
| accepted 率 | 100% | 46.7% |
| T9 hard issue | 0 | 0 |
| ContextEmergency | 3/3 | 8/8（推断） |
| budget_used 峰值 | <1.3 | **1.4019** |
| halt 原因 | 无 | `context_emergency_budget_ratio_halt` |
| Ch8 伏笔状态 | — | 10 planted / 3 due / 13 overdue |

### sci-fi 对比基线（V8 目标水位）

| 指标 | sci-fi Ch200 |
|---|---|
| accepted | 200/200（100%） |
| T9 hard issue | 0 |
| ContextEmergency | 偶发，不连续 |
| budget_used | 长期 <1.0 |
| health | median ≥8.5，无连续真实退化 |
| critical orphan | 0 |

**V8 的完成标准**：非 sci-fi 体裁在对应窗口内，accepted 率与质量指标必须达到 sci-fi 同级，而不只是"能跑完"。

---

## 依赖关系与执行纪律

```
173a 常量审计 ──► 173b 模型 ──► 173c 加载机制 ──► 173d 预算分配 ──► 173e 门禁阈值 ──► 173f 状态压缩 ──► 173g 短窗口验证
                                                                                                      │
                                                                                                      ▼
                                                                                              174 Ch100 爬坡（候选 xuanhuan）
                                                                                                      │
                                                                                                      ▼
                                                                                              175 第二体裁 Ch100 爬坡
```

- **173 串行为主**：Profile 机制是后续所有体裁调参的地基，必须等模型与加载机制落地后才能调预算/阈值/压缩策略。
- **不回退 sci-fi**：任何 Profile 改动必须通过 sci-fi `--end 10` 回归，保证旧行为不变。
- **短窗口是对标手段，不是终点**：V8.1 用 end 10/15/20 快速验证各体裁是否能达到 sci-fi 同级质量；通不过不进 174。
- **质量同标，不放宽口径**：非 sci-fi 体裁的 T9/health/orphan/伏笔回收等硬指标与 sci-fi 使用同一套冻结口径，不因"体裁特殊"而降低验收。
- **Ch100 爬坡后置**：174/175 是必选目标（非可选），但必须在 173g 证明各体裁短窗口质量达标后启动。
- **文档纪律**：173 各子任务在开工前写详细规划；173g 完成后必须产出多体裁短窗口质量对标报告；174/175 在实跑数据出炉后补齐，避免文档超前返工。

---

## V8 明确不做（划界）

| 项 | 归属 |
|----|------|
| 重复 Task 170 式文学性专项 prompt 工程 | V8 是工程底盘解耦，不是文学 rubric 调优；文学质量仍按 V7 三层契约观测，不作为阻塞门 |
| 新增 Agent / Workflow 节点 | V8 只做运行时参数解耦，不新增节点 |
| 全自动跨体裁 LLM 改写闭环 | 不做；只调 Context Diet 预算、阈值、压缩策略 |
| 所有体裁一次验证到 Ch200 | V8 目标先做到短窗口质量同标 + 1-2 体裁 Ch100；Ch200 跨体裁验证划归 V9 或更晚 |
| 多项目并发 / 分布式长跑 | 不做 |
| 继续优化 sci-fi 单一体裁到 Ch250/Ch300 | 已取消，划归 V7 历史目标 |

---

## 文档入口

- V8 任务事实：`tasks/V8-README.md`
- V8 P0 详细规划：`tasks/173-genre-runtime-profiles.md`
- V8 长调研报告：`docs/reports/v8-literature-and-landscape-review.md`
- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
- V7 历史事实：`tasks/V7-README.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
- 开发规范：`AGENTS.md`
