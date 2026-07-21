# Task 186: urban Ch100 爬坡任务书

> **阶段**: V9.5 urban 第三体裁中篇爬坡
> **类型**: 真实 LLM 实跑 / 中篇爬坡 / 冻结口径验收
> **优先级**: P1（V9 B 组判据，地基实战验收）
> **依赖**: 185 urban 短距验证已完成（初始 base_budget=12000，end15 15/15、T9=0、emergency=0）；187.p 已按 Ch19 ContextEmergency 证据将 Ch100 爬坡 registry baseline 提升到 14000
> **状态**: ✅ 任务书完成（设计 review 后已修订，准入 Task 187）
> **来源**: `tasks/V9-README.md` Task 186 行；172b xuanhuan/wuxia Ch100 爬坡方法论

---

## 任务边界

本任务目标是完成 **urban 体裁 Ch1-Ch100 中篇爬坡**，用冻结五门口径验证 V9 生产化地基在第三体裁上的实战可用性，为 V9 收口提供最终质量证据。

必须完成：

1. 编写本任务书并通过评审（治理规则：先补任务书再开跑）。
2. 复用 `scripts/run_172b_ch100_climb.py`，以 `TEMPLATE_ID=urban RUN_ID=187` 启动爬坡（执行归 Task 187）。
3. 每 25 章一段（arc 边界）做段边界质量门审计，任一 FAIL 冻结现场 → 定点修复（按 `187.p/q/…` 登记）→ 机制修复后 clean rerun。
4. 终判按冻结口径：Ch1-Ch100 全 accepted、budget<1.0、CED≤sci-fi 同级×1.15、overdue≤sci-fi 同章尺度、health≥8.0、T9=0。
5. 证据落盘，Task 187 单独写执行记录；V9 收口时统一更新 V9-README / STATUS / INDEX / README。

不做：

- 不改动核心工作流节点或 Agent 边界。
- 不新增体裁 runtime profile 字段（185 落定初值 base_budget=12000、floor=0；187.p 仅调整既有 urban `base_budget` 字段到 14000）。
- 不放宽 T9、budget、CED、overdue、health 任一口径。
- 不做 V10 优秀度信号包或跨体裁 Ch200。

---

## 前置证据（185 短距验证，2026-07-20）

| 指标 | urban end15（registry 默认值） | 结论 |
|---|---|---|
| accepted | 15/15 | 完成度 PASS |
| budget_used 峰值 | 0.9643 | < 1.0，无 emergency |
| before_emergency 峰值 | 0.0 | 远离 1.3 halt 线 |
| context_emergency_count | 0 | 172k 的 17 次连续 emergency 已消除 |
| overdue | 3 | 短窗口无 floor 压力 |
| CED/1k | 5.46 | 与 sci-fi 同量级 |
| T9 | 0（修复后检测器复测） | 文本洁净 PASS |
| 成本 | ¥1.733 | 单章约 ¥0.116 |

**推入 Ch100 的关键不确定性**：

- urban 对话密度、现代职业/地点一致性在 15 章内未充分展开，长窗口下是否出现新的 CED 热点或 overdue 墙是主要风险。
- `foreshadowing_horizon_floor` 在 185 保持 0；Ch100 尺度若 overdue 失控，优先查 resolve 机制，再评估是否启用 floor。

---

## 设计 review 结论（2026-07-20）

结论：**准入 Task 187**。review 后对任务书做了三处执行性修正：

1. `scripts/run_172b_ch100_climb.py` 当前不读取外部 `DATABASE_URL` 作为爬坡库路径，而是按 `TEMPLATE_ID` 固定写入 `.tmp/task172b_<template>_ch100.db`，project id 写入 `.tmp/task172b_<template>_project.json`。本任务采用现有 harness 路径，不为 187 新增路径参数，降低对已验证爬坡工具的扰动。
2. `scripts/five_gate_check.py` 与 `scripts/segment_audit.py` 均要求显式 `--project-id`，且没有 `--output` 参数。审计 JSON 通过 stdout 重定向落盘。
3. wrapper 的 `-SuccessMarkerRegex '"status": "completed"'` 不匹配当前 harness 输出；改为使用 harness 的 `[report]` 输出作为业务完成标记，或在短命令下依赖正常退出。

review 后冻结约束不变：不改五门判定函数、不改 CED/T9/health/overdue 口径、不用诊断 DB 做终判样本。

---

## 冻结验收口径（引用 172b §1.1）

终判 = 同时满足 B 组六条判据：

