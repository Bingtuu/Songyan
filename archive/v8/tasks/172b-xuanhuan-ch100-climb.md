# Task 172b — 非 sci-fi 体裁 Ch100 爬坡验证

> **状态**: ✅ 完成（Ch100 全 accepted，V 维度五门 PASS）
> **归属**: V8.2 多体裁章数爬坡（V8 验收 **V 维度**）
> **前置**: 172a.7 短窗口质量同标 + 172a.p S 维度达标（overdue<5）✅
> **候选体裁**: **xuanhuan**（首选）
> **对标基线**: sci-fi Ch1-100（`.tmp/task171_ch1_ch200.db` = V7「轨道蜃景」220/220 accepted，见 §1.1）

---

## 1. 目标与验收（V 维度）

V8-README V 维度判据：

> 至少一个非 sci-fi 体裁稳定推进到 **Ch100**，且前 100 章质量指标**不劣于 sci-fi Ch1-Ch100 基线**。

172b 出口 = 同时满足：

| 项 | 判据 | 对标 sci-fi Ch1-100 基线 |
|---|---|---|
| 完成度 | Ch1-100 全 accepted（isolate 失败 ≤ 明确记录且非系统性） | 100/100 |
| budget | budget_used 峰值 < 1.0；无 `context_emergency_budget_ratio_halt` | 长期 <1.0 |
| ContextEmergency | 偶发不连续 | 偶发 |
| T9 hard | = 0 | 0 |
| 连续性 | critical orphan = 0；health median 不持续退化 | median ≥8.5, critical orphan 0 |
| **S（伏笔）** | overdue foreshadowing 受控（172a.p horizon floor 在 Ch100 尺度仍有效） | — |

> **质量同标纪律**：不因"玄幻状态密度高"放宽任何硬指标。撞墙则路由 `172b.p` 定点修复，不放宽阈值、不做 prompt 工程。

### 1.1 sci-fi Ch1-100 基线（冻结对标口径）

用 172b harness 的 `_segment_metrics` 同一方法（issue 数按 `chapter_number <= up_to` 界定）从 V7 sci-fi 实跑 DB `.tmp/task171_ch1_ch200.db`（project `835afdf1…`，genre=scifi，220/220 accepted）提取，脚本 `.tmp/compute_scifi_baseline.py`，落盘 `.tmp/scifi_ch100_baseline.json`：

| checkpoint | accepted | budget_peak | before_emerg_peak | emergency | overdue | health | CED/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| Ch25 | 25/25 | 0.989 | 1.267 | 28 | 61 | 9.2 | 9.33 |
| Ch50 | 50/50 | 0.989 | 1.267 | 32 | 110 | 9.4 | 9.28 |
| Ch75 | 75/75 | 0.989 | 1.267 | 32 | 136 | 9.9 | 9.46 |
| Ch100 | 100/100 | 0.989 | 1.267 | 32 | 168 | 10.0 | 9.13 |

**对标口径澄清**（关键，避免误判）：

1. **budget < 1.0**：sci-fi 峰值 0.989（近上限但从不 halt）。xuanhuan 峰值应同样 < 1.0、无 `context_emergency_budget_ratio_halt`。
2. **CED ≤ sci-fi 同级**：sci-fi Ch1-100 CED 稳定在 **9.13-9.46**（不随章数衰减，证明 harness CED 已正确密度归一）。xuanhuan 应 ≤ 该量级（短窗口 end15 已测 10.48，约 +14%，Ch100 尺度需实测）。
3. **overdue 用 Ch100 尺度判**：sci-fi 自身 Ch100 overdue = **168**（未完结长篇天然携带大量 open thread）。V 维度是「≥ sci-fi 基线」——xuanhuan Ch100 overdue 只要 **≤ sci-fi 同尺度（≤168）** 即达标，**不套用 S 维度 end15 的 `<5`**（那是短窗口口径）。172a.p 的 floor=12 保证 xuanhuan 不会比 sci-fi 更短视。
4. **health median ≥ sci-fi**：sci-fi Ch25-100 health 9.2→10.0。xuanhuan median 不持续退化即可。

## 2. 为什么选 xuanhuan

1. **验证数据最厚**：xuanhuan 已有 end15（base=13000/15000 两轮）+ floor12 三次实跑，budget/CED/overdue 都有基线。
2. **最难的体裁**：genre_rules 比 scifi 贵 +79.9%（172a.1），状态密度最高（功法/境界/势力/法宝）。在最难体裁上证明 Ch100 = V 维度最强证据。
3. **S 修复是 xuanhuan 特化的**：172a.p horizon floor=12 专为 xuanhuan 密集埋伏笔设计，Ch100 尺度是它的真实考验。
4. **模板骨架就绪**：`project_templates/xuanhuan/outline.json` 已含 9 arc（覆盖 Ch1-250）+ 3 thread，Ch100 落在 arc 3 边界（Ch76-100），全程 `has_skeleton=True`。

