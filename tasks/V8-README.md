# V8 Task 总索引

> **阶段**: 多体裁可插拔质量 → 多体裁章数爬坡  
> **当前口径**: V7 在 sci-fi 单一体裁下达成 Ch200 后收尾。V8 把系统从"只会写科幻"解耦为"按体裁调整写法"，建立 `GenreRuntimeProfile`，先让 xuanhuan/wuxia/urban 在短窗口（end 10/15/20）稳定通过，再向中篇（Ch100/Ch150）爬坡。  
> **最后整理**: 2026-07-14（V7 收尾，V8 启动，历史报告归档）

本文是 V8 阶段任务文档的事实入口。V7 历史事实入口见 `tasks/V7-README.md`；V6 见 `tasks/V6-README.md`；V5 见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。

---

## 一句话目标

> **V8 让系统的长跑能力从科幻单一体裁泛化到多个中文网文体裁。核心抓手是 `GenreRuntimeProfile`：把 Context Diet 2.0 的预算分配、门禁阈值、状态压缩、伏笔蒸发等运行时契约从 sci-fi 默认值中解耦，让玄幻、武侠、都市等体裁都能稳定生成，再逐步把验证窗口从短章拉向中篇。**

---

## 阶段验收判定

V8 通过 = 同时满足以下四项：

| 维度 | 判据 |
|------|------|
| **P（可插拔）** | `GenreRuntimeProfile` 机制可插拔：新增体裁只需新增 Profile 文件/记录，不修改核心逻辑；无 Profile 体裁 100% 回退旧行为 |
| **Q（短窗口质量）** | xuanhuan/wuxia/urban `--end 10` 全 accepted，无 budget halt；xuanhuan `--end 15` 全 accepted；xuanhuan `--end 20` gap ≤1 且有明确 isolate 记录 |
| **S（状态可控）** | xuanhuan end 15 中 overdue foreshadowing < 5（基线 13），ContextEmergency 触发率 ≤50%（基线 100%），budget_used 峰值 < 1.0 |
| **V（中篇爬坡）** | 至少一个非 sci-fi 体裁稳定推进到 Ch100（可选目标，视 173 完成后资源决定） |

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

xuanhuan 短窗口现状（V8 启动基线）：

| 指标 | `--end 3` | `--end 15` |
|---|---|---|
| 完成章节 | 3/3 | 7/15（Ch8 被 halt） |
| T9 hard issue | 0 | 0 |
| ContextEmergency | 3/3 | 8/8（推断） |
| budget_used 峰值 | <1.3 | **1.4019** |
| halt 原因 | 无 | `context_emergency_budget_ratio_halt` |
| Ch8 伏笔状态 | — | 10 planted / 3 due / 13 overdue |

sci-fi 对比基线：

| 指标 | sci-fi Ch200 |
|---|---|
| accepted | 200/200 |
| T9 hard issue | 0 |
| ContextEmergency | 偶发，不连续 |
| budget_used | 长期 <1.0 |

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
- **短窗口优先**：V8.1 不追求 Ch100+，先让各体裁在 end 10/15/20 稳定通过，把 ContextEmergency、budget_used、伏笔回收等关键指标压下来。
- **Ch100 爬坡后置**：174/175 是可选目标，视 173 完成后计算资源与 LLM 预算决定。
- **文档纪律**：173 各子任务在开工前写详细规划；173g 完成后必须产出多体裁短窗口验证报告；174/175 在实跑数据出炉后补齐，避免文档超前返工。

---

## V8 明确不做（划界）

| 项 | 归属 |
|----|------|
| 新增 Agent / Workflow 节点 | V8 只做运行时参数解耦，不新增节点 |
| 全自动跨体裁 LLM 改写闭环 | 不做；只调 Context Diet 预算、阈值、压缩策略 |
| 所有体裁一次验证到 Ch200 | V8 目标先做到短窗口稳定 + 1-2 体裁 Ch100；Ch200 跨体裁验证划归 V9 或更晚 |
| 多项目并发 / 分布式长跑 | 不做 |
| 继续优化 sci-fi 单一体裁到 Ch250/Ch300 | 已取消，划归 V7 历史目标 |

---

## 文档入口

- V8 任务事实：本文档
- V8 P0 详细规划：`tasks/173-genre-runtime-profiles.md`
- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
- V7 历史事实：`tasks/V7-README.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
- 开发规范：`AGENTS.md`
