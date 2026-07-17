# Task 171 Ch200 长跑分析报告与下一阶梯规划

> 日期：2026-07-12  
> Run ID：`run-fb39245c`  
> DB：`.tmp/task171_ch1_ch200.db`  
> 范围：Ch1-Ch200  
> 结论口径：稳定性面硬指标 + 20% 人工抽读复盘 + Tier 2 文学观测

## 1. 执行结论

Task 171 Ch200 长跑最终完成：**200/200 accepted，failed gaps=[]，run status=completed，Halt=None**。

这证明 171p/171q/171r/171s 四个撞墙修复后，系统已具备 Ch200 级别的无人值守推进能力：

- 171p/171r：`state_mismatch` 假阻塞被根治，未再阻断长跑。
- 171q：分段修订去重阈值对齐后，逐字重复大幅下降。
- 171s：critical setting 同义提及刷新修复后，Ch159/Ch165 的 false critical orphan 不再重复阻断。

20% 抽读复盘后，稳定性面遗留问题一度从“duplicate + stale report”扩展为更明确的 **D1 文本洁净量具 false negative**：

1. **171u 前 T9 duplicate hard defects 曾为 4**：Ch11(1)、Ch84(2)、Ch171(1)，现已清零。
2. **文本洁净 artifact 漏检**：Markdown 章标题、保护指令、斜杠拼接、纯省略号段、prompt/patch 指令进入 accepted 正文，但旧 T9 meta 口径未全部命中。
3. **报告中保留 Ch159/Ch165 stale critical orphan 历史行**：代码与当前 tracking 已修复，但历史 continuity report 未重算，导致报告层仍显示 P1 peak=1。

171t/171u 已完成后，Task 171 主线的工程结论更新为：**Ch200 规模化完成，且 D1 hard clean pass。进入 Ch250 前的剩余前置不再是硬清洁，而是 171v Ch200+ 文学可读性护栏。**

## 2. 核心指标

| 指标 | 结果 | 判定 |
|---|---:|---|
| accepted chapters | 200/200 | ✅ |
| run status | completed | ✅ |
| gaps | 0 | ✅ |
| Halt | None | ✅ |
| 平均字数 | 3946.6 | ✅ 稳定 |
| 字数中位数 | 4142 | ✅ 稳定 |
| 字数范围 | 2640-4557 | ✅ 可接受 |
| duplicate paragraphs | 0 | ✅ 171u 后 clean |
| meta leak / artifact | 0 | ✅ 171t/171u 后 clean |
| health avg | 9.47 | ✅ |
| health median | 9.6 | ✅ |
| orphan slope | 0.0332/章 | ✅ 很低 |
| critical orphan peak（当前事实源） | 0 | ✅ stale report 已排除 |

## 3. D1 文本洁净残留

全量 accepted 正文扫描发现 4 处重复：

| 章节 | 数量 | 类型 |
|---:|---:|---|
| Ch11 | 1 | 近重复：同一句仅引号形态不同（`'...'` vs `“...”`），similarity=0.9706 |
| Ch84 | 2 | 逐字重复同一句：“字段#7到#12的波形……” |
| Ch171 | 1 | 逐字重复系统播报句：“收割者舰队预计抵达时间……” |

这说明 171q 的分段修订路径修复有效，但当时仍缺一个 **accept-time T9 final sweep**。171t/171u 已补齐该缺口。

20% 抽读进一步发现旧 T9 meta 口径存在 false negative；171t/171u 已将其纳入 hard issue 并完成当前 Ch200 清洁：

| 类别 | 样例章节 | 判定 |
|---|---|---|
| Markdown 章标题 | Ch1、Ch2、Ch4、Ch47、Ch75 | accepted 正文不应出现 `# 第一章`、`# 第二章` 等标题行 |
| 保护指令 | Ch84、Ch160 | `【保护内容 — 请勿修改】` 属于明确非叙事指令泄漏 |
| 斜杠拼接 | Ch41、Ch76、Ch124、Ch164 | 非单位/坐标/路径语境下的 `/` 疑似 patch 拼接残留 |
| 纯省略号段 | Ch26、Ch32、Ch76、Ch101、Ch174 | 独立段落仅含省略号，疑似占位残留 |
| prompt/patch 指令 | Ch76 | “每句末尾加重语气，机械眼闪烁红色警告”属于写作指令进正文 |