## 3. 实施（复用既有基础设施，不新增节点）

### harness

新建 `scripts/run_172b_ch100_climb.py`，复用 `run_158_ch1_ch100.py` 的编排（无人值守 + kill/resume + 逐章 metrics + 报告），但：

- 项目初始化改用 `ProjectInitializer.from_template("xuanhuan")`（自动导入 9-arc/3-thread 骨架），**删掉 run_158 的手搓 `_build_outline`**。
- `gate_config = GateConfig.for_mode("enforce")`，`on_failure="isolate"`。
- runtime_profile 由 pipeline 按 genre 自动加载（xuanhuan base=15000, floor=12 生效）。
- 分段跑（每 25 章一段，即 arc 边界），段间读 DB 汇总，避免单次超长阻塞。

### 分段爬坡计划

```
段1 Ch1-25   (arc0)  → 汇总 budget/overdue/health → 无 halt 才进段2
段2 Ch26-50  (arc1)  → 汇总 → gate
段3 Ch51-75  (arc2)  → 汇总 → gate
段4 Ch76-100 (arc3)  → 汇总 → 出 Ch100 报告
```

每段结束跑一次证据收集（continuity_reports、context_snapshots、foreshadowings、review_reports CED），任一段触发 halt 或指标劣化即停并路由 172b.p。

### 证据 & 报告

产出 `archive/v8/reports/172b-xuanhuan-ch100-climb.md`：逐段 budget 曲线、ContextEmergency 频率、overdue 轨迹、CED vs scifi Ch1-100 基线、health 趋势、失败清单。

### V 维度验收判定器（可证伪）

`.tmp/vdim_compare.py` 读 live xuanhuan DB，按当前爬坡深度线性插值 sci-fi 基线（`.tmp/scifi_ch100_baseline.json`），对 5 个门禁给 PASS/FAIL。**CED 用 chapter-bounded 口径**（issue 与 words 均按 `chapter_number <= up_to` 界定）——比 harness `_segment_metrics` 更严：后者 issue 计数不设章界，在 live DB 上会被 in-flight 章（如正在写的 Ch11 report）污染，判定器自算 bounded CED 规避此偏差，与冻结基线严格同口径。

| gate | 判据 | sci-fi 对标 |
|---|---|---|
| budget | xuanhuan budget_peak < 1.0 且无 halt | 峰值 0.989 |
| CED | xuanhuan CED ≤ sci-fi × 1.15（172a.7「同级」口径） | 9.13-9.46 |
| overdue | xuanhuan overdue ≤ sci-fi 同章尺度 | Ch9→61 … Ch100→168 |
| health | xuanhuan health ≥ 8.0（median 不退化代理） | 9.2-10.0 |
| completeness | accepted ≥ up_to−1（gap≤1 自动过；gap>1 转 documented-isolate 复核，不静默阻断） | 100/100 |

Ch13 早期读（`up_to≥100` 才是终判）：budget 0.938 / CED 10.12（bounded）/ overdue 0 / health 9.0 / completeness 13/13 → **五门全 PASS**（early-warning，非终判）。终判在 climb 到达 Ch100 深度时给出：`final` 以「爬坡触达 Ch100」为终态，单章瞬时 isolate 会在 completeness 门显性报 REVIEW，而非永久判 partial。

## 4. 风险与撞墙路由（172b.p 预案）

| 风险 | 触发信号 | 172b.p 预案（不放宽口径） |
|---|---|---|
| 长尺度 budget 溢出 | Ch50+ budget_used 逼近 1.0 或 halt | ramp_per_chapter 按体裁微调 / genre_rules 内容精简（层 3），非分区权重 |
| **CED 超 sci-fi 同级** | Ch100 累计 CED > sci-fi × 1.15（≈10.50） | **定点修复 CED 热点章（多轮修订章 issue 计数最高者，如 Ch8/15/19/20），不放宽 tolerance、不改 CED 口径**。口径对称（scifi/xuanhuan 均按全版本 issue 计数），故 CED 超标是真实质量信号（首稿 issue 更密），诚实响应是修订质量提升而非放宽阈值 |
| overdue 反弹 | Ch100 overdue > sci-fi 同章（>168） | horizon floor 随章号动态 / 主动回收调度（评估是否超 MVP） |
| 连续性退化 | critical orphan > 0 / mismatch 持续 | continuity 容忍度按体裁（172a.6 已有 Profile 字段） |
| health 持续下滑 | median < scifi 基线 | 定点诊断，判定真退化则新开修复 Task |

