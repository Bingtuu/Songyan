# Task 196 校准报告：优秀度信号包样本集、标注协议与规则试点负结果

> **任务**: `tasks/196-excellence-signal-calibration.md`（V10.3 优秀度信号包首任务）
> **完成时间**: 2026-07-29
> **数据**: `archive/v10/artifacts/196-excellence-sample-set.json`（60 章样本，seed=196）、`archive/v10/artifacts/196-excellence-annotations.json`（72 条标注）、`.tmp/196_rule_pilot.json`（规则试点）、`.tmp/196_sample_texts/`（60 章正文快照，复算用）
> **复算脚本**: `.tmp/196_calib_compute.py`（本报告全部数字由该脚本从上述产物计算，非转抄）

---

## 1. 目的与产物清单

Task 196 目标：为 V10 C 组优秀度信号包（197-203）建立公共基础——可复现样本集、三层标注协议、第一次真实误报实证；196 本身不实现任何新信号。

三份版本管理产物：

| 产物 | 路径 | 内容 |
|------|------|------|
| 样本清单 | `archive/v10/artifacts/196-excellence-sample-set.json` | 60 章：xuanhuan 冻结库（`.tmp/task_v10_xuanhuan_ch200.db`，project `d160a55a…`）+ sci-fi 冻结库（`.tmp/task171_ch1_ch200.db`，project `835afdf1…`）各 30 章；seed=196，segment_size=25，8 个弧段每段 3-4 章全覆盖；每样本含 genre/chapter/version_id/segment |
| 标注记录 | `archive/v10/artifacts/196-excellence-annotations.json` | 72 条 AnnotationRecord：anchor 12 + prelabel 48 + spotcheck 12（实测分层计数 48/12/12） |
| 校准报告 | `tasks/196-excellence-calibration-report.md` | 本文 |

AnnotationRecord schema：`{genre, chapter, version_id, sample_layer, scores, rationale, evidence_quotes, annotator, disagreement}`。`scores` 为四维 1-5 Likert：homogeneity（同质化感知）、tension（张力/节奏）、ai_tone（AI 腔）、overall（整体优秀度）。`sample_layer` 三值：`anchor`（agent 精读锚点，好坏两极各 6）/ `prelabel`（LLM 批量预标）/ `spotcheck`（agent 深读抽检复核）。`annotator` 三值：`agent-deep-read` / `llm-prelabel` / `human-review`；本批实际落库两值（24 条 agent-deep-read + 48 条 llm-prelabel），人工抽审未产生分歧故无 `human-review` 行（见 §5）。

---

## 2. 信号边界

优秀度信号包内各任务的测量边界：

| 任务 | 测什么 | 不测什么 |
|------|--------|----------|
| 197 跨章同质化/多样性/叙事张力 | 章间词汇/意象/结构复用度、弧段内张力曲线 | 单章文笔好坏、设定一致性 |
| 198 中文 AI 腔规则包 | 词面级 AI 痕迹模式类扩充（复读、自指泄漏、工程残留、套路表达） | 语义级文学判断、角色一致性 |
| 200 角色声纹锚点 | 角色对白的声纹稳定性/区分度 | 情节张力、设定正确性 |

边界声明（对齐 V10 守护项与 C5）：**优秀度、文学 craft、同质化、AI 腔一律不进入 CED**。CED 维持现口径：consistency-only、merged/source、正文证据。本批全部信号（LLM judge 分数、规则命中、深读标注）与五门/segment audit/T9 判定路径零交集，196 实施中未改动任何 gate 与运行时口径。

---

## 3. report-only vs 候选 gate 划分

- **V10 内全部信号 report-only**：只做离线分析或 report/observe 输出，不注入 Writer/CreativeDirector prompt，不进入自动硬门。
- **任何信号进 gate 的前置条件**（对齐 C5）：① 有本报告级的校准证据（样本真值 + 区分度数据）；② 单独立项批准；③ 改动后跑 scifi 短窗口回归，影响 Ch200 口径的还须重放 189 baseline。
- **本批信号当前成熟度评估**：
  - 规则信号（`detect_ai_tells` + `detect_fatigue_words` 现形态）：**负结果，不可用**——区分度为零甚至方向反转（§4），不得用作任何校准基准或阈值；
  - LLM judge 预标：**未校准，存在单向宽松偏差**（§5），分数不可直接用作阈值或真值替代；
  - agent 深读标注（anchor 12 + spotcheck 12）：**小样本真值基准**——可作 197/198/200 的校准锚，但样本量只支撑方向性结论，不支撑阈值定标。

---

## 4. 试点误报记录（负结果）

### 4.1 数据

`detect_ai_tells`（内置 20 条正则）+ `detect_fatigue_words`（词表取 `src/songyan/genres/data/<genre>.json` 体裁数据）跑全部 60 章，逐章命中（`scripts/run_196_rule_pilot.py` → `.tmp/196_rule_pilot.json`，复算自 `.tmp/196_calib_compute.py`）：