注意：并非所有括号/系统播报都是缺陷。科幻文本中的 diegetic UI 警告、系统提示可以合法存在；171t 需要做的是补足 hard artifact 识别，同时避免误伤叙事内 UI。

## 4. 工程质量趋势

按 50 章分段统计 accepted version score_card：

| 区间 | overall | readability | coherence | momentum | length |
|---|---:|---:|---:|---:|---:|
| Ch1-50 | 0.843 | 0.885 | 0.868 | 0.924 | 0.722 |
| Ch51-100 | 0.871 | 0.884 | 0.865 | 0.976 | 0.732 |
| Ch101-150 | 0.877 | 0.863 | 0.870 | 0.958 | 0.724 |
| Ch151-200 | 0.881 | 0.859 | 0.881 | 0.958 | 0.736 |

解读：

- overall 没有衰减，反而轻微上升。
- readability 从 0.885 到 0.859，轻微下降但仍在高位。
- coherence 稳定，后段略升。
- momentum 从 0.924 提升并稳定在 0.958 以上。

工程门禁层面没有出现长篇衰减。

## 5. 文学 Tier 2 观测

按 50 章分段统计 accepted version 的 LiteraryAuditor：

| 区间 | literary_quality | character_autonomy | conceptual_grounding | fissure_preservation |
|---|---:|---:|---:|---:|
| Ch1-50 | 5.58 | 3.01 | 4.97 | 7.08 |
| Ch51-100 | 5.66 | 3.14 | 5.62 | 7.05 |
| Ch101-150 | 5.59 | 2.84 | 5.05 | 7.10 |
| Ch151-200 | 5.59 | 3.02 | 5.38 | 7.19 |

解读：

- literary_quality 稳定在 5.6 左右，没有长篇衰减。
- fissure_preservation 稳定在 7.0+，主线裂隙保持较好。
- conceptual_grounding 中等偏稳，Ch51-100 最强，后段回落但未崩。
- character_autonomy 长期在 3.0 附近，是最明确的文学短板。

报告触发 Tier 2 spot_read：`character_autonomy_score`、`conceptual_grounding_score`、`fissure_preservation_score`。人工抽读结果支持“角色自主性为主要短板”，但不支持“整体 prose 劣化”。

## 6. 20% 抽读方法

首次分析抽读 30/200 章；本次复盘扩展到 40/200 章，并额外覆盖 high-risk artifact 命中章。

原 30 章样本为：

Ch1、8、15、22、29、36、43、50、57、64、71、78、85、92、99、106、113、120、127、134、141、148、155、162、169、176、183、190、196、200。

扩展复盘额外关注：

- 早章/中段/后段均衡抽样；
- T9 duplicate 命中章；
- Markdown 标题、保护指令、斜杠拼接、纯省略号段、prompt/patch 指令等 high-risk artifact 命中章；
- Ch159/Ch165 stale critical orphan 相关上下文。

抽读方式：

- 每章读取开头、中段、结尾；
- 关注 T9 重复、文本 artifact、AI 腔、场景动作、角色声音、概念落地、长篇后段疲劳；
- 结合全量 duplicate scan 与 score_card/literary_observations。

## 7. 抽读结论

### 7.1 优点

1. **长篇后段没有散架**
   Ch190/196/200 仍有清晰任务目标、空间场景、动作推进和悬念钩子。系统没有出现“后段只剩摘要/解释”的退化。

2. **硬科幻质感稳定**
   后段持续使用坐标、频率、协议层、导航、相位、晶体节点等具体机制承载概念，而不是泛泛“能量/命运/真相”。

