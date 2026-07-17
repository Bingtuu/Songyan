# V8 Task 总索引

> **阶段**: 多体裁可插拔质量 → 多体裁章数爬坡（P/C/Q/S/V 五维验收完成）
> **当前口径**: V7 在 sci-fi 单一体裁下达成 Ch200 后收尾。V8 的目标不是再做一轮类似 Task 170 的"文学性提分 prompt 工程"，而是把支撑 sci-fi 长跑的**工程底盘**（Context Diet 2.0、门禁、结算、连续性审计）以及**既有文学护栏**从科幻隐式画像解耦——运行时契约建立 `GenreRuntimeProfile`（层 2），文学护栏 lexicon/主角名参数化到 `GenreProfile`（层 3，Task 172d），让 xuanhuan/wuxia/urban 等体裁达到与 sci-fi **同等的完成度和质量基线**，再向中篇（Ch100/Ch150）爬坡。  
> **任务编号**: V8 从 Task 172 开始；编号是 trace id，不等同于严格执行顺序。原 V7 Task 172（Ch250）已取消并归档，V8 复用 172 作为项目模板化入口。
> **最后整理**: 2026-07-17（172c.r 代码修复完成：resolve 失效四层根因全修——prompt card 1.0.4 补 resolve 契约、settlement 事实源纳 overdue、resolve 防幻觉校验、5.3 同事务覆写修复；health 口径对齐 vdim 三层漏计全修；12 新测试 + 全量 2779 passed + ruff 全绿；scifi/wuxia 实跑回归中断待重跑，通过后写 DONE 并做存量 DB 处置决策）

本文是 V8 阶段任务文档的事实入口。V7 历史事实入口见 `tasks/V7-README.md`；V6 见 `tasks/V6-README.md`；V5 见 `tasks/V5-README.md`；历史规划稿统一归档到 `archive/`，仅在追溯设计边界时查阅。

---

## 一句话目标

> **V8 让系统从"只会写科幻"变成"每个体裁都能写到科幻的质量水位**。核心抓手是 `GenreRuntimeProfile`：把 Context Diet 2.0 的预算分配、门禁阈值、状态压缩、伏笔蒸发等运行时契约从 sci-fi 默认值中解耦，使玄幻、武侠、都市等体裁在 accepted 率、文本洁净、事实一致性、连续性、health 等维度上达到与 sci-fi 同等的基线，再逐步把验证窗口从短章拉向中篇。**

---

## 阶段验收判定

V8 通过 = 同时满足以下五项：

| 维度 | 判据 |
|------|------|
| **P（可插拔）** | `GenreRuntimeProfile` 机制可插拔：新增体裁只需新增 Profile 文件/记录，不修改核心逻辑；无 Profile 体裁 100% 回退旧行为 |
| **C（完成度）** | xuanhuan/wuxia/urban 短窗口验证 accepted 率达到 sci-fi 同级：**--end 10 全 accepted，--end 15 全 accepted，--end 20 gap ≤1 且有明确 isolate 记录** |
| **Q（质量同标）** | 各体裁短窗口质量指标对齐 sci-fi 基线：T9 hard issue = 0；ContextEmergency 不连续触发；budget_used 峰值 < 1.0；health 不持续退化；连续性审计 critical mismatch = 0；**一致性错误密度 CED ≤ sci-fi 同级**。**CED 只计入体裁中性的带证据 issue**（live 门禁如 `check_supporting_character_goal_presence` 是体裁中性的，按配角名判定，计入）；文学 observe 路径（`observe_active_choice` 等）当前科幻硬编码，**在 172d 落地前不计入 CED、也不作为验收依据**（否则 xuanhuan 会因找不到"林渊/按下"而假失败） |
| **S（状态可控）** | xuanhuan end 15/20 中 overdue foreshadowing < 5（基线 13），伏笔回收链不崩；角色/设定状态膨胀受控 |
| **V（中篇爬坡）** | 至少一个非 sci-fi 体裁稳定推进到 Ch100，且前 100 章质量指标不劣于 sci-fi Ch1-Ch100 基线 |