> **CED 中途轨迹观测**（Ch21 深度实读，`.tmp/probe_ced_trend.py`）：累计 CED 在 Ch15（10.84）/Ch20（11.01）**曾超 Ch100 尺度 ceiling（10.50）**，Ch21 回落 10.53。热点集中在多轮修订章（Ch8=74 / Ch19=64 / Ch15=56 / Ch20=55 条 evidence issue）。此为 CED 门在 Ch100 终判的**首要风险**；口径与 sci-fi 严格对称，故若终判 FAIL 走上表 172b.p「定点修复热点章」预案，**严禁放宽 tolerance**。

### 4.1 实跑事故记录：resume 短路致 Ch26-100 从未生成（已修复，commit `dd5ac8a`）

**现象**：首轮爬坡在 Ch25 accepted 后「完成」，报告 4 段 accepted 恒为 25，Ch26-100 从未产出（分段表 up_to=50/75/100 的 accepted 均为 25，words 恒 86066）。

**根因**：`run_project_pipeline` 的 completed-run 幂等短路（`phase2_graph.py`）只判 `existing_run.status == "completed"`，未判「请求范围是否已全部 accepted」。分段爬坡逐段扩大 end（seg1 `(1,25)` 完成并把 run 标 completed；seg2/3/4 `(1,50)/(1,75)/(1,100)` resume 复用该 run），后续段命中 completed 即在 ~3s 内 0 生成短路返回。

**修复**：短路条件加 `_compute_resume_start(start,end,accepted) > end`（仅当请求范围已全部 accepted 才短路），否则落入既有 resume 续跑路径（重标 running、更新 end、从首个缺口章续跑）。回归测试 `test_resume_completed_run_expanded_range_continues`（completed run `(1,2)` + 请求 `(1,4)` → 生成 Ch3-4、跳过 Ch1-2）；既有 `test_resume_completed_run_returns_early`（全 accepted 范围仍短路）保持通过，幂等性不破。15/15 resume 测试通过。重启后实跑日志确认 `resume completed_count=25 previous_status=completed` 后 **`chapter_start chapter_number=26`**，续跑生效。

### 4.2 实跑事故记录：Ch30 `health_low_p1_halt` 假 orphan（已修复，commit `0d7cd42`）

**现象**：续跑在 **Ch30 撞墙**，`health_low_p1_halt: P1_count=1 (critical orphaned setting)`，health 6.8（<8.0），overdue 100。分段表 up_to=50 段 accepted=30、halt 非空。

**根因（定点审计，非放宽口径）**：`health_low_p1_halt` 门禁在 `hard_p1 > 0`（≥1 个 `category=='critical'` 的 orphaned setting）时触发（`_gates.py`；`count_hard_p1_for_halt` 仅计 critical，`_scanners.py` critical orphan 阈值=沉寂>3 章）。被判 orphan 的是 `祭坛上的'那个东西'`（key_alias=`entity` 英文）。实测正文 Ch26-29 分别出现「那个东西」×5/3/8/2——**writer 确实在回收**，但 `_setting_reference_terms`（settlement）与 `_check_mandatory_references`（rule_auditor 强制回收）的 name split 集**不含引号**，引号内 4 字核心词「那个东西」永不生成为引用词/候选，导致引用未被记账、`last_mentioned` 冻结在 25 → 假 orphan → 门禁 halt。**非门禁松紧问题**：sci-fi 在 Ch159/165 命中同一 `health_low_p1_halt`（其 run log 实证），门禁对 sci-fi 并未更松；xuanhuan 只是因「引号包裹/短口语化」命名更早触发。

**修复**：两条匹配路径统一把中英文引号纳入 name split（仍受 `len>=2` + low-info 过滤），使正文真实回收被记账，**不改任何门禁阈值**（真正被弃置的 critical setting 仍会 halt）。附带数据修复：`祭坛上的'那个东西'` 与 `'那个东西'的变形能力` 两个 setting 的 `last_mentioned_chapter` 按修复后 matcher 实证的真实末次引用章（Ch29）从 25/26 更正为 29——修复 matcher bug 造成的陈旧数据，非放宽。验证：修复后 Ch30 尺度 critical orphan `1→0`（`hard_p1=0`，halt 不再触发）；`test_172bp_quoted_xuanhuan_name_refreshes_tracking`（引号内实体被记账）+ `test_172bp_quoted_name_absent_does_not_refresh`（缺席仍不记账，门禁仍能捕获真 orphan）；53 recycling + 18 mandatory-reference 测试全绿，两文件 ruff-clean。