3. **动作与身体代价持续存在**
   林渊的神经损伤、金属化、左臂接口、频率过载在多章中持续成为行动阻力，文本没有完全漂浮为设定讲解。

4. **章节钩子有效**
   多数样本结尾有清晰 forward pull，例如 Ch127 “你带来的钥匙，不止一把”、Ch190 禁忌之门扩张、Ch200 黑色晶体主动生长。

5. **AI 腔没有明显反弹**
   抽样中未见典型空泛总结句、模板化议论或“在这个充满……”式表达。

### 7.2 D1 硬缺陷

1. **文本洁净检测漏报**
   旧报告 `meta=0` 不能代表正文 artifact 为 0。Markdown 标题、保护指令、纯省略号段等必须进入 T9 hard issue。

2. **accept-time 缺少 final sweep**
   Ch11/84/171 的 duplicate 表明最后 accepted head 仍可能携带重复段落，不能只依赖 revision 中间路径去重。

3. **stale report 污染最终判定**
   Ch159/165 的 critical orphan 是 pre-fix false positive，当前 tracking 已能刷新同义提及，但最终报告仍可能读取旧 continuity report。

### 7.3 文学短板

1. **角色自主性不足**
   林渊经常是在协议、倒计时、系统播报、外部危机驱动下反应。虽然他有选择，但选择常表现为“继续破解/继续推进”，缺少更多价值冲突、误判代价和主动设局。

2. **后段概念密度偏高**
   Ch127 之后，“协议层、基因锁、陷阱协议、频率深渊、观察者、方舟意志、审判序列”等概念密集叠加。可读性仍可接受，但读者负担上升。

3. **动作母题有重复**
   高频模式包括：指尖悬停、左臂接口发烫、倒计时、神经接口刺痛、控制台数据流。这些是有效母题，但在 200 章尺度上需要更多替换动作与生活化/关系化承载。

4. **人物关系戏份偏功能化**
   赵铭、小周、陈薇/陈曦等角色能推动信息与情绪，但多数时候仍服务于主线机制。下一阶梯需要让配角在关键节点拥有自己的目标与误判，而不只是解释/提醒/牺牲。

## 8. 总体质量判断

本次 Ch200 证明：系统已能在 200 章尺度维持稳定可读的硬科幻网文文本，不再出现 V6/V7 早期那种整段重复、明显 AI 腔、后段摘要化、上下文失控式塌陷。

171t/171u 完成后，Ch200 已从“规模跑通”升级为“D1 hard clean pass”。但若目标是“200 章以上保证文学性和可读性并提升到下一阶梯”，当前仍不应直接冲 Ch250；下一步应把 Tier 2 文学短板转成 Ch200+ 护栏。

## 9. 下一步规划

### Task 171t：Ch200 D1 文本洁净量具补强（必须先做）

状态：✅ 已完成。

目标：先让量具能看见所有 hard-clean 问题，避免旧 `meta=0` 造成虚假通过。

内容：

1. 扩展 T9 hard issue 检测：
   - Markdown 标题；
   - 保护指令；
   - 斜杠拼接；
   - 纯省略号段；
   - prompt/patch 指令；
   - duplicate final sweep。
2. 每个 hard issue 必须有定位和 `evidence_quote`。
3. 区分合法 diegetic UI 与真实指令泄漏，避免误伤。
4. 输出 171u 可消费的清洁清单。

### Task 171u：Ch200 D1 清洁应用与报告事实源复算

状态：✅ 已完成。

目标：基于 171t 的补强量具，把 Ch200 当前 accepted head 清到 D1 hard issue=0。

内容：

1. 对 Ch200 accepted 正文执行 final sweep；
2. 对 deterministic-cleanable issue 创建 cleaned version，禁止覆盖旧 `chapter_versions`；
3. 清洁 Ch11/84/171 duplicate 及所有 artifact；
4. 修复 continuity report 聚合，只取最新事实源，排除 Ch159/165 pre-fix stale 污染；
5. 重跑 `--report`，目标：
   - T9 duplicate=0；
   - T9 meta/artifact=0；
   - gaps=0；
   - Halt=None；
   - critical orphan 当前事实源一致。