### 当前验收状态（2026-07-15）

| 维度 | 状态 | 当前证据 |
|------|:----:|----------|
| P | ✅ PASS | `GenreRuntimeProfile` 已可插拔；scifi profile 全默认回退旧行为，无 profile 体裁保持旧路径 |
| C | ✅ PASS | scifi/wuxia/urban `--end 10` 全 accepted；xuanhuan `--end 15` 已通过 isolate 复核 |
| Q | ✅ PASS | 短窗口 T9=0、budget<1.0；Ch100 consistency CED：xuanhuan 0.4434 ≤ sci-fi 0.3976 ×1.15 |
| S | ✅ PASS（172b 终判） | xuanhuan Ch100 overdue 166 ≤ sci-fi Ch100 168；172b.p 证明 `foreshadowing_horizon_floor=48` 长窗口有效。**172c wuxia 段 3 发现深层缺陷**：Ch75 vdim overdue=203， SettlementExtractor 伏笔 resolve 机制完全失效（wuxia/xuanhuan 均为 0 resolved） |
| V | ✅ PASS（172b 终判） | xuanhuan Ch1-Ch100 100/100 accepted，budget / CED / overdue / health / completeness 五门全 PASS。172c wuxia 仅到 Ch75，且 CED/overdue/health 三门外，尚未闭合 |

V8 当前完成判据已满足。172c（wuxia 第二体裁 Ch100）保留为 V8-pass 后续增强，用于扩展多体裁长窗口佐证，不回溯性阻塞本次 V8 完成判定。

**V8-pass 后技术债（已清零）**：`GenreRuntimeProfile` 中 `partition_ratios`、`max_*`、`hard_enforce_ratio`、`setting_evaporation`、`character_decay.dormant_window`、`continuity.*` 等声明后未接线字段已由 172e-172i 全部接到消费者；`load_profile()` 语义已澄清为注册表基线 + DB 字段级覆盖层；占位字段 `arc_summarization_enabled` / `outline_dimming_enabled` / `mismatch_tolerance` 已移除。

### 外部调研支撑

长调研报告见 `docs/reports/v8-literature-and-landscape-review.md`。核心结论：

1. **体裁差异本质上是状态动力学差异**（CreAgentive、DOME、ConStory-Bench 共同支持），不存在单一上下文策略能覆盖所有体裁。
2. **GenreRuntimeProfile 与外部最佳实践一致**：CreAgentive 的 genre-agnostic Story Prototype + style realization 解耦、AI Dungeon/NovelAI 的 Memory/Lorebook、DOME 的 hierarchical outline + memory weights 都指向“运行时按体裁定制上下文”是必然的工程路径。
3. **一致性评估需要专用密度指标**：ConStory-Bench 的 Consistency Error Density (CED) 可跨体裁公平比较，V8 应将其纳入验收。
4. **sci-fi baseline 必须显式化**：V7 的成功依赖于一组未文档化的默认参数，V8 第一步应把当前默认值固化为 `scifi` profile，避免后续调参回退旧行为。

---

## Task 状态

> 状态口径：`◻ 规划中`（有规划稿，未开工）/ `🔄 进行中` / `✅ 完成`（有 `*-DONE.md`）/ `⚠️ 条件完成` / `⚠️ 条件未通过` / `⏳ 占位`（骨架占位，详细文档待前置数据出炉后写）。

### Task 编号治理（2026-07-15 起）

为避免把编号误读成执行顺序，V8 后续按以下规则维护任务事实源：

