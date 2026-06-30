# 300 章目标：主要卡点与解决路径分析

> 本文是面向「高质量完成 300 章」长期目标的代码级 gap 分析，作为 V6/V7 规划（`docs/v6-plan.md`、`docs/v7-vision.md`）的论证基础。
> 结论基于对当前主干代码的精读与实跑报告交叉验证，关键断言均标注代码位置。
> 编写时间：2026-06-30。基线：V5.2 进行中，连续性治理管线仅验证到 Ch30（Task 138n）。

---

## 0. 一句话结论

当前架构**能"跑完" 300 章，但不能"高质量"跑完 300 章**。

经过两轮分析，根因分两层。**第一层（生成层）是真正的根**，第二层（治理/工程层）大多是它的下游症状：

- **根因（生成层）**：系统**没有自顶向下的叙事架构**——章节目标是反应式逐章生成的，不存在全书大纲、弧规划或"剧情线索（plot thread）开启-兑现"的前瞻调度结构。所有跨章机制都是"压缩/遗忘"类（分层摘要、设定蒸发、摘要截断）或"反应式审计"类（orphan/overdue 事后扫描），**没有任何"规划/结构"类机制**。详见 §1。
- **下游症状（治理/工程层）**：orphan 累积、文学质量无指标、长程伏笔失效、enforce 不可用——这些在 §2-§6 逐条展开，但其中 §2/§3 在很大程度上是根因的表现，而非独立病灶。

最关键的认知风险是**指标自欺**：Task 138n 的 health 8.5 是被打分公式美化过的数字，它对 P3 orphan 麻木，掩盖了 orphan 绝对总量仍在线性累积的事实。在相信"能撑到 300 章"之前，必须先看 orphan **绝对总数的斜率**，而非只看 health 分。

> **第二轮修订说明（2026-06-30）**：初版把"orphan 源头无限流"列为 P0 根因。复查 GoalPlanner/CreativeDirector/models 后确认，那只是症状——真正的根因是缺叙事架构。本文据此重排了因果与优先级，新增 §1。

---

## 1. 根因（生成层）：缺自顶向下的叙事架构

> 这是第二轮分析新增、并被代码证实的根因。它解释了 §3（orphan）与 §4（质量/伏笔）两个原 P0 为什么会同时存在——它们是同一个缺口的两个表现。

### 1.1 代码证据（已核实）

| 证据 | 位置 | 事实 |
|------|------|------|
| GoalPlanner 的全部历史输入 = 上一章摘要 + 静态设定 | `agents/goal_planner.py`（约 L44-78）+ `goal_planner/1.0.0.yaml` | prompt 变量只有 `chapter_number`、项目静态设定（主角/core_hook/tone/taboos）、genre/mode 规则、`recent_summaries`。**无任何全书大纲/卷纲/弧规划入参** |
| `recent_summaries` 实为上一章 120 字摘要 | `workflows/phase2_graph.py` `_get_previous_summary`（已核实 L53-56） | 只取前一章 `plot_summary` 并**截断到 120 字符** |
| CreativeDirector 无弧级线索概念 | `agents/creative_director/__init__.py`（约 L57-97） | 输入为单章 goal + recent_summaries + 待回收设定；`foreshadowing_due` 由 LLM 当场判断，非来自规划结构 |
| 无前瞻数据模型 | `models/` | **不存在** outline/synopsis/story_plan、plot_thread/storyline/main_plot/progression。仅有 `ArcSummary`/`VolumeSummary`（回顾性文本）与 arc/volume 的"章号百分比边界"空壳 |
| 无 plan→generate→re-plan 闭环 | `arc_summary_generator.py` + `_helpers.py` `load_layered_summaries` | ArcSummary 是对已完成章节的事后聚合，只作为压缩上下文喂给写作端，**不回流到 GoalPlanner** |
| 项目创建不收大纲 | `cli/main.py`（约 L114-163） | 用户只填 title/genre/主角/core_hook/章数；arc_boundaries 仅按百分比自动切章号，无剧情内容 |

### 1.2 因果链

```
缺叙事架构（无全书大纲 / 无弧规划 / 无线索经济 / GoalPlanner 只看上一章 120 字）
        │
        ├─► Writer 反应式逐章发挥，缺"本弧只讲 X、别开新线"的约束
        │       └─► 单章随手抛出大量新 critical 设定后弃用 ──► §3 orphan 累积
        │
        ├─► 没有"主线/弧"这个可度量对象 ──► §4 文学质量无法度量（不是没做指标，是没有对象）
        │
        └─► 伏笔 plant/payoff 由 LLM 当场拍脑袋、无前瞻调度 ──► §4 长程伏笔被动遗忘
```

### 1.3 为什么这改变了优先级