结果：

- 追加 20 个 clean accepted versions；
- accepted heads 200/200；
- remaining hard issues=0；
- T9 meta/artifact=0；
- T9 duplicate=0；
- T6b critical orphan peak=0；
- `task-171-ch200-long-run-report.md` 已复算。

### Task 171v：文学可读性护栏（Ch200+ 前置）

目标：不阻塞主线，但给 Ch250 前的 Writer/CreativeDirector 增加轻量护栏。

内容：

1. 角色自主性护栏：
   - 每章 chapter goal 明确一个“林渊主动选择”；
   - 选择必须包含备选方案、代价、不可逆后果；
   - 不允许只写“继续破解/继续推进”。
2. 概念密度护栏：
   - 每章最多 1 个新核心概念；
   - 新概念必须通过动作/对话/失败结果落地；
   - 后段禁止连续三章以纯协议解释推进。
3. 母题疲劳扫描：
   - 统计“指尖悬停/左臂发烫/倒计时/神经接口刺痛”等高频表达；
   - 超阈值时给 Writer 注入替代表达建议。
4. 配角目标注入：
   - 每 5 章至少 1 个配角拥有与林渊不完全一致的目标；
   - 通过冲突推动信息，而非只做提示器。

### Task 171w：171v-hardening 与 Ch201-Ch220 重验

状态：✅ 已完成（2026-07-13）。

前置原因：171v Ch201-Ch220 小窗口 `run-e27b763f` 已实跑但未通过出口：19/20 accepted，failed=[207]，配角目标未落正文，主动性与概念密度未达预期。

执行结果（四个工作包全部落地）：

- **171w-a**：报告脚本参数化（`--run-id` / `--output` / `--include-legacy-harness`），Ch200 主报告 run_id 已校准为 `run-fb39245c`，旧 V6 harness 表默认不输出。
- **171w-b**：171v 四类护栏字段持久化到 `creative_briefs`（`protagonist_active_choice` / `new_concept_budget` / `fatigue_motif_replacements` / `supporting_character_goal`），revision metadata 继承 parent brief/snapshot，范围审计 helper 可回放完整链路。
- **171w-c**：正文 observe 检测硬化（配角目标/主动选择/概念预算），ReviewMerger 接线将"目标配角未出现在正文"升级为 major patchable issue（CHARACTER_BEHAVIOR），可触发自动修订链路。
- **171w-d**：Ch207 settlement 数值闭合修复（解析层 + 验证层双层兜底），重跑 Ch201-Ch220 **20/20 accepted，failed=[]，Halt=None，status=completed**，T9 meta/artifact=0、duplicate=0。

出口证据：Ch201-Ch220 20/20 accepted，Ch207 已接受（`rev-207-7-edf1218b`），numerical ledger 正常闭合。

### Task 172：Ch250 下一阶梯验证

前置：171w hardening + Ch201-Ch220 重验通过。✅ 前置已满足。

执行：

1. 以当前 Ch200 DB 为起点 resume 到 Ch250；
2. 每 25 章自动生成中间报告；
3. 抽读比例保持 15%（Ch201-250 抽读 8 章 + 关键失败章全读）；
4. 放行标准：
   - T9 duplicate/meta/artifact=0；
   - gaps=0；
   - Halt=None；
   - health median >= 8.5；
   - 文学抽读无明显后段疲劳；
   - character autonomy 人工抽读不低于 Ch150-200 水平。

## 10. 建议结论

Task 171 已取得关键工程突破：**Ch200 全量跑通 + D1 hard clean pass**。171w 硬化后 Ch201-Ch220 20/20 accepted 验证通过。

推荐执行顺序：

1. Task 171w：171v-hardening 与 Ch201-Ch220 重验；✅ 已完成（2026-07-13）
2. Task 172：Ch250 长跑验证（前置已满足，可启动）。