1. **编号是追踪 ID，不是依赖顺序**：真实执行顺序以本文的依赖图与各任务前置条件为准。例如 `172d` 编号晚于 `172c`，但它是 `172a.7` 的硬前置，必须在 Ch100 爬坡前完成。
2. **阶段任务与事故修复分层展示**：`172` / `172a` / `172b` / `172c` / `172d` 是阶段或工作包；`172a.p`、`172b.p`、`172b.q` 是父任务下的撞墙定点修复，不与主线阶段并列排序。
3. **字母后缀只在父任务内有序**：`172b.p`、`172b.q` 表示 172b 中按发现顺序产生的修复项，不表示它们晚于 `172c` 或 `172d`。
4. **后续增强必须先补任务文档**：启动 `172c` 前必须先补 `tasks/172c-*.md`，明确目标、前置证据、分段验收和撞墙路由；不能直接从占位行开跑。
5. **不为治理本身新增数字任务号**：文档治理结论内嵌在 `tasks/V8-README.md`，避免再制造新的编号噪音。

以下表格按**事实层级与依赖关系**排列，而不是按编号字母顺序排列。

### V8.0：项目模板化与体裁可插拔（ProjectTemplate）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172 | 项目模板化与体裁可插拔 | ✅ 完成 | `tasks/172-project-template-plugin-DONE.md` |
| 172-TEST | 合并到 main 门槛值与测试计划 | ✅ 完成 | `tasks/172-project-template-plugin-TEST-PLAN.md` |
| 172-PLAN | 实施计划 | ✅ 完成 | `docs/superpowers/plans/2026-07-13-project-template-plugin-plan.md` |

### V8.1：体裁运行时画像（GenreRuntimeProfile）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172a | 体裁运行时画像总览 | ✅ 完成 | `tasks/172a-v8-genre-runtime-profiles.md` |
| 172a.1 | 现状审计与常量提取 | ✅ 完成 | `docs/reports/172a.1-context-diet-constants-audit.md` |
| 172a.2 | `GenreRuntimeProfile` 数据模型 + 数据库表 | ✅ 完成 | 172a 规划 §172a.2 |
| 172a.3 | 按体裁加载 Profile | ✅ 完成 | 172a 规划 §172a.3 |
| 172a.4 | Context Diet 预算分配按体裁 | ✅ 完成 | `docs/reports/172a.4-budget-decoupling-validation.md` |
| 172a.5 | 硬门禁阈值按体裁 | ✅ 完成 | 172a 规划 §172a.5 |
| 172a.6 | 状态压缩与伏笔蒸发按体裁 | ✅ 完成 | 172a 规划 §172a.6 |
| 172a.7 | 多体裁短窗口验证 | ✅ 完成 | `docs/reports/172a.7-genre-short-window-validation.md` |
| 172a.p | 伏笔 horizon 下限（S 维度定点修复） | ✅ 完成 | `tasks/172a.p-foreshadowing-horizon-floor.md` |

### V8.3：文学护栏跨体裁化（GenreProfile 层 3，172a.7 硬前置）

> 说明：`172d` 编号保留为历史 trace id；按依赖它应阅读在 `172b/172c` 之前。

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172d | 文学护栏 lexicon + 主角名跨体裁化 | ✅ 完成 | `tasks/172d-cross-genre-literary-guardrails-DONE.md` |

> **172d 定位**：把 `literary_guardrail_observe.py` 的科幻硬编码（`protagonist_name="林渊"` + 5 组主动选择/配角/代价 lexicon）参数化——主角名从 `protagonist_profile` 读取，lexicon 迁入 `GenreProfile` 并为 xuanhuan/wuxia/urban 各配一套，无 profile 回退科幻组。**172d 必须先于 172a.7 落地**：172a.7 的多体裁短窗口质量报告正是用文学 observe 路径渲染的，不修 172d 则 xuanhuan 报告会因找不到"林渊/按下"而每章判 MISSING，验收报告失真。