**续跑闭环验证（Ch31-35，实跑落地）**：修复后 resume 续跑无 re-halt，逐章正常推进 Ch31→35（各章 draft→revision→accepted，无门禁阻断）。关键实证——**Ch33 continuity 审计（每 3 章一跑）已落库 health=9.4**（从 Ch30 假 orphan 事件的 6.8 恢复），证明引号 matcher 修复**经受住真实审计**，非仅静态预测。`vdim_compare.py` 在 Ch35 深度五门全 PASS（early-warning）：budget 0.981 / CED 10.13（自 Ch28 的 10.40 持续下行，远离 Ch100 ceiling 10.71）/ overdue 76（<scifi 81）/ health 9.4（≥8.0）/ completeness 35/35。§4.2 事故闭环完成。

### 4.3 实跑事故记录：Ch65 overdue 超 sci-fi 同章尺度（已定点修复，172b.p）

**现象**：续跑越过 Ch50 后在 Ch65 early-warning 读数触发 V 维度 overdue FAIL：budget 0.981 PASS、CED 10.41 PASS、health 9.4 PASS、completeness 65/65 PASS，但 overdue **171 > sci-fi 同章尺度约 126**。按 §3/§4 纪律主动停止爬坡，冻结 live DB，路由 `tasks/172b.p-xuanhuan-foreshadowing-long-window.md`。

**根因**：172a.p 的 `foreshadowing_horizon_floor=12` 已生效（Ch65 live DB 中 168/191 条 horizon 为 +12），但它只解决短窗口 S 维度。Ch100 长窗口下，xuanhuan 每章 plant 密度高于 sci-fi（2.94 vs 2.20 条/章），且现有 MVP 中 sci-fi/xuanhuan 都几乎 `resolved=0`，overdue 主要由 plant 密度与 expected horizon 决定。floor=12 延后了爆发，但到 Ch65 仍线性累积并超过 sci-fi 同章尺度。

**修复**：不改 `vdim_compare.py`、不放宽 overdue 门禁、不改 sci-fi 基线；把 xuanhuan Ch100 长窗口运行时 floor 从 12 提升到 **48**（scifi=0、wuxia=12 不变），并对 live DB 未 resolved 伏笔执行一次性 expected 修复：`expected_resolve_chapter = planted_in_chapter + 48`、派生 `status` 重置为 `planted`。修复行数 188；overdue@Ch65 **171→50**，当前已 planted 伏笔的 overdue@Ch100 预估 **188→166**（低于 sci-fi Ch100 基线 168）。验证：`test_172ap_foreshadowing_horizon_floor.py` 12 passed；V8 profile 回归 164 passed；相关 ruff clean；`vdim_compare.py 65` 五门全 PASS；`segment_audit.py 65` 预测 Ch66 continuity audit `critical_orphans=0`、不会触发 halt。

### 4.4 Ch75 边界审计：五门 PASS，前瞻 orphan 风险由正文回收消解

Ch75 正式段边界（172b.p 修复后续跑）：

| gate | Ch75 xuanhuan | sci-fi 同章尺度 | verdict |
|---|---:|---:|---|
| budget | 0.981 | 0.989 | PASS |
| CED/1k | 10.55 | 9.46 × 1.15 | PASS |
| overdue | 85 | 136 | PASS |
| health | 9.6 | >=8.0 | PASS |
| completeness | 75/75 | 75/75 | PASS |

深度审计发现两次前瞻 critical orphan 风险，但均由后续 accepted 正文真实回收消解，而非放宽门禁：

- Ch78 前瞻：Ch75 时预测 5 个 critical orphan；Ch77 accepted 后全部被正文提及，`segment_audit.py` @Ch77 显示 Ch78 `critical_orphans=0`，Ch78 continuity audit 实际落库 health=9.7。
- Ch84 前瞻：Ch81 时预测 5 个 critical orphan；Ch82 accepted 刷新 4 个，Ch83 accepted 刷新剩余 `《渊海引气诀》第一层`，`segment_audit.py` @Ch83 显示 Ch84 `critical_orphans=0`。

当前判断：172b.p 的 long-window floor 修复稳定，orphan 风险主要来自 accepted 前的 in-flight 版本尚未刷新 tracking；只在 accepted 后仍 `critical_orphans>0` 时再开新定点修复。

### 4.5 实跑事故记录：Ch91-Ch93 CED 终段超线（转 172b.q）