| 指标 | 值 |
|------|-----|
| ai_tell_count 分布 | 0 命中 53 章 / 1 命中 6 章 / 2 命中 1 章（合计 7/60 章有命中） |
| 命中类别分布 | 机械意识触发 ×5、AI 套路表达 ×1、抽象情感表达 ×1 |
| fatigue_word_total | mean=0.67，max=3，分布 0:33 / 1:15 / 2:11 / 3:1 |
| 弱锚点（overall≤2，n=6）ai_tell 均值 | **0.00**（6 章全部 0 命中） |
| 强锚点（overall≥4，n=6）ai_tell 均值 | **0.33**（xuanhuan Ch1、scifi Ch1 各 1 命中） |

### 4.2 结论

**该规则集当前形态不适合做优秀度校准基准。** 问题不是误报率，而是召回/区分度：

- 6 个最弱锚点章（overall=2，人工深读判定的最差样本）规则命中全为 0——漏报率 100%；
- 仅有的 2 次锚点命中落在 overall=5 的最强章上，组均值方向反转（弱 0.00 < 强 0.33）。n=6/组纯属噪声，但即便忽略显著性，该信号在最需要区分的两极样本上毫无区分力；
- fatigue 词表 max=3、33/60 章（55.0%）为 0，无分档能力。

### 4.3 不匹配分析（Task 198 输入）

现 `ai_tells` 共 5 类 20 条正则：机械意识触发（3）、过度感官描写（5）、抽象情感表达（4）、时间感知异常（4）、AI 套路表达（4）（`src/songyan/utils/ai_tells.py:12-42`）。全部是**文风修辞类**词面模式。而 24 章 agent 深读标注实际抓到的缺陷主类是**生成/拼装事故类**，完全不在现有模式集内：

| 人工深读缺陷类 | 典型证据（锚点 rationale） | 现规则覆盖 |
|----------------|---------------------------|------------|
| 逐字段落/句子复读（verbatim repeat） | xuanhuan Ch50 结尾整段重复第 13 行旧段；scifi Ch84 同句逐字 ×4；scifi Ch194 "瞳孔在急剧收缩" ×10 | 无 |
| 章节号自指泄漏 | scifi Ch84 "林渊在第21章看到过这个协议的设计蓝图"；scifi Ch194 "在第162章的老雷留下的线索中" | 无 |
| 工程残留/未渲染标记 | xuanhuan Ch50 残留 `## 二/三/四` Markdown 标题；scifi Ch84 未渲染舞台指示"（停顿半秒）"；xuanhuan Ch194 英文残留 "invisible" | 无 |
| 设定补丁段（说明文重述） | xuanhuan Ch118 第 185 行设定汇总段（令牌二分/星辰血脉/七家族手印） | 无 |
| 模板化修辞（否定三连/明喻机器化/意象库存枯竭） | xuanhuan Ch118 "纹路"明喻逐字重复 3 次（"像是活物"×1 + "像是活的"×2）；spotcheck 多章排比复读 | 部分（仅覆盖固定搭配，无复读计数） |

198 规则包扩充应以这五类为主方向，优先做"章内/跨章逐字复读检测"与"自指泄漏/工程残留词面规则"——它们在深读缺陷中占比最高且词面可达。

---

## 5. 标注协议与 provenance 声明

### 5.1 三层协议

1. **anchor（12 章）**：好坏两极各 6（双体裁各 3 强 3 弱），agent 逐章精读，rationale 必含正文证据引用；实测 evidence_quotes 45/45 逐字命中正文（100%）。
2. **prelabel（48 章）**：LLM 按 judge 卡 `excellence_prelabel/1.0.0.yaml` 批量评分，纯离线，不进工作流；evidence_quotes 逐字命中率 94/134 = **70.1%**，29/48 章含 ≥1 条非逐字引用（拼接/改写式引用）。
3. **spotcheck（12 章）**：从预标样本按弧段抽样（每体裁 6 章、每弧段 1 章，实测覆盖弧段 1-6，未含弧段 7-8），agent 深读复核，分歧写入 `disagreement` 字段；实测 evidence_quotes 48/48 逐字命中（100%）。

**provenance 声明（任务书强制）**：锚点真值为 **agent 精读 + 用户抽审（4 章），非全人工标注**。用户于 2026-07-29 抽审 4 条锚点标注（xuanhuan Ch1 强 / Ch50 弱、scifi Ch104 强 / Ch84 弱），结论：**认可，无分歧**。因抽审零分歧，标注记录中未新增 `human-review` 行，未触发协议降级路由。下游任务（尤其 201）必须按此 provenance 使用本批真值，不得当全人工标注引用。

### 5.2 judge 宽松偏差（LLM 预标失真）

预标 48 章 × 4 维 = 192 个维度分数，复算结果：

| 指标 | xuanhuan（n=24） | scifi（n=24） | 合并（n=48） |
|------|------------------|----------------|--------------|
| 分数 ≤2 的维度数 | 0 | 0 | **0 / 192** |
| homogeneity 均值 / 分布 | 3.67（min 3） | 3.96（min 3） | 3.81（3:9 / 4:39） |
| tension 均值 / 分布 | 4.79 | 4.96 | **4.88**（4:6 / 5:42） |
| ai_tone 均值 / 分布 | 4.21 | 4.04 | 4.13（4:42 / 5:6） |
| overall 均值 / 分布 | 4.33 | 4.25 | 4.29（4:34 / 5:14） |