### V8.2：多体裁章数爬坡（主线与后续增强）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172b | 非 sci-fi 体裁 Ch100 爬坡验证（首选：xuanhuan） | ✅ 完成 | `tasks/172b-xuanhuan-ch100-climb.md` |
| 172c | 第二个非 sci-fi 体裁 Ch100 爬坡验证（候选：wuxia） | 🔄 进行中 | `tasks/172c-wuxia-ch100-climb.md` |

#### 172c 撞墙定点修复（从属于 172c，不是独立阶段）

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172c.p | wuxia forgotten_items 物品追踪粒度修复 | ✅ 完成 | `tasks/172c.p-wuxia-forgotten-inventory-tracking.md` |
| 172c.q | wuxia 物品追踪语义补强（变体归一 / 非物品过滤 / 消耗流转） | ✅ 完成 | `tasks/172c.q-wuxia-inventory-identity.md` |
| 172c.r | wuxia 伏笔回收与 continuity 健康度修复 | 🔄 进行中 | `tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix.md` |

> 172c 实跑段 3 后暴露两个设计缺陷，已按证据新建 `172c.r`；`172c.p`/`172c.q` 是 172c 内部按发现顺序产生的物品追踪修复，不影响 172c 主线状态。

---

### V8.4：运行时契约补完（V8-pass 后技术债）

> V8 验收时发现 `GenreRuntimeProfile` 大量字段声明后未接线。172e-172i 是 V8-pass 后补完接线与文档的技术债清理，不阻塞 V8 完成判定，但阻塞 V9 按体裁深度调参。**2026-07-15 已全部完成，技术债清零。**

| Task | 名称 | 状态 | 事实文档 |
|------|------|:----:|----------|
| 172e | ContextManager / BudgetPruner 字段接线 | ✅ 完成 | `tasks/172e-context-manager-profile-wiring.md` |
| 172f | SettingEvaporator / 伏笔排序字段接线 | ✅ 完成 | `tasks/172f-evaporation-profile-wiring.md` |
| 172g | 角色归档窗口字段接线 | ✅ 完成 | `tasks/172g-character-decay-profile-wiring.md` |
| 172h | 连续性审计字段接线 + 消除重复常量 | ✅ 完成 | `tasks/172h-continuity-profile-wiring.md` |
| 172i | Profile 回退语义澄清 + V8 文档修复 | ✅ 完成 | `tasks/172i-profile-fallback-semantics-and-docs.md` |

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

### 172c wuxia 中篇现状（2026-07-16）

| 指标 | 段 1 Ch1-25 | 段 2 Ch26-50 | 段 3 Ch51-75 |
|---|---|---|---|
| accepted | 25/25 | 25/25 | 25/25 |
| 0 halt | ✅ | ✅ | ✅ |
| budget_used_peak | 0.995 | — | 0.995 |
| CED/1k (vdim) | 0.49 | — | 0.47 |
| overdue_foreshadowing (vdim) | 32 | — | **203** |
| health_latest | 3.0 → 7.2 | 5.6-7.8 | 5.3-6.0 |
| 五门 verdict @Ch75 | — | — | budget/completeness PASS；CED/overdue/health FAIL |

**关键发现**：
- wuxia 与 xuanhuan 的 `foreshadowing` 记录中 **`resolved` 数量均为 0**：每章平均埋 3-4 个伏笔，但 SettlementExtractor 从未成功 resolve。
- `continuity_auditor` health 公式使用 `ForeshadowingRepository.list_active()`，只统计 `lifecycle_status=active` 且 `status IN ('planted','due')` 的伏笔； overdue 被 `archive_overdue()` 归档到 `dormant`/`archived` 后，health 公式不再计入，导致 health 5.6 但 vdim 统计到 203 个 overdue 的割裂。
- `foreshadowing_horizon_floor`（wuxia=12，xuanhuan=48）只是把逾期推后，不能替代 resolve 机制。

### sci-fi 对比基线（V8 目标水位）