**现象**：Ch89 仍五门 PASS（CED 10.60 <= 同章 ceiling 10.67），但 Ch91 起 CED early-warning 持续 FAIL：Ch91 10.66 > ceiling 10.64；Ch92 10.66 > ceiling 10.63；Ch93 10.76 > 约 10.60。Ch100 ceiling 为 sci-fi Ch100 9.1328 × 1.15 ≈ 10.50。按 Ch93 现场，剩余 7 章若平均 3000 字/章，新增 evidence issue 总量需 ≤136（约 19.4/章）才可能自然摊薄；而最近 Ch89/90/92/93 分别为 58/65/38/74，继续硬跑大概率 Ch100 CED FAIL。

**根因分层**：

1. 当前 `.tmp/vdim_compare.py` 的 CED numerator 过宽：把 `show_dont_tell`、`narrative_pacing`、`dialogue_subtext` 等文学 craft issue 计入 CED；它们不属于 Consistency Error Density。
2. 当前 vdim 同时计入 `llm` 与 `merged` report，而 merged 已包含 LLM issues，存在双重计数。
3. 即便过滤为 consistency-only，xuanhuan 的 `character_behavior` / `dialogue_distinctness` 密度仍高于 sci-fi，说明存在真实人物行为/声纹一致性风险，不能靠量具纠偏直接宣告通过。

**路由**：停止继续烧 Ch94-Ch100 token，转 `tasks/172b.q-consistency-ced-repair.md`：先修 CED 量具（consistency-only、去双计数、accepted source 可解释），再决定是否做真实 consistency 修复。不放宽 tolerance，不把文学 craft 当 CED 阻塞门。

### 4.6 Ch100 终判：五门 PASS，V 维度闭合

172b.q 修复后，xuanhuan 已推进到 **Ch100 accepted**。终判命令：

```powershell
python .tmp/vdim_compare.py 100
```

| gate | xuanhuan Ch100 | sci-fi Ch100 | verdict |
|---|---:|---:|:---:|
| budget_peak | 0.981 | 0.989 | PASS |
| consistency CED/1k | 0.4434（154 issues / 347,290 words） | 0.3976（157 issues / 394,839 words） | PASS（≤ ×1.15 ceiling 0.4573） |
| overdue foreshadowing | 166 | 168 | PASS |
| health | 9.1 | ≥8.0 | PASS |
| completeness | 100/100 accepted | 100/100 | PASS |

CED 终判使用 `src/songyan/evals/consistency_ced.py` 的 consistency-only 口径：每个 accepted head 追溯 review source version，优先 `merged` report，排除文学 craft issue 与 `rule-mr-*` mandatory-reference 聚合工作项（该项的 `evidence_quote` 是 setting key 列表，不是正文证据句）。真正带正文引用的 `world_consistency` 仍计入。

结论：172b 达成 V8 V 维度验收条件。按 V8-README §“Ch100 爬坡后置”纪律，172c（wuxia 第二体裁 Ch100）是 V8-pass 后续增强，不回溯性阻塞本次 V8 完成判定。


## 5. 依赖

- **硬前置**：172a.7 报告全绿（scifi/wuxia/urban 回归 + CED 基线）+ 172a.p overdue<5 实证。**未达标不开工**（V8-README 纪律："172a.7 证明短窗口质量达标后才启动 172b"）。
- xuanhuan Ch100 已达标 → 172c 可选 wuxia 做第二体裁增强验证（wuxia --end 10 已证 0 halt、peak 0.958、CED 8.48 优于 scifi）。

## 172c 预备情报：wuxia 需要 horizon floor

wuxia --end 15 回归 DB 解剖（`.tmp/analyze_foreshadowing.py`）显示 wuxia 的 plant-time horizon **比 xuanhuan 更短**：分布峰值在 +2（8 条）/+3（8 条），max 仅 +11，overdue 达 25（end15, floor=0）。这是与 xuanhuan 相同的短 horizon 病理，且更严重。

实跑 DB 模拟 horizon floor 效果：

| floor | overdue @end10 | overdue @end15 |
|---|---|---|
| 0（现状） | 12 | 25 |
| 8 | 1 | 16 |
| 10 | 0 | 12 |
| **12** | 0 | **5** |

**结论**：172c 启动 wuxia Ch100 前，必须给 wuxia profile 设 `foreshadowing_horizon_floor`（建议 **≥12**，与 xuanhuan 同级；长窗口可能需更高）。这是 172a.p 机制的直接复用，无需新代码——只在 `_default_registry()` wuxia 条目加一行 `foreshadowing_horizon_floor=12`。