| 判据 | 口径 | sci-fi Ch1-100 基线（冻结） |
|---|---|---|
| B1 完成度 | Ch1-Ch100 全 accepted；gap≤1 走 documented-isolate 复核 | 100/100 |
| B2 上下文预算 | `budget_used` 峰值 < 1.0；无 `context_emergency_budget_ratio_halt` | 峰值 0.989 |
| B3 一致性 CED | consistency-only、merged/source、正文证据口径；≤ sci-fi 同章尺度 × 1.15 | Ch25 9.33 / Ch50 9.28 / Ch75 9.46 / Ch100 9.13 |
| B4 伏笔回收 | overdue ≤ sci-fi 同章尺度；不套用短窗口 `<5` | Ch25 61 / Ch50 110 / Ch75 136 / Ch100 168 |
| B5 连续性健康 | health ≥ 8.0（latest 非 None），median 不持续退化 | Ch25 9.2 / Ch50 9.4 / Ch75 9.9 / Ch100 10.0 |
| B6 文本洁净 | T9 = 0；无 Markdown 泄漏、无段落重复、无 AI 保护指令混入 | 0 |

**口径守护**：

- CED 只统计 consistency 类 issue，不计文学 craft 或 `rule-mr-*` 聚合项。
- T9 不接受解释性豁免；PASS 样本必须 clean rerun 后 T9=0。
- overdue 在 Ch100 尺度对标 sci-fi 同章，不套用 185 短窗口的 3 条。

---

## 分段爬坡计划

复用 `scripts/run_172b_ch100_climb.py`，每 25 章为一段（arc 边界），段边界做正式五门审计：

```
段1 Ch1-25   → 五门审计 → 全 PASS 才进段2
段2 Ch26-50  → 五门审计 → 全 PASS 才进段3
段3 Ch51-75  → 五门审计 → 全 PASS 才进段4
段4 Ch76-100 → 五门审计 → 出 Ch100 终判报告
```

每段结束收集：

- `continuity_reports`：CED、overdue、health、orphan/critical 计数。
- `context_snapshots`：budget 峰值、emergency 次数、before_emergency 峰值。
- `foreshadowings`：plant/resolve/archive 分布、expected horizon 分布。
- `review_reports`：规则/语义 issue 类型分布、修订轮数。

任一 FAIL 触发冻结：记录当前 DB、run_id、段号、五门明细 → 路由 `187.p` 定点修复 → 机制修复后从该段起点 clean rerun。

---

## 撞墙路由表（187.p/q/r/s…）

| 风险墙 | 触发信号 | 正确杠杆（禁止行为） |
|---|---|---|
| **预算墙** | Ch50+ `budget_used` 逼近 1.0 或触发 `context_emergency_budget_ratio_halt` | 抬 `base_budget`（185 初值 12000；187.p 已升至 14000；若 Ch50+ 仍吃紧再 review 是否升至 15000）；**禁止调分区权重** |
| **CED 墙** | 某段 CED > sci-fi 同段 × 1.15 | 定点修复 CED 热点章（多轮修订章、issue 计数最高者）；**禁止放宽 tolerance、禁止改 CED 口径** |
| **overdue 墙** | Ch100 overdue > sci-fi 同章（>168）或某段 resolved=0 且 plant 密集 | **先查 resolve 机制是否生效**，再评估 `foreshadowing_horizon_floor`；禁止直接调 floor 掩盖 resolve 失效 |
| **health 墙** | health < 8.0 或 median 持续退化 | 定点诊断连续性报告，判定真退化则修健康权重或回收调度；**禁止放宽 health 阈值** |
| **T9 墙** | 任一段 clean rerun 后 T9 > 0 | 冻结样本，定点修 text cleanliness / urban writer_rules；**禁止解释性豁免** |
| **完成度墙** | 单章 isolate 或 gap>1 | 复核是否为系统性失败；非系统性 isolate 可记录后继续；系统性失败停跑修机制 |

---

## 执行方案（准入 Task 187）

### 阶段 A：任务书评审（本 Task 186）

- 本任务书评审通过为 Task 187 开跑硬门槛。
- 评审重点：冻结口径是否对齐 172b §1.1、撞墙路由表是否覆盖 urban 已知风险、分段计划是否合理。

### 阶段 B：环境准备

```powershell
$env:TEMPLATE_ID = "urban"
$env:RUN_ID = "187"
$env:CHECKPOINTER_MODE = "sqlite"
$env:SONGYAN_RUN_COST_BUDGET = "25.0"   # 按 185 单章 ¥0.116 × 100 章 + 余量
```

- 爬坡 harness 固定写入：
  - DB：`.tmp/task172b_urban_ch100.db`
  - project 文件：`.tmp/task172b_urban_project.json`
  - 分段 metrics：`.tmp/task172b_urban_segments.jsonl`
  - 报告：`docs/reports/187-urban-ch100-climb.md`