| 指标 | sci-fi Ch200 |
|---|---|
| accepted | 200/200（100%） |
| T9 hard issue | 0 |
| ContextEmergency | 偶发，不连续 |
| budget_used | 长期 <1.0 |
| health | median ≥8.5，无连续真实退化 |
| critical orphan | 0 |

### sci-fi Ch1-100 逐段基线（172b V 维度对标口径，冻结）

从 V7 实跑 DB `.tmp/task171_ch1_ch200.db`（「轨道蜃景」，220/220 accepted）用 172b harness 同一 `_segment_metrics` 方法（issue 按 `chapter_number <= up_to` 界定）提取，落盘 `.tmp/scifi_ch100_baseline.json`：

| checkpoint | budget_peak | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|
| Ch25 | 0.989 | 61 | 9.2 | 9.33 |
| Ch50 | 0.989 | 110 | 9.4 | 9.28 |
| Ch75 | 0.989 | 136 | 9.9 | 9.46 |
| Ch100 | 0.989 | 168 | 10.0 | 9.13 |

> **关键口径**：sci-fi 自身 Ch100 overdue=168（未完结长篇天然携带大量 open thread），CED 稳定 9.13-9.46。172b 判 V 维度用**此 Ch100 尺度**（xuanhuan overdue ≤168、CED ≤ 同级、budget<1.0），**不套用 S 维度 end15 的 `<5`**（短窗口口径）。详见 `tasks/172b-xuanhuan-ch100-climb.md` §1.1。

**V8 的完成标准**：非 sci-fi 体裁在对应窗口内，accepted 率与质量指标必须达到 sci-fi 同级，而不只是"能跑完"。

---

## 技术方案概要

### 核心抽象：GenreRuntimeProfile

`GenreRuntimeProfile` 是 Context Diet 2.0 的运行时契约，每个体裁拥有独立配置。V8 验收时已完成核心杠杆接线；剩余声明后未接线字段已由 172e-172i 全部接线或移除（见下）。

**已接线（V8 验收完成）**：

- **上下文预算**：`base_budget` / `ramp_per_chapter` / `min_budget` 已接入 `ContextManager.dynamic_budget()`；xuanhuan base_budget=15000 解决 Ch8 halt。
- **伏笔 horizon 下限**：`foreshadowing_horizon_floor` 已接入 `SettlementExtractor`；xuanhuan floor=48 保证 Ch100 overdue 受控。
- **halt 门禁阈值**：`emergency_halt_ratio` 已接入 `phase2_graph.py`，在 genre 已知后覆盖 `GateConfig`。
- **角色档案 focal gaps**：`character_decay.focal_gaps` 已接入 `_resolve_profile_level()`，控制角色档案加载密度。

**已接线（172e-172i 完成）**：

- **可裁分区比例/硬上限**：`partition_ratios`、`max_soft_refs`、`max_foreshadowing`、`max_character_states`、`max_setting_input` 已接入 `BudgetPruner`（172e）。
- **核裁/emergency 触发阈值**：`hard_enforce_ratio`、`context_emergency_trigger_ratio` 已替换 `HARD_ENFORCE_THRESHOLD=1.3` 与硬编码 `budget_used > 1.0`（172e）。
- **状态蒸发曲线**：`setting_evaporation`、`foreshadowing_evaporation` 已接入 `SettingEvaporator` 与 `_rank_foreshadowings`（172f）。
- **角色生命周期归档窗口**：`character_decay.dormant_window` / `archive_window` / `functional_window` 已接入 `CharacterStateRepository`，替换硬编码 30/60（172g）。
- **连续性审计容差**：`continuity.forgotten_threshold` / `state_mismatch_window` / `orphaned_thresholds` 已接入 `_scanners.py`，消除重复常量（172h）。
- **占位字段移除**：`arc_summarization_enabled`、`outline_dimming_enabled`（172i）、`mismatch_tolerance`（172h）已从模型删除。
> **根因修正（三轮审计结论）**：xuanhuan Ch8 被 halt 时，动态预算仅 `8000 + 8×250 = 10,000` token，`budget_used_before_emergency=1.4019` 是**核裁之后**测得的残值（`_context_emergency` 在 `_enforce_budget_hard` 之后运行）。核裁与 emergency **从不裁剪** `hard_constraints / genre_rules / mode_rules / chapter_goal`，所以 1.40 残值几乎全是**不可裁核心**。因此**调整分区权重（character_states/recent_plot/soft_references/foreshadowing 之间的比例）无法压下溢出**——溢出发生在不可裁核心。真正的杠杆是：**(a) 抬高 base budget / 爬坡起点**、**(b) 缩短 xuanhuan genre_rules 内容本身（层 3 内容编辑）**、**(c) 抬 halt 阈值**。

