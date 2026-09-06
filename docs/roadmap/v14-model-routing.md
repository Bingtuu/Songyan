# V14 Task 总索引

> **阶段**: 成本优化与按角色模型路由
> **定位**: V14 是运行成本工程阶段，目标是把单一 LLM 配置升级为按角色（writer / auditor / settlement / summary 等）独立路由模型，并让路由收益可量化。不新增 Agent，不动 pipeline 结构。
> **当前口径**: V13 已全量闭环（Task 226-229，2026-09-06），口径定义以 `docs/quality-gates.md` 为准。V14 只改 LLM client 的配置注入与成本观测，不改变任何质量门口径。
> **状态**: 进行中。Task 230 model routing audit DONE（报告 `docs/reports/230-v14-model-routing-audit.md`，本地），当前任务为 Task 231 per-role 配置解析与注入。

---

## 背景结论

2026-09 同类项目调研结论：

- 头部同类 ainovel-cli 和 InkOS 均支持按角色分配模型（写手用便宜模型快出稿，审计用强模型精审），这是已被验证的刚需，不是探索性功能。
- Songyan 当前是单一 `LLM_MODEL` 配置，所有角色共用同一模型。settlement prompt 10K+ tokens、auditor 长正文审查、writer 全文生成，三者的成本/能力需求完全不同，统一配置要么浪费成本要么牺牲质量。
- V15（导入续写）将对已有小说做逐章 settlement 回放，一本 200 章的书意味着 200 次 settlement 调用。**V14 是 V15 的成本前置**：没有 per-role 路由，V14 未做就跑 V15 会把回放成本放大数倍。

---

## 一句话目标

> 让 writer / 审查 / settlement / summary 等角色可以独立配置 model / provider / 参数，同窗口 run 的总成本可量化下降，且 CED / T9 / 五门口径与回归结果零变化。

---

## V14 硬边界

- 不新增核心 Agent / Workflow 节点。
- 不改变任何 prompt 内容、审查逻辑、质量门口径或 hard gate。
- 不改变 settlement 数据完整性约束和事务边界。
- 路由配置的解析顺序必须显式文档化，不允许隐式 fallback 行为。
- 配置错误必须 fail-fast（preflight / doctor 层拦截），不允许运行期静默降级到默认模型。
- SQLite 仍是唯一长期事实源；成本拆分数据写入既有 run log / report 结构，不新增事实表。
- 不把 report-only / spike 信号接入任何 runtime 路径。

允许的改动：

- 配置层新增 per-role LLM 配置段与解析逻辑。
- LLM client 调用点按角色注入配置。
- doctor / preflight 增加 per-role 配置校验。
- report / run log 的成本聚合增加 per-role 拆分。
- 顺路执行 217 review 中与 LLM 调用路径直接相关的 backlog（Task 230 审计结论：P2 九项无一直接相关；相关项 P1-2 settlement 重试次数涉及质量行为，另立任务评估，不并入 V14）。

---

## 配置解析契约（规划草案，Task 230 冻结）

```dotenv
# 全局默认（向后兼容，V11 用户配置零迁移成本）
LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...

# 按角色覆盖（未配置的角色回落到全局默认）
LLM_WRITER_MODEL=...
LLM_AUDITOR_MODEL=...
LLM_SETTLEMENT_MODEL=...
LLM_SUMMARY_MODEL=...
```

解析顺序（显式、文档化）：`角色专属配置 → 全局默认`。无其他隐式来源。

角色清单以 Task 230 审计的实际调用点为准，规划预期至少覆盖：writer、rule/llm auditor、revision、settlement、summary、goal_planner、creative_director。

---

## 验收矩阵

| 组 | 验收目标 | 通过标准 |
|----|----------|----------|
| A | 向后兼容 | 只配全局 `LLM_MODEL` 的既有用户行为零变化 |
| B | 路由生效 | 每个角色的实际调用模型可在 run log 中验证 |
| C | fail-fast | 角色配置非法（空 model、非法 base_url 形态）在 preflight 阶段 exit 1，不进 pipeline；真实可达性探测保持 opt-in（`--check-llm`）并扩展为逐角色 |
| D | 成本可量化 | report 输出 per-role token / 成本拆分，同窗口对比有数字 |
| E | 口径零变化 | scifi 短窗口回归通过；CED / T9 / 五门实现零行为变化 |
| F | 既有守护项 | `pytest tests/` 全绿、ruff 通过，不破坏 V11 已验收路径 |

---

## Task 拆解

| Task | 名称 | 状态 | 目标 | 依赖 |
|------|------|:----:|------|------|
| 230 | V14 model routing audit | DONE | 只读审计 LLM client 全部调用点与配置注入路径，冻结角色清单、解析顺序和改动面 | V13 规划 |
| 231 | per-role 配置解析与注入 | TODO | 配置层支持角色覆盖，client 调用点按角色解析，doctor/preflight 校验 | 230 |
| 232 | 成本观测 per-role 拆分 | TODO | run log / report 成本聚合按角色拆分，路由收益可量化 | 231 |
| 233 | V14 回归与成本对比验收 | TODO | scifi 短窗口回归 + 单模型 vs 路由模型同窗口成本对比，产出验收报告 | 231/232 |

---

## Task 230: V14 Model Routing Audit

目标：

- 枚举 `call_llm` / LLM client 的全部调用点，标注所属角色。
- 确认配置注入路径是否支持按角色区分，冻结改动面。
- 冻结角色清单和配置解析顺序（见上节契约草案）。

测试：

- 不改 runtime，纯审计。
- 审计报告必须列出全部调用点及角色归属。

---

## Task 231: per-role 配置解析与注入

目标：

- 配置层支持角色级覆盖，解析顺序显式。
- doctor / preflight 校验每个生效角色配置可达性。
- 非法配置 fail-fast，不静默降级。

测试：

- 只配全局默认时行为与现状一致（回归）。
- 角色覆盖生效可在 run log 验证。
- 非法角色配置在 preflight exit 1。

---

## Task 232: 成本观测 per-role 拆分

目标：

- run log 记录每次 LLM 调用的角色归属。
- report 的成本聚合增加 per-role 维度。

测试：

- 拆分总和等于既有总量（不重复计数、不漏计）。
- 不改变既有 report 字段语义，只新增。

---

## Task 233: V14 回归与成本对比验收

目标：

- scifi 短窗口回归通过，质量门口径零变化。
- 同一窗口分别用单模型和路由配置跑，产出成本对比数字。

测试：

- 验收报告含 run_id、成本拆分、质量门结果对比。

---

## 风险与对策

| 风险 | 对策 |
|------|------|
| 角色配置组合爆炸，用户配错 | 解析顺序只有两个层级；preflight fail-fast；doctor 给推荐配置 |
| 弱模型路由到 auditor 导致质量门数据不可比 | 验收矩阵 E 强制口径零变化；baseline 复验时必须用冻结配置 |
| 改动面扩散到 Agent 内部 | 只允许改配置注入，Agent 签名不变 |
| 成本拆分破坏既有 report 消费者 | 只新增字段，不改既有字段语义 |

---

## 与前置阶段的关系

- V11 的 profile 安全机制（validate / dry-run / rollback）为 V14 的配置面提供既有防护模式，per-role 配置应复用同一套校验纪律。
- V13 公开的口径文档是 V14 验收矩阵 E 的判定依据：口径定义以 V13 文档为准。
- V14 是 V15（导入续写）的成本前置，V15 启动前 V14 必须闭环。