对照锚点层：12 个锚点中 6 个 overall=2（最低 ai_tone=1、homogeneity=1）。**预标分布整体压扁在 3-5 分，锚点证明真实分布延伸到 1-2 分**——judge 看不见低分区。

spotcheck 12 章对照预标同章分数（分差 = spotcheck − prelabel）：

| 指标 | 值 |
|------|-----|
| ≥1 个维度分差 ≥2 的章 | **10 / 12** |
| 偏差方向 | **≥2 分差的 24 次全部 prelabel 高于 spotcheck；全部 48 项维度分差（含 <2）无一次 spotcheck 高于 prelabel——单向宽松，无反向** |
| 分差 ≥2 的维度分布 | ai_tone 9 次、tension 7 次、overall 6 次、homogeneity 2 次 |

judge 漏判内容（深读 rationale 归纳）：逐字复读、章节号自指泄漏、未渲染舞台指示、设定补丁段、模板修辞——与 §4.3 人工缺陷类完全同构。ai_tone 是偏差最大维度（9/12 章差 ≥2 分），因为 judge 对"工程事故型 AI 痕迹"不敏感，只捕捉文风型 AI 腔。

### 5.3 prelabel 层定位与 follow-up

- prelabel 是**低精度高天花板的草稿信号**：分数不可用作阈值，不可作真值；其价值是 48 章的广覆盖与 rationale 草稿。
- prelabel 证据引用保真度仅 70.1%，下游消费其 evidence_quotes 前必须逐字校验（对齐"没有证据的 issue 不进入自动修订"精神）。
- **Task 201 judge 偏差对策输入**：judge 卡 v2 候选——① rubric 注入好坏两极锚点示例（本批 12 锚点可直接复用）；② 强制检查项：逐字复读 / 自指泄漏 / 设定补丁段 / 排比复读 / 工程残留标记；③ 要求引用必须逐字，非逐字引用降权或拒绝。

### 5.4 双体裁精读印象（锚点 agent，30 章/体裁）

- **xuanhuan**：强章动作场景有物理支点（凹坑、苔藓、簧片、呼吸节奏），靠克制笔法立人物（"嘴角动了动，又收了回去"）；通病是工程痕迹残留（Markdown 标题、英文残词）、设定补丁段（说明文重述已铺信息）、意象库存枯竭（同一明喻全章复读）。
- **scifi**：具体化能力强（倒计时进度、字段数值、百分比制造张力）；通病是逐字重复失控（同句 ×4、核心短语 ×10）、叙事自指泄漏（章节号当记忆索引写进正文）、揭示套路循环（古老存在自白/反派解说腔）。

---

## 6. 对 197-202 的接口约定

- **样本清单**：`archive/v10/artifacts/196-excellence-sample-set.json`（seed=196，可复现；60 章正文快照 `.tmp/196_sample_texts/` 不版本管理，可用 `scripts/build_196_sample_set.py` 从冻结库重建）。
- **标注记录**：`archive/v10/artifacts/196-excellence-annotations.json`，schema 见 §1；消费前按 `sample_layer` / `annotator` 过滤。
- **各下游任务消费层**：
  - 197 / 198 / 200：用 **anchor + spotcheck（24 章 agent 深读）做校准真值**；prelabel 仅作对照基线，不得当标注真值；
  - 201：用 spotcheck 的 `disagreement` 字段（12 条 spotcheck 中 10 条含 prelabel_vs_spotcheck 分歧记录；xuanhuan Ch32、scifi Ch17 两章无分歧）+ §5.2 偏差数据做 judge 偏差建模；
  - 202 / 203：复用本报告的信号边界（§2）与成熟度评估（§3）。
- **user-review 结论记录**：2026-07-29 用户抽审 4 锚点（xuanhuan Ch1/Ch50、scifi Ch104/Ch84），零分歧认可；协议维持"agent 精读锚点 + 人工抽审"路径，未降级。

---

## 7. 局限

1. **样本规模**：60 章、双体裁（xuanhuan + scifi），wuxia/urban 未覆盖；跨体裁结论只支撑这两类。
2. **真值规模**：深读真值仅 24 章（anchor 12 + spotcheck 12），只支撑方向性结论，不支撑阈值定标与统计显著性检验（§4 的组均值 n=6/组）。
3. **真值主观性**：锚点为 agent 精读 + 4 章人工抽审，非全人工标注；不同精读者可能移动边界章 ±1 分（10/12 章分差 ≥2 与 24/24 单向性这类主结论不依赖边界判定）。
4. **judge 单卡单跑**：预标仅用 `excellence_prelabel/1.0.0` 一版卡各跑一次，未测卡间/采样方差；§5.2 的宽松偏差是"该卡该配置"的结论，201 改卡后需重测。
5. **规则试点范围**：仅 `detect_ai_tells` + `detect_fatigue_words` 现词表；§4.3 的不匹配分析证明该结果不可外推到"规则方法本身无效"，只证明"现有模式集无效"。