加载顺序（172i 最终语义）：

```
project.genre
    → 代码默认注册表取体裁基线（含 V8 实证调校）
        → 未知体裁：回退 scifi baseline
    → 查 SQLite genre_runtime_profiles
        → 命中：DB 字段级覆盖注册表基线；未提供/与默认值相同的字段保留基线值
        → 未命中：返回注册表基线
        → DB 异常：返回注册表基线，不阻断生成
```

每个项目记录 `runtime_profile_id` + `runtime_profile_snapshot`，保证可审计。

### 注入点

**已注入（V8 验收完成）**：

- `ContextManager` 动态预算（`_dynamic_budget` base/ramp；`assemble_context_package()` 按 genre 加载 profile）。
- `SettlementExtractor` 伏笔 horizon 下限（`_clamp_foreshadowing_horizon()`）。
- `phase2_graph.py` halt 阈值覆盖（`emergency_halt_ratio` → `GateConfig.context_emergency_budget_ratio_threshold`）。
- `_resolve_profile_level()` 角色 focal gaps（`character_decay.focal_gaps`）。
- `literary_guardrail_observe.py` lexicon + 主角名（172d，层 3）。

**已注入（172i 完成）**：

- `load_profile()` DB/注册表回退语义：代码注册表为基线，DB 为字段级覆盖层；DB 未命中/异常时回退注册表；未知体裁回退 scifi baseline。

**已注入（172e-172h 完成）**：

- `BudgetPruner._apply_partition_budgets` / `_prune_*` 分区比例与硬上限（172e）。
- `BudgetPruner._enforce_budget_hard` 核裁阈值 + `_context_emergency` 触发比例（172e）。
- `SettingEvaporator._calculate_resolve_confidence` 蒸发曲线（172f）。
- `_rank_foreshadowings` 伏笔紧迫性权重（172f）。
- `CharacterStateRepository.archive_stale` / `archive_very_stale` 归档窗口（172g）。
- `continuity_auditor/_scanners.py` forgotten / state_mismatch / orphaned 三处容差（172h）。

**已知设计缺陷**：

- 门禁服务 `GateConfig` 构建时序：当前 `cli/main.py:521` 在 genre 已知前就构建了全局 `GateConfig`，`phase2_graph.py` 只能在运行时逐个字段覆盖。后续重构候选：genre 已知后统一构造（不阻塞 V9 调参，172e-172i 未动此路径）。
- ~~角色衰减劈裂~~：已由 172g 统一——`dormant_window` / `archive_window` / `functional_window` 已接入 `CharacterStateRepository`，与 `_resolve_profile_level()` 的 `focal_gaps` 同属 `character_decay` profile。
- **SettlementExtractor 伏笔 resolve 机制失效（172c 段 3 发现；172c.r 修复已落地，待实跑回归）**：wuxia 75 章、xuanhuan 100 章的 `foreshadowings.status='resolved'` 数量均为 0。172c.r 诊断+TDD 确认**四层根因**：A. prompt card 1.0.3 只演示 `plant`；B. `resolved_hooks` 自由文本成为不回写 DB 的替代出口；C. `list_active()` 把 overdue 伏笔从 settlement prompt 事实源滤除；D. `_update_continuity_tracking` 5.3 自动状态机独立连接陈旧读，把同事务内刚 resolve 的伏笔当场翻回 overdue。四层已全部修复（详见 `tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix.md` §2.1/§3.1）。
- **continuity_auditor health 漏计 overdue（172c 段 3 发现；172c.r 修复已落地，待实跑回归）**：`_find_overdue_foreshadowings()` 原用 `list_active()`（`lifecycle_status='active' AND status IN ('planted','due')`），漏计三层：archived overdue、dormant overdue、**active 但 status='overdue'** 的条目（wuxia Ch75 实例 153+36+20），与 vdim 冻结口径（`status != 'resolved'` 无 lifecycle 过滤）完全脱节；已改 `list_overdue_unresolved()` 对齐 vdim 口径（172c.r §3.2）。