- 初版把"在 settlement 录入处给 `new_settings` 限流"当根治。复查后判定这是**治标**：Writer 仍会在正文里制造无用新概念，限流只是"不记录"，反而让事实库与正文脱节、更不完整。
- 真正的根治是**给系统一根贯穿全书的叙事骨架 + 线索经济**，让章节目标自顶向下派生、让"先兑现已开线索再开新线"成为生成约束。
- 但叙事架构是**较大且有开放性的改造**，不能一步到位。务实路径：**V6 先做最小可用骨架（MVP）+ 度量**，把退化从"无对象、无约束"变成"可见、可控"；完整线索经济闭环放 V7（见 `docs/v6-plan.md` / `docs/v7-vision.md`）。

---

## 2. 验证深度的真实状况（前提）

| 口径 | 实际情况 |
|------|----------|
| 唯一 150/150 全成功证据（`run-a2bed648`） | 跑在 **V5.1 旧管线**，发生在 orphan 治理（138h-138n）**之前** |
| 当前 V5.2 连续性治理管线 | 迄今**只验证到 Ch30** |
| 对 300 章目标的"已验证深度" | 约 **10%**；最关键的事实库治理逻辑只有 **1/10** 被验证 |

V5 自身历史是最强的预测信号：每一次长窗口实跑都撞出新墙（Ch5 → Ch8 → Ch18 → Ch115 → Ch15 enforce）。"一次跑通并验证 300 章"与该系统的全部历史规律相悖。

---

## 3. 症状一：连续性治理——源头无限流，治理端硬上限（下游 P0）

> **定位**：这是 §1 根因的最主要下游表现。Writer 在无叙事约束下随手制造新设定，治理端再被动收拾。以下仍是真实代码缺陷且必须修，但**单独修治理端只能减速、不能止血**，须与 §1 的叙事骨架配合。

### 3.1 现状逻辑链

| 阶段 | 实现位置 | 行为 |
|------|----------|------|
| 引入 | `settlement_extractor/_apply.py` `apply_settlement`（约 L474-498） | `new_settings` **无数量上限** INSERT 进 DB |
| 分类 | `settlement_extractor/_apply.py` `_infer_setting_category`（约 L688-719） | 纯关键词判定，硬编码主角名「林渊」 |
| 判 orphan | `continuity_auditor/_scanners.py`（约 L35-75）+ `db/continuity_repo.py` `find_orphaned`（约 L248-269） | 按沉寂阈值（critical=3 章）扫 `status='active'` 设定 |
| 治理 | `workflows/_helpers.py` `_load_critical_mandatory_references`（约 L484-571） | 把最紧急 critical orphan 注入 Writer 作硬约束 |
| 蒸发 | `setting_evaporator/__init__.py` + `db/continuity_repo.py`（约 L131-187） | 归档 background/technical/historical，**排除 critical/recurring** |

### 3.2 在 300 章处的失效点（已核实代码）

- **MR 上限恒为 12，与章节号无关**（已核实 `_helpers.py:516-517`）：
  ```
  max_mandatory_references = min(max(scenes_count * 2, 6), 12)
  ```
  Task 138m 报告推荐的渐进上限 `min(10, 3 + chapter//10)` **从未被实现**。Ch300 每章最多强化 12 条设定，而活跃 critical 可能有数百条 → 回收速率被钉死，长尾 critical 永远轮不到强化。

- **health_score 对 P3 麻木**（已核实 `continuity_auditor/__init__.py` `_compute_health_score` L161-203）：
  - 扣分权重：critical ×2.0、recurring ×1.0、background ×0.1、technical/historical ×0.05；
  - count>10 用 `10 + sqrt(count-10)` 衰减；`chapter>30` 时全乘 0.5；floor=2.0。
  - 后果：**几百条 P3 orphan 最多把分压到地板 2.0，而 2-3 条 critical 就触底**。这正是 138n "P1 清零分数回 8.5、但 orphan 总数 25 仍在涨" 的数学根源——分数掩盖了总量失控。

- **SettingEvaporator 是降级而非根治**（`continuity_repo.py:131-187`）：归档明确排除 critical/recurring，critical 阈值设计成几乎永不蒸发。归档只是 `active→archived` 移出 orphan 统计，承载的伏笔/呼应被静默丢弃。

- **源头零限流**：全链路没有任何机制限制"每章新引入 critical 设定数"。138m 已实测 Ch22 一章引入 13 个 `ruins.core.*` critical 设定后立即丢弃。

### 3.3 解决路径