- 确认 `songyan profile show --genre urban` 的 source=registry、base_budget=14000、floor=0。若需检查目标 DB 的 override，临时设置 `$env:DATABASE_URL = "sqlite:///.tmp/task172b_urban_ch100.db"` 后再运行该命令；不要期待 `DATABASE_URL` 改变爬坡 harness 的库路径。
- 确认 harness 资源、wrapper、成本熔断已就位。

### 阶段 C：分段爬坡（Task 187）

```powershell
# 初始化项目
python scripts/run_172b_ch100_climb.py --init

# 分段推进
python scripts/run_172b_ch100_climb.py --to 25
python scripts/run_172b_ch100_climb.py --to 50
python scripts/run_172b_ch100_climb.py --to 75
python scripts/run_172b_ch100_climb.py --to 100
```

每段用 wrapper 防卡：

```powershell
powershell -NoProfile -File scripts\run_with_timeout.ps1 -TimeoutSec 5400 -SuccessMarkerRegex "\[report\]" -- python scripts\run_172b_ch100_climb.py --to <n>
```

### 阶段 D：段边界审计

先读取 project id：

```powershell
$db = ".tmp/task172b_urban_ch100.db"
$projectInfo = Get-Content .tmp/task172b_urban_project.json | ConvertFrom-Json
$projectId = $projectInfo.project_id
```

每段结束后运行：

```powershell
python scripts/five_gate_check.py --genre urban --db $db --project-id $projectId --up-to <n> --format json > .tmp/187_seg<n>_five_gate.json
python scripts/segment_audit.py --db $db --project-id $projectId --up-to <n> --format json > .tmp/187_seg<n>_audit.json
```

五门结果与 172b 的 `.tmp/vdim_compare.py` 口径对照，确保无漂移。

### 阶段 E：终判与归档

- Ch100 终判报告落盘 `.tmp/187_urban_ch100_final.json`。
- Task 187 执行记录单独落到 `tasks/187-urban-ch100-climb-execution.md`，完成后改为 `*-DONE.md`。
- V9 收口时统一归档到 `archive/v9/`。
- 更新 `docs/STATUS.md`、`tasks/V9-README.md`、`docs/INDEX.md`、`README.md`。

---

## 验收判据

- 本任务书评审通过。
- Task 187 执行后同时满足：
  - Ch1-Ch100 全 accepted（gap≤1 可复核）；
  - `budget_used` 峰值 < 1.0，无 `context_emergency_budget_ratio_halt`；
  - CED ≤ sci-fi 同章尺度 × 1.15；
  - overdue ≤ sci-fi 同章尺度；
  - health ≥ 8.0；
  - T9 = 0。
- 五门工具与段审计输出落盘，与 xuanhuan/wuxia Ch100 重放口径一致。
- 全量 pytest、CLI pytest、mypy、ruff 在文档更新后仍绿（聚焦测试 + CLI 已绿即可作为中间证据）。

---

## Out of Scope

- urban Ch100 之后的 Ch150/Ch200 验证（归 V10）。
- 新增体裁或创作模式。
- 优秀度信号包、风格卡、中文 AI 腔规则包。
- GateConfig 构建时序重构、DB 稀疏覆盖存储。
- 小说特化微调或多 agent 仿真生成。

---

## 风险与纪律

| 风险 | 对策 |
|---|---|
| API 成本：Ch100 实跑约 ¥12-15 | 185 已成本标定；187 用 `SONGYAN_RUN_COST_BUDGET` 熔断；分段跑、段边界早停不烧后续章节 |
| 进程退出挂死 | 173 已修复；所有实跑走 wrapper；跑完核对进程状态 |
| urban 现代设定一致性出 CED 热点 | 172b 纪律：热点章定点修复，不放宽 CED 口径 |
| overdue 在长窗口失控 | 先查 resolve 机制，再评估 floor；禁止直接调 floor |
| 185 标定值在 Ch100 不够 | 187.p 已将 base_budget 从 12000 抬到 14000；若后续仍触发预算墙，再 review 是否升至 15000；不碰分区权重 |
| 段边界五门工具口径漂移 | 以 xuanhuan/wuxia Ch100 DB 重放为基线，判定函数不改 |

---

## 文档入口

- V9 总索引：`tasks/V9-README.md`
- 185 前置证据：`tasks/185-urban-short-window-calibration-DONE.md`
- 冻结口径参照：`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1
- xuanhuan Ch100 报告：`archive/v8/reports/172b-xuanhuan-ch100-climb.md`
- wuxia Ch100 报告：`archive/v8/reports/172c-wuxia-ch100-climb.md`
- 五门工具：`scripts/five_gate_check.py`、`scripts/segment_audit.py`
- 爬坡 harness：`scripts/run_172b_ch100_climb.py`