### 可插拔与回退

- 新增体裁：新增一个 Profile 记录/文件，不修改核心逻辑。
- 无 Profile 体裁：100% 回退到 scifi 默认行为（即 V7 验证过的行为）。

---

## 依赖关系与执行纪律

```
172 项目模板化 ─────────────────────────────────────────────────────────────────────┐
                                                                                    │
                                                                                    ▼
172a.1 常量审计 ──► 172a.2 模型 ──► 172a.3 加载机制 ──► 172a.4 预算分配 ──► 172a.5 门禁阈值 ──► 172a.6 状态压缩 ──┐
                                                                                                              │
172d 文学护栏跨体裁化（可与 172a.2–172a.6 并行）──────────────────────────────────────────────────────────────┤
                                                                                                              ▼
                                                                                                      172a.7 短窗口验证 + 多体裁质量报告
                                                                                                              │
                                                                                                              ▼
                                                                                                      172b Ch100 爬坡（候选 xuanhuan） ──► 172c 第二体裁 Ch100 爬坡（可选增强）
                                                                                                              │
                                                                                                              ▼
                                                                                                      V8 验收完成（P/C/Q/S/V 五维全绿）
                                                                                                              │
                                                                                                              ▼
                                                                                                      172e-172i 运行时契约补完（V8-pass 后技术债；已全部完成）
```

- **172 是 172a 的前置**：`ProjectTemplate` 为各体裁提供统一的项目初始化入口；`GenreRuntimeProfile` 依赖模板化的项目结构来按 genre 加载运行时参数。
- **172a 串行为主**：Profile 机制是后续所有体裁调参的地基，必须等模型与加载机制落地后才能调预算/阈值/压缩策略。
- **172d 是 172a.7 的硬前置**：172a.7 的多体裁质量报告用文学 observe 路径渲染；172d 未落地则 xuanhuan/wuxia/urban 报告失真。172d 可与 172a.2–172a.6 并行开发（改的是 `GenreProfile` 层，与运行时层解耦），但必须在 172a.7 前合入。
- **预算杠杆是 base_budget/genre_rules 内容，不是分区权重**：溢出在不可裁核心，172a.4 调 base_budget 爬坡起点 + 缩短 genre_rules 内容，不调可裁分区权重比例。
- **不回退 sci-fi**：任何 Profile 改动必须通过 sci-fi `--end 10` 回归，保证旧行为不变。
- **短窗口是对标手段，不是终点**：V8.1 用 end 10/15/20 快速验证各体裁是否能达到 sci-fi 同级质量；通不过不进 172b。
- **质量同标，不放宽口径**：非 sci-fi 体裁的 T9/health/orphan/伏笔回收等硬指标与 sci-fi 使用同一套冻结口径，不因"体裁特殊"而降低验收。
- **Ch100 爬坡后置**：172b 是 V 维度验收闸口（line 28 判据「**至少一个**非 sci-fi 体裁到 Ch100」，即 xuanhuan/172b 达标即闭合 V 维度、V8 五维度全绿）；172c（wuxia 第二体裁）是**已承诺的后续 scope**（强化「多体裁」佐证），在 172b 达标后启动，但 172c 若撞墙不回溯性推翻 V8-pass。二者都必须在 172a.7 证明各体裁短窗口质量达标后才启动。
- **文档纪律**：172a 各子任务在开工前写详细规划；172a.7 完成后必须产出多体裁短窗口质量对标报告；172b/172c 在实跑数据出炉后补齐，避免文档超前返工。