| 优先级 | 动作 | 性质 |
|--------|------|------|
| 高 | **（治本，见 §1）叙事骨架约束 Writer"先兑现已开线索再开新线"** | 从源头减少无用 critical 设定的产生 |
| 中 | **录入侧降级而非限流**：单章超额 `new_settings` 标记为候选/低优先，而非丢弃；收紧 `_infer_setting_category`（世界观细节不应是 critical） | 缓解，不让事实库与正文脱节 |
| 中 | **MR 上限自适应**：实现 138m 推荐但未落地的随活跃量上限；排序从"最沉默优先"改为"主线相关性 + 沉默"综合 | 防止强化的 12 条全是无关长尾 |
| 中 | **critical 显式 resolve/作废出口**：剧情交代或标记废弃，而非靠沉寂归档 | 真回收 vs 假归档 |
| 中 | **health_score 增加"orphan 绝对总量"维度**或独立监控曲线 | 反指标自欺 |

> 注：初版把"录入处硬限流"列为高优先根治，本轮下调——它治标。真正的高优先动作是 §1 的叙事骨架。

---

## 4. 症状二：质量评估体系——只测"事实一致"，不测"故事好看"（下游 P0）

> **定位**：这同样是 §1 根因的表现。文学质量"无法度量"的深层原因是**没有可度量的对象**——没有主线/弧结构，"主线推进度""弧级伏笔兑现率"无从计算。补指标的前提是先有结构（§1）。

### 4.1 现状逻辑

- 三个审查器全是**逐章、无跨章状态**：
  - `rule_auditor.py`（代码级：字数/钩子/AI 腔/短段落/markdown 泄漏/`mandatory_reference_missing`）；
  - `llm_auditor.py`（12 维语义审查，critical/major 必须带 evidence）；
  - `literary_auditor.py`（文学诊断）。
- **LiteraryAuditor 结论不进入评分**：`score_aggregator.py:238-239` 只把 `literary_quality_score` 塞进 details，注释明写"不影响主 score"。
- **质量债零累计**：`degraded_accept`、`convergence_failed` 只写单章 state（`_nodes.py` 附近），无跨章计数器。

### 4.2 在 300 章处的失效点

- **无文学质量长期趋势**：`review_repo.py` 没有任何按章节范围回读 literary_observations 的查询。"第 100-200 章人物弧光持续走低"这种退化**没有任何信号**——continuity health 仍可能显示绿色，但"高质量"已崩。
- **长程伏笔无保障**：`expected_resolve_chapter` 由 LLM 自由填、**无上限校验**（`_validate.py` 仅校验"必须 > 当前章"）；逾期 >15 章即被 archive（`settlement_repo.py` 生命周期）。即 **Ch10 埋、Ch250 兑现的长线伏笔，系统会在中途主动"遗忘"它**——这恰恰是长篇最核心的爽点结构。
- **无主线/弧层结构追踪**：只有 `ArcSummary`（文本摘要 + character_arcs 描述，启发式 10 章一弧），没有主线推进度量、弧级质量分、弧级伏笔兑现率。

### 4.3 解决路径

| 优先级 | 动作 |
|--------|------|
| 高 | **（前提，见 §1）先建主线/弧结构**，使"主线推进度""弧级伏笔兑现率"成为可度量对象 |
| 高 | **质量债账本**：跨章累计 degraded_accept / convergence_failed 章数，纳入长窗口 gate 维度 |
| 高 | **文学质量趋势化**：把 character_autonomy / conceptual_idling 入库做滑动窗口趋势，退化超阈值告警 |
| 中 | **长程伏笔生命周期改造**：超长跨度伏笔区别对待，不能用"逾期 15 章归档"一刀切 |

---

## 5. 症状三：运行可靠性——30 小时连续运行未设计（P1）

### 5.1 现状逻辑

- **无真正 resume**：`phase2_graph.py` 每次新建 `run_id`，"续跑" = 用相同章节范围重跑、靠 `ChapterHeadRepository` 跳过 `status=="accepted"` 章。
- LLM 重试：`llm/retry.py` + `client.py`，`max_retries=3` 指数退避，单次 timeout=60s。**无 429/Retry-After 专门处理**，瞬态全包成 LLMError。
- DB：`_run_lifecycle_cleanup` 每章只 archive 不 DELETE，**运行中无 VACUUM**，VACUUM 仅离线脚本。

### 5.2 在 300 章 / 30 小时处的失效点

- **性能外推**：单章平均耗时从 156s（138k）→ 353s（138n，因 revision 轮数增加），约 2.25 倍。按 353s 外推，300 章 ≈ **30 小时**连续运行。
- **默认 `on_failure="abort"`**：任一章硬失败即终止整个 30h run，retry 仅 +1 次。30h 内持续 429 极可能，单阶段失败级联到 abort。
- **续跑只认 accepted**：崩溃时正在写的章会从头重算，旧 LangGraph checkpoint 成孤儿。
- **DB 单调膨胀**：150 章 196MB → 300 章线性翻倍，查询变慢、无运行中回收。

