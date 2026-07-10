# Task 170h: 中段窗口文学性/可读性复评报告（初筛）

> 生成时间: 2026-07-09 10:37:48
> 项目: `995b5623470f4b8792bfc1854e6030e9`  窗口: Ch29-Ch32  抽到章数: 4
> 本报告为**助手初筛**：LLM 按 5 维 rubric 预评 + 机器分对照 + 标可疑点。
> **最终文学判定以用户复核终评分为准**（见第 5 节留空表）。

## 1. 5 维 rubric 说明

| 维度 | 含义 | 对应机器信号 |
|------|------|--------------|
| ai_tone | AI 腔密度 | ai_rhythm_pattern / RuleAuditor |
| voice | 角色声纹区分度 | polyphony_weakness / character_autonomy |
| concept | 概念空转 | conceptual_idling / conceptual_grounding |
| exposition | 说明文堆叠 | authorial_intrusion / excessive_smoothing / exposition_carrier |
| pacing | 场景节奏 | momentum / excessive_smoothing |

评分 1-5（1=差 5=好）。抽读正文见 `.tmp/task170h_prose_ch28_ch40.md`。

## 2. LLM 初评 5 维分（初筛，非最终）

| Ch | ai_tone | voice | concept | exposition | pacing | 均值 | 最差维 | 一句话总评 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 29 | 3 | 2 | 4 | 3 | 4 | 3.20 | voice | 概念落地有质感，但角色声纹趋同、AI腔排比堆砌，整体干净但缺乏个性。 |
| 30 | 2 | 2 | 3 | 3 | 4 | 2.80 | ai_tone | 节奏紧张但语言模板化、角色声纹模糊，概念落地不足，属于‘干净但平庸’的网文章节。 |
| 31 | 2 | 1 | 3 | 2 | 4 | 2.40 | voice | 场景推进有力，但角色声纹完全扁平，AI腔明显，概念落地不足。 |
| 32 | 2 | 1 | 3 | 2 | 3 | 2.20 | voice | 概念有潜力但被模板化比喻和说明文式对白拖累，角色声纹几乎无区分，节奏在记忆回放中陷入停滞。 |

## 3. 机器分 vs LLM 初评 偏差（诊断可信度）

| Ch | 机器 literary_quality | 机器 character_autonomy | 机器 conceptual_grounding | LLM rubric 均值(×2) | 偏差判定 |
|---:|:---:|:---:|:---:|:---:|---|
| 29 | 5.50 | 2.50 | 4.00 | 6.4 | 一致(rubric≈6.4 vs 机器5.5) |
| 30 | 5.50 | 3.50 | 5.00 | 5.6 | 一致(rubric≈5.6 vs 机器5.5) |
| 31 | 5.50 | 2.50 | 4.50 | 4.8 | 一致(rubric≈4.8 vs 机器5.5) |
| 32 | 5.50 | 2.50 | 6.00 | 4.4 | 一致(rubric≈4.4 vs 机器5.5) |

> 偏差判定：LLM rubric 均值归一到 0-10 后与机器 literary_quality 相差 ≥3 记 ⚠️。
> ⚠️ 项是「机器诊断可能失真」的候选，需用户重点复核。

## 4. T9 文本洁净度 + exposition 载体 + run_log

| Ch | meta_tag | duplicate_para | timeline_conflict | exposition_carrier | QG_passed | degraded | continuity_health |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 29 | 0 | 0 | 0 | 0 | True | False | - |
| 30 | 0 | 0 | 0 | 0 | True | False | 3.00 |
| 31 | 0 | 0 | 0 | 0 | True | False | - |
| 32 | 0 | 0 | 0 | 0 | True | False | - |

> T9 硬红线（窗口合计）：元标记泄漏 0、整段落重复 0。（时间线矛盾为 report-only 诊断，不计硬红线。）
> exposition 载体硬灌（窗口合计）：0 处；分布：无。

## 5. 用户复核终评分（待填）

> 请只读第 3 节 ⚠️ 偏差章和第 2 节最差维标出的章，逐章给 1-5 终评分。

| Ch | ai_tone | voice | concept | exposition | pacing | 备注 |
|---:|:---:|:---:|:---:|:---:|:---:|---|
| 29 |  |  |  |  |  |  |
| 30 |  |  |  |  |  |  |
| 31 |  |  |  |  |  |  |
| 32 |  |  |  |  |  |  |

## 6. 可疑段落摘录（LLM 标出，供复核定位）

**Ch29**（最差维 voice）：“你以为钥匙是给你用的？”声音压低，像在拆穿一个幼稚的谎言。“别让它闭合——除非你想变成墙。”声音不是从空气中传来的，是直接写入神经接口的。

**Ch30**（最差维 ai_tone）：林渊咬紧牙关，用右手撕开左肩残存的衣料。神经接口露出来，金属插口边缘的皮肤已经碳化，露出暗红色的肌肉组织。他从口袋里掏出最后一根连接线——不是标准接口，是他在第七舱段改装的应急线缆，线芯裸露，没有绝缘层。

**Ch31**（最差维 voice）：“不对。”林渊的声音从喉咙里挤出来，干涩得像砂纸摩擦。“这不对。”他后退一步，靴底踢到一块崩解的金属碎片。碎片在空中翻转，落入扭曲场，瞬间化作金色尘埃。

**Ch32**（最差维 voice）：“这是唯一的办法。”韩墨的声音像念协议文本，句式完整到不自然，“方舟必须被锁死。钥匙持有者互补关系已经建立——你需要一个复制体来维持核心协议的稳定性。”

## 7. exposition 载体硬灌明细（Task 170h 代码检测）

窗口内未检测到明显 exposition 载体硬灌模式。

## 8. 与 170b 基线对比

| 维度 | 170b 基线 | 170f Stage 2 | 170h 目标 | 备注 |
|------|:---:|:---:|:---:|------|
| voice | 1.8 | - | 可测量提升 | 需 LLM rubric / 机器 character_autonomy 双重验证 |
| pacing | 2.4 | 3.25 ✅ | 保持 ≥3.0 | 170f 已验证 scene_interaction 有效 |
| exposition | 2.1 | 2.0 ❌ | ≥2.5 | 170h 核心攻坚指标 |
| concept | 3.2 | 3.0 | 不回退 | |
| ai_tone | 2.2 | 2.0 | 不回退 | |
| T9 近似重复 | 漏报 | 0 | 不漏报 | 170c 已补强 |

> 170h 判定：需综合 LLM rubric 均值、机器分、exposition 载体检测、T9 硬红线、用户复核终评分后给出 pass/observation/blocker。

## 9. 初筛观察（助手，非最终判定）

- LLM 初评窗口 5 维均值: 2.65 / 5
- 机器/LLM 偏差大(⚠️)的章数: 0 / 4
- T9 硬红线: 元标记 0、整段落重复 0
- exposition 载体硬灌: 0 处

> 这是助手初筛观察，**不是 pass/observation/blocker 判定**。最终判定需用户复核后，在 170h DONE 文档中给出。