---

## V8 明确不做（划界）

| 项 | 归属 |
|----|------|
| 重复 Task 170 式**文学性 rubric 调优 / prompt 工程**（新增 rubric、重写 Writer prompt 追求文学高分） | V8 不做文学质量提分；文学**内容质量**仍按 V7 三层契约观测，不作为阻塞门 |
| 新增 Agent / Workflow 节点 | V8 只做运行时参数解耦 + 既有护栏参数化，不新增节点 |
| 全自动跨体裁 LLM 改写闭环 | 不做；只调 Context Diet 预算、阈值、压缩策略 + 既有文学护栏 lexicon 参数化 |
| 所有体裁一次验证到 Ch200 | V8 目标先做到短窗口质量同标 + 1-2 体裁 Ch100；Ch200 跨体裁验证划归 V9 或更晚 |
| 多项目并发 / 分布式长跑 | 不做 |
| 继续优化 sci-fi 单一体裁到 Ch250/Ch300 | 已取消，划归 V7 历史目标 |

> **范围澄清（172d 归属）**：既有文学护栏（`literary_guardrail_observe.py`）当前把主角名 `林渊` 与主动选择/配角/代价 lexicon **硬编码为科幻形状**。将其**参数化为按体裁可插拔**（主角名从 `protagonist_profile` 读取、lexicon 迁入 `GenreProfile`）**属于 V8 范围**（Task 172d，风格实现层解耦），与"重做 Task 170 式文学提分"是两回事——前者是让既有护栏在非科幻体裁不失真，后者是追求更高文学分。V8 只做前者。

---

## 文档入口

- V8 任务事实：`tasks/V8-README.md`
- Task 172 完成报告：`tasks/172-project-template-plugin-DONE.md`
- Task 172 测试计划：`tasks/172-project-template-plugin-TEST-PLAN.md`
- V8 P0 详细规划：`tasks/172a-v8-genre-runtime-profiles.md`
- V8 文学护栏跨体裁化：`tasks/172d-cross-genre-literary-guardrails-DONE.md`
- V8 xuanhuan Ch100 爬坡：`tasks/172b-xuanhuan-ch100-climb.md`
- V8 wuxia Ch100 爬坡（进行中）：`tasks/172c-wuxia-ch100-climb.md`
- V8 wuxia 物品追踪修复：`tasks/172c.p-wuxia-forgotten-inventory-tracking.md`
- V8 wuxia 物品身份语义补强：`tasks/172c.q-wuxia-inventory-identity.md`
- V8 wuxia 伏笔回收与 continuity 健康度修复（规划中）：`tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix.md`
- V8 xuanhuan Ch100 报告：`docs/reports/172b-xuanhuan-ch100-climb.md`
- V8 CED 终段修复：`tasks/172b.q-consistency-ced-repair.md`
- V8 运行时契约补完：
  - `tasks/172e-context-manager-profile-wiring.md`
  - `tasks/172f-evaporation-profile-wiring.md`
  - `tasks/172g-character-decay-profile-wiring.md`
  - `tasks/172h-continuity-profile-wiring.md`
  - `tasks/172i-profile-fallback-semantics-and-docs.md`
- V8 长调研报告：`docs/reports/v8-literature-and-landscape-review.md`
- 项目状态：`docs/STATUS.md`
- 文档路由：`docs/INDEX.md`
- V7 历史事实：`tasks/V7-README.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
- 开发规范：`AGENTS.md`