### 5.3 解决路径

- run 级断点续跑 + 429/Retry-After 感知退避 + 全局 LLM 预算/熔断；
- 运行中增量 VACUUM / wal_checkpoint；
- 失败策略从"abort 整批"改为"隔离单章、继续后续、最后汇总"。

---

## 6. 症状四：enforce 门禁不可生产用（P2）

- **enforce 必暴毙**（`_gates.py` + `phase2_graph.py`）：enforce 模式下 `health_low_p1_halt` 无 anomaly_factor，**首个 P1>0 即 halt**；而 138k 实测 Ch30 P1=35。
- **`quality_gate_fail_streak`（连续 3 章 QG=false）是 always-on、不受 gate_mode 控制**——这是 Task 129 在 Ch15 暂停的元凶。
- 当前系统本质是"观测并降级接受"，不是"保证质量"。300 章下大量降级接受会悄悄累积质量债。

### 解决路径

- enforce 门禁自适应化（anomaly-factor 在 enforce 默认启用）；
- 把 always-on 的 streak halt 改为可配置 + 与质量债账本联动；
- 先在度量到位后，再谈 enforce 默认化。

---

## 7. 症状五：题材强耦合（P2，仅当目标含题材泛化时）

所有长窗口验证都在**同一个科幻遗迹题材项目**上做。半硬编码处：

| 位置 | 耦合内容 | 换题材后果 |
|------|----------|-----------|
| `settlement_extractor/_apply.py` `_setting_cluster_canonical`（约 L94-216） | 为科幻项目逐条手写的实例级 canonical 白名单（`E-7θ通道相位节点`等）+ 硬编码 `theta→θ`、`第七→第7` | 设定回收去重退化为零 |
| `settlement_extractor/_validate.py`（约 L22-159） | telemetry/数值 allowlist 是科幻环境读数词表（温度/氧气/相位/角秒/衰减…） | 玄幻"灵力/丹药数量/境界值"不命中 → 数值结算误报 |
| `_apply.py` `_infer_setting_category` + `review_merger.py`（约 L33-35） | 硬编码主角名「林渊」 | 认知豁免/分类失效 |

**换玄幻/都市最先崩的是数值结算**（telemetry allowlist），其次是设定回收去重。题材切换"标称配置驱动（genres/*.json + creative_modes/*.json），实质半硬编码"。

---

## 8. 卡点优先级总表

| 优先级 | 卡点 | 性质 | 是否随章节数放大 |
|--------|------|------|:----------------:|
| **P0（根因）** | 缺自顶向下叙事架构 / 线索经济（§1） | 生成层结构性缺失 | 是 |
| **P0（症状）** | 连续性退化只被压住（§3，根因下游） | 结构性 | 是 |
| **P0（症状）** | 文学质量 / 长程伏笔无指标（§4，根因下游：无可度量对象） | 当前盲区 | 是 |
| **P1** | 缺 50→100→300 渐进式连续运行证据（§2） | 验证深度 | — |
| **P1** | 性能 / 可靠性在 30h 尺度未评估（§5） | 工程 | 是 |
| **P2** | enforce 门禁不可生产用（§6） | 质量保证机制 | 是 |
| **P2** | 单题材、未泛化（§7） | 鲁棒性 | — |

> 关键：§3 和 §4 两个 P0 症状在很大程度上由 §1 根因驱动。只修症状（治理端限流 + 补指标）能减速退化，但无法止血；必须同时引入叙事骨架，才能让"先兑现已开线索再开新线"成为生成约束。

---

## 9. 推进总原则（修订版）

> **结构先行，度量同步，再治末端。**
> 1. **建最小叙事骨架（治本起点，§1）**：全书大纲 / 弧规划 / 线索经济 MVP，让章节目标自顶向下派生。
> 2. **度量同步建立（§3.3/§4.3）**：orphan 绝对量、质量债账本、文学趋势、弧级伏笔兑现率——让退化可见、让骨架效果可判定。
> 3. **再治末端（§3/§5/§6）**：MR 自适应、录入降级、run 级续跑、限流退避、enforce 自适应。
>
> 初版原则是"度量先行→源头限流→工程加固"。本轮修订把"源头限流"上修为"建叙事骨架"，因为限流只是不记录症状、不解决 Writer 为何制造无用设定。**没有骨架，度量也缺少可度量的主线对象。**

阶段拆分见 `docs/v6-plan.md`（V6：叙事骨架 MVP + 度量 + 可靠长跑，验证到 Ch100-150）与 `docs/v7-vision.md`（V7：线索经济闭环 + 满 Ch300 渐进验证）。
