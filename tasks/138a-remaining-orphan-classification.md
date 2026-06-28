# Task 138a: 剩余 orphan 分类与证据表

> **类型**: 诊断 / 证据整理
> **状态**: 进行中
> **前置**: Task 137 `run-4ba8de9d` Ch10-Ch12 聚焦复跑 completed

## 背景

Task 137 最新聚焦复跑 `run-4ba8de9d` 已通过 Ch10-Ch12：Ch12 accepted `v-12-6-75a4b0c7`，settlement/summary/QG 均通过；但 Ch12 continuity 仍为 `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。

本任务负责先把 19 个 orphan 的证据链拆清楚，不改代码、不复跑。

## 目标

输出剩余 19 个 orphan 的分类表和最小根因，作为 Task 138b 决策输入。

## 数据源与边界

- DB: `.tmp/task137_ch10_focus_20260628_183255.db`
- Run ID: `run-4ba8de9d`
- Ch12 accepted version: `v-12-6-75a4b0c7`
- 最新 Ch12 continuity report: `cont_e754c0a9`，`created_at=2026-06-28 10:53:13`
- 本轮只做只读查询与文档证据整理；不改代码、不复跑。

## 待办

- [x] 读取 `run-4ba8de9d`、`.tmp/task137_ch10_focus_20260628_183255.db` 与 Ch12 continuity report，确认 Ch10-Ch12 已 completed。
- [x] 记录 Ch12 continuity 现状：`health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
- [x] 导出 19 个 orphan 的 `setting_key`、`setting_name`、`category`、`introduced_in_chapter`、`last_mentioned_chapter`、`chapters_since_mention`、tracking/snapshot 状态。
- [x] 标注是否存在 active human mark、`recovery_required`、以及是否在 Ch11/Ch12 accepted 正文中出现。
- [x] 分类为：critical 未刷新/未合并、background/technical 未 archive、命名/别名/canonical 未命中、应转 human mark 或人工保留、真实 orphan。
- [x] 更新 Task 137 文档与 `docs/reports/task-137-ch10-focus-validation-report.md`。

## 只读查询结论

- Ch12 continuity: `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
- orphan category 分布: `critical=4`、`background=13`、`technical=2`。
- tracking 汇总: 19/19 均为 `setting_tracking.status=active`；19/19 均为 `recovery_required=0`。
- snapshot 汇总: 19/19 均有且仅有 1 条 `setting_snapshots.lifecycle_status=active`；未发现 orphan key 对应 archived snapshot 或一对多 lifecycle 混合。
- active human mark 汇总: 8/19 存在 `human_marks.lifecycle_status=active AND resolved_at IS NULL` 的 setting mark；11/19 无 active human mark。schema 支持 `recovery_required` 与 `human_marks.lifecycle_status/resolved_at`。

## 19 项分类表

> `HM` 表示 active unresolved setting human mark；`tracking/snapshot` 本表 19 项均为 `active / active(1)`，`recovery_required=0`。

| # | setting_key | setting_name | cat | intro | last | since | tracking_id | HM | Ch11/Ch12 accepted 正文证据 | 分类 |
|---:|---|---|---|---:|---:|---:|---|---|---|---|
| 1 | `artifact.mega_ruin.surface_material` | 巨型遗迹表面材料特性 | critical | 3 | 3 | 9 | `track-...-3b6909f4` | Y | Ch11: “巨型遗迹表面的能量纹路...以斐波那契序列频率激活”；另有“英仙臂外侧的巨型遗迹外层...非欧几何合金碎片” | 命名/别名/canonical 未命中 |
| 2 | `organization.expedition.team_7` | 第7远征队·静默节点 | critical | 4 | 7 | 5 | `track-...-12ec23a4` | Y | 未发现 `第7远征队` / `静默节点` | critical 未刷新/未合并 |
| 3 | `artifact.ruin.phase_flush_mechanism` | 相位冲刷机制 | critical | 7 | 7 | 5 | `track-...-3efb7ff8` | Y | 未发现 `相位冲刷` | critical 未刷新/未合并 |
| 4 | `artifact.mega_ruin.wall_living_properties` | 遗迹墙壁活体特性 | critical | 8 | 8 | 4 | `track-...-859eca35` | Y | Ch12: “核心舱的意识结构被撼动了。墙壁上的能量纹路开始闪烁...” | 命名/别名/canonical 未命中 |
| 5 | `location.perseus.arm_mega_ruin` | 英仙臂外侧巨型遗迹 | background | 1 | 1 | 11 | `track-...-a3581375` | Y | Ch11: “英仙臂外侧的巨型遗迹外层见过类似的气味” | 命名/别名/canonical 未命中 |
| 6 | `law.emergency.conscription_act_article_7` | 《边缘星域紧急征召法》第七条 | background | 1 | 1 | 11 | `track-...-a4a0b402` | Y | 未发现 `紧急征召法` / `第七条` | 应转 human mark 或人工保留 |
| 7 | `artifact.silent_ruins.gate_inscription` | 静默遗迹门禁铭文 | background | 2 | 2 | 10 | `track-...-2ca45ac9` | Y | 未发现 `门禁铭文`；仅有宽泛 “静默遗迹” | background/technical 未 archive |
| 8 | `artifact.mega_ruin.space_folding_defense` | 巨型遗迹内部空间折叠防御机制 | background | 3 | 3 | 9 | `track-...-e59c788e` | Y | 未发现 `空间折叠`；Ch11 仅提“巨型遗迹表面的能量纹路...不是防御系统” | background/technical 未 archive |
| 9 | `artifact.ruin_channel.palm_groove` | 手掌凹槽识别系统 | background | 4 | 4 | 8 | `track-...-a5de22c8` | N | 未发现 `手掌凹槽` | background/technical 未 archive |
| 10 | `artifact.quantum.state_data_crystal` | 量子态数据晶体 | background | 4 | 5 | 7 | `track-...-339cee16` | N | 未发现 `量子态数据晶体` | background/technical 未 archive |
| 11 | `artifact.ruin.fibonacci_time_loop` | 斐波那契周期循环（时间闭环） | background | 4 | 4 | 8 | `track-...-67aee033` | N | Ch11: “斐波那契的变体。起始值不是1，而是0.618” | 命名/别名/canonical 未命中 |
| 12 | `artifact.ruin.radiation_pulse_pattern` | 辐射脉冲模式 | background | 4 | 4 | 8 | `track-...-94d03ef9` | N | 未发现 `辐射脉冲` | background/technical 未 archive |
| 13 | `artifact.ruin.nonlocal_spacetime_marking` | 非本地时空标记系统 | background | 4 | 4 | 8 | `track-...-c9320d25` | N | Ch11: “欺骗遗迹系统的时空标记系统” | 命名/别名/canonical 未命中 |
| 14 | `artifact.ruin.time_rewind_mechanism` | 时间回滚机制 | background | 5 | 5 | 7 | `track-...-9969ab98` | N | 未发现 `时间回滚` | background/technical 未 archive |
| 15 | `technology.neural_signal.segmented_storage` | 神经信号分段存储机制 | background | 5 | 5 | 7 | `track-...-74d2350a` | N | Ch11: “神经信号篡改完成”；未出现 `分段存储` | 命名/别名/canonical 未命中 |
| 16 | `artifact.ruin.loop_origin_at_time_zero` | 循环起始点为时间原点 | background | 5 | 5 | 7 | `track-...-0f43e1e4` | N | 未发现 `时间原点` | background/technical 未 archive |
| 17 | `technology.nanite.swarm_self_check_window` | 纳米机械蜂群防御系统——自检窗口机制 | background | 6 | 6 | 6 | `track-...-d4e996b7` | N | 未发现 `纳米机械蜂群` / `自检窗口` | background/technical 未 archive |
| 18 | `signal.fibonacci.frequency_hopping_sequence` | 斐波那契频率跳变序列 | technical | 2 | 2 | 10 | `track-...-c5ab5ca2` | N | Ch11: “以斐波那契序列频率激活的纹路” | 命名/别名/canonical 未命中 |
| 19 | `artifact.ruin_channel.radiation_markings` | 遗迹通道辐射标记 | technical | 4 | 4 | 8 | `track-...-71c9a5b8` | N | 未发现 `辐射标记` / `遗迹通道` | background/technical 未 archive |

## 分类统计

| 分类 | 数量 | 代表项 | 最小根因 |
|---|---:|---|---|
| critical 未刷新/未合并 | 2 | `第7远征队·静默节点`、`相位冲刷机制` | Ch11/Ch12 accepted 正文未出现可推导别名；active human mark 也未促成回收或 resolution。 |
| background/technical 未 archive | 9 | `手掌凹槽识别系统`、`量子态数据晶体`、`辐射脉冲模式`、`遗迹通道辐射标记` | 这些项 `recovery_required=0` 且长期未提及，但 tracking/snapshot 仍 active；archive/过滤阈值没有把 stale background/technical 从 orphan 评分中移出。 |
| 命名/别名/canonical 未命中 | 7 | `英仙臂外侧巨型遗迹`、`非本地时空标记系统`、`斐波那契频率跳变序列` | 正文有可推导提及，但 refresh 检测未映射到 canonical setting_key，或提及落在更宽/更窄的同簇设定名上。 |
| 应转 human mark 或人工保留 | 1 | `《边缘星域紧急征召法》第七条` | 该项已有 active unresolved mark，但正文未回收；Task 138b 需决定它是应人工保留的世界观前提，还是取消强制回收并 archive。 |
| 真实 orphan | 0 | - | 本轮没有证据能证明某项既应强制回收、又无 alias/archive/human-mark 处理路径；真实 orphan 候选应由 Task 138b 在人工保留决策后再判定。 |

## 最小根因

1. `background/technical` stale 项未被 archive 或从 continuity orphan 评分中过滤，是数量主因（9/19）。
2. alias/canonical 同簇刷新仍不完整，是误报主因（7/19），尤其是“斐波那契/频率/时空标记/巨型遗迹外层”这类正文表达与 setting_key 粒度不一致。
3. 自动生成的 active human mark 对本轮 8 项没有形成闭环：既未促使正文回收，也未在有证据时 resolve。
4. critical 中仍有 2 项在 Ch11/Ch12 未出现：`第7远征队·静默节点`、`相位冲刷机制`，需要 Task 138b 明确是强制补回收、合并到其他 setting，还是降级/人工保留。

## Task 138b 决策输入

- 是否先处理 7 个 alias/canonical miss：预期可直接降低误报，不改变正文。
- 是否对 9 个 stale background/technical 执行 archive/评分过滤：必须保护 `critical`、`recurring`、`recovery_required=1` 与 active 人工保留项。
- 是否保留或取消 `《边缘星域紧急征召法》第七条` 的 active human mark：若保留，应作为人工事实源；若不保留，应 archive 而不是继续强迫每章回收。
- 对 2 个 critical 真缺口的最小动作：补 Writer/CD 回收输入、人工标记保留，或设置 canonical merge；不要在 Task 138b 前扩大到 Ch1-Ch20/default run。

## 验收

- 有完整 19 行分类表。
- 每类有数量、代表样例、证据来源和最小根因。
- 明确 Task 138b 的决策输入。

---

## Round 2 / run-4fd48756

> **类型**: 诊断 / 证据整理  
> **状态**: 已完成  
> **前置**: Task 138e 判断 Task 137 仍活跃，下一轮回到 Task 138a

### 数据源与边界

- DB: `.tmp/task138d_ch10_focus_20260628_201716.db`
- Run ID: `run-4fd48756`
- Ch12 accepted version: `v-12-3-a240b75d`
- 最新 Ch12 continuity report: `cont_6ff93a98`，`created_at=2026-06-28 12:34:36`
- Baseline prior round: `run-4ba8de9d`，`orphaned=19`、`health=3.0`
- Current continuity: `health=3.0`、`orphaned=16`、`forgotten=2`、`mismatches=0`
- 本轮只做只读查询与文档证据整理；不改代码、不复跑。

### 只读查询结论

- `project_runs`: `run-4fd48756` 为 `completed`，`completed_chapters=[10, 11, 12]`，`failed_chapters=[]`。
- Ch11/Ch12 run log: `success=true`、`settlement_success=true`、`summary_success=true`、`quality_gate_passed=true`、`settlement_validation_errors=[]`。
- orphan category 分布: `critical=4`、`background=9`、`technical=3`。
- tracking 汇总: 16/16 均为 `setting_tracking.status=active`；16/16 均为 `recovery_required=0`。
- snapshot 汇总: 16/16 均有且仅有 1 条 `setting_snapshots.lifecycle_status=active`。
- active human mark 汇总: 8/16 存在 active unresolved setting mark；这 8 条均由本次 Ch12 continuity report 于 `created_at_chapter=12` 生成，不是复跑前已存在的人工保留事实。

### 16 项分类表

> `HM` 表示 `human_marks.lifecycle_status=active AND resolved_at IS NULL`。本表 16 项均为 `tracking=active`、`snapshot=active(1)`、`recovery_required=0`。

| # | setting_key | setting_name | cat | intro | last | since | tracking_id | HM | Ch11/Ch12 accepted 正文证据 | 分类 |
|---:|---|---|---|---:|---:|---:|---|---|---|---|
| 1 | `artifact.mega_ruin.surface_material` | 巨型遗迹表面材料特性 | critical | 3 | 3 | 9 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-3b6909f4` | Y(ch12) | Ch12: “非欧几何合金碎片的纹理、巨型遗迹表面的能量纹路、门禁铭文的每一个字符” | alias/canonical 未命中 |
| 2 | `organization.expedition.team_7` | 第7远征队·静默节点 | critical | 4 | 7 | 5 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-12ec23a4` | Y(ch12) | 未发现 `第7远征队` / `第七远征队` / `静默节点` | critical 真缺口 |
| 3 | `artifact.ruin.phase_flush_mechanism` | 相位冲刷机制 | critical | 7 | 7 | 5 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-3efb7ff8` | Y(ch12) | 未发现 `相位冲刷` / `冲刷机制` / `相位偏移` | critical 真缺口 |
| 4 | `artifact.mega_ruin.wall_living_properties` | 遗迹墙壁活体特性 | critical | 8 | 8 | 4 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-859eca35` | Y(ch12) | 未发现 `墙壁` / `活体` / `意识结构` / `核心舱`；仅有 `巨型遗迹表面的能量纹路`，不足以指向“墙壁活体特性” | critical 真缺口 |
| 5 | `artifact.ruin_channel.palm_groove` | 手掌凹槽识别系统 | background | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-a5de22c8` | Y(ch12) | 未发现 `手掌凹槽` / `掌纹` / `凹槽识别` | background/technical 未 archive |
| 6 | `artifact.quantum.state_data_crystal` | 量子态数据晶体 | background | 4 | 5 | 7 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-339cee16` | Y(ch12) | 未发现 `量子态数据晶体` / `数据晶体`；Ch11 仅有泛化“量子态信息流” | background/technical 未 archive |
| 7 | `artifact.ruin.fibonacci_time_loop` | 斐波那契周期循环（时间闭环） | background | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-67aee033` | Y(ch12) | 未发现 `时间闭环` / `周期循环`；Ch12 仅有“斐波那契螺旋”视觉 motif | background/technical 未 archive |
| 8 | `artifact.ruin.radiation_pulse_pattern` | 辐射脉冲模式 | background | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-94d03ef9` | Y(ch12) | 未发现 `辐射脉冲`；Ch11/Ch12 的 `脉冲` 为疼痛/按键反馈，非辐射模式 | background/technical 未 archive |
| 9 | `artifact.ruin.nonlocal_spacetime_marking` | 非本地时空标记系统 | background | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-c9320d25` | N | 未发现 `时空标记` / `非本地` / `标记系统` | background/technical 未 archive |
| 10 | `artifact.ruin.time_rewind_mechanism` | 时间回滚机制 | background | 5 | 5 | 7 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-9969ab98` | N | 未发现 `时间回滚` / `回滚机制` / `倒流` | background/technical 未 archive |
| 11 | `technology.neural_signal.segmented_storage` | 神经信号分段存储机制 | background | 5 | 5 | 7 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-74d2350a` | N | Ch12: “神经信号通路切换到了义肢的备用总线”；未出现 `分段存储` | background/technical 未 archive |
| 12 | `artifact.ruin.loop_origin_at_time_zero` | 循环起始点为时间原点 | background | 5 | 5 | 7 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-0f43e1e4` | N | 未发现 `时间原点` / `循环起始点`；`零点七秒` 不是该设定证据 | background/technical 未 archive |
| 13 | `technology.nanite.swarm_self_check_window` | 纳米机械蜂群防御系统——自检窗口机制 | background | 6 | 6 | 6 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-d4e996b7` | N | 未发现 `纳米机械蜂群` / `蜂群防御` / `自检窗口` | background/technical 未 archive |
| 14 | `signal.fibonacci.frequency_hopping_sequence` | 斐波那契频率跳变序列 | technical | 2 | 2 | 10 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-c5ab5ca2` | N | 未发现 `频率跳变` / `斐波那契序列频率`；Ch12 仅有“斐波那契螺旋” | background/technical 未 archive |
| 15 | `technology.fibonacci.phase_shift_parameter` | 斐波那契相位偏移参数 | technical | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-3833a1d1` | N | 未发现 `相位偏移` / `相位偏移参数`；`0.1毫米` 为导线直径，不是参数证据 | background/technical 未 archive |
| 16 | `artifact.ruin_channel.radiation_markings` | 遗迹通道辐射标记 | technical | 4 | 4 | 8 | `track-56fbb888d78f4b29bb1a0e8aa7e6a675-71c9a5b8` | N | 未发现 `辐射标记` / `遗迹通道`；泛化 `标记` 指 SS-047 继承者，不是通道辐射标记 | background/technical 未 archive |

### 分类统计

| 分类 | 数量 | 代表项 | 最小根因 |
|---|---:|---|---|
| critical 真缺口 | 3 | `第7远征队·静默节点`、`相位冲刷机制`、`遗迹墙壁活体特性` | Ch11/Ch12 accepted 正文未出现可推导别名或同簇证据；Ch12 report 新建 P1 human mark，但尚未形成回收。 |
| background/technical 未 archive | 12 | `手掌凹槽识别系统`、`非本地时空标记系统`、`斐波那契相位偏移参数` | 这些项 `recovery_required=0`、tracking/snapshot 仍 active；多数无正文证据，少数只有宽泛同词或 motif，不足以 refresh。 |
| alias/canonical 未命中 | 1 | `巨型遗迹表面材料特性` | Ch12 accepted 明确出现“非欧几何合金碎片”“巨型遗迹表面的能量纹路”，但 tracking `last_mentioned_chapter` 仍停在 Ch3。 |
| human mark/人工保留 | 0 | - | 当前 16 项没有复跑前已存在且仍应人工保留的 setting mark；8 条 active mark 均是本次 report 生成的待回收诊断。 |
| 真实 orphan | 0 | - | 本轮没有证据证明某个非 critical 项必须继续强制回收；真实 orphan 候选应在 Task 138b-R2 对 archive/human mark 策略确认后再判定。 |

### 与上一轮 19 项对比

严格按 `setting_key` 对比，上一轮 19 项中有 4 项不再出现在 `run-4fd48756` 的 orphan 列表，同时新增 1 项 technical orphan，因此总数净减少 3。

| 变化 | setting_key | setting_name | 当前状态 | 可能原因 |
|---|---|---|---|---|
| 消失 | `location.perseus.arm_mega_ruin` | 英仙臂外侧巨型遗迹 | tracking 仍 active，但 `last_mentioned_chapter=12`；旧 active mark 已 `resolved_at=2026-06-28T12:34:25.552185` | Ch12 明确出现“英仙臂外侧巨型遗迹的全息影像/精确位置/坐标”，Task 138c 的 alias/refresh 路径生效。 |
| 消失 | `law.emergency.conscription_act_article_7` | 《边缘星域紧急征召法》第七条 | tracking/snapshot 仍 active，复跑前 Ch9 active mark 仍 unresolved | Task 138c 对非 critical 且已有 active human mark 的 setting 豁免自动 orphan 惩罚，使其转为人工保留/待回收事实，不再计入 orphan。 |
| 消失 | `artifact.silent_ruins.gate_inscription` | 静默遗迹门禁铭文 | tracking/snapshot 仍 active，复跑前 Ch9 active mark 仍 unresolved | 既有 active human mark 豁免自动 orphan 惩罚；Ch12 也出现“门禁铭文的文字/每一个字符”，但 tracking `last_mentioned_chapter` 仍为 2，说明主要消失原因更可能是 human mark 豁免。 |
| 消失 | `artifact.mega_ruin.space_folding_defense` | 巨型遗迹内部空间折叠防御机制 | tracking/snapshot 仍 active，复跑前 Ch9 active mark 仍 unresolved | 既有 active human mark 豁免自动 orphan 惩罚；Ch11 出现“空间折叠中继网络”，但不是“内部空间折叠防御机制”的直接回收。 |
| 新增 | `technology.fibonacci.phase_shift_parameter` | 斐波那契相位偏移参数 | tracking/snapshot active，active human mark 无 | 该 technical stale 项上一轮未进入 19 项，本轮在其他旧项被刷新/豁免后进入 orphan 列表；正文未发现相位偏移证据。 |

因此，如果按“净减少 3”口径说明，净变化为：`英仙臂外侧巨型遗迹` 被 refresh，`《边缘星域紧急征召法》第七条` 与 `静默遗迹门禁铭文` / `巨型遗迹内部空间折叠防御机制` 中的两个以上被 human mark 豁免抵消；但精确 key 级事实是 **4 个旧项消失 + 1 个新项出现 = 净减少 3**。

### 最小根因

1. Task 138c 的 alias/refresh 修复只明确命中 `英仙臂外侧巨型遗迹`，但 `巨型遗迹表面材料特性` 仍未刷新，说明 canonical 同簇刷新仍有缺口。
2. 复跑前已有 active human mark 的非 critical 项已能从 orphan 惩罚中移出；但本次 report 新生成的 8 条 active mark 不能 retroactively 影响同一轮 continuity 评分。
3. 剩余主因已转为 stale background/technical active 项未 archive/过滤（12/16），其中大量没有 Ch11/Ch12 正文证据。
4. critical 真缺口从上一轮 2 个扩大到本轮 3 个：`遗迹墙壁活体特性` 在当前 accepted 正文中没有“墙壁/活体/意识结构/核心舱”证据，不能再按上一轮证据归为 alias miss。

### Task 138b-R2 决策输入

- 继续进入 Task 138b-R2；不建议直接扩大到 Ch1-Ch20/default run。
- 优先处理 12 个 stale background/technical：决定是 archive、评分过滤，还是把新生成 Ch12 active mark 留给下一章回收输入。
- 对 3 个 critical 真缺口分别决策：强制回收输入、人工保留、canonical merge，或降级；不能静默 archive。
- 对 `artifact.mega_ruin.surface_material` 补窄 alias/canonical refresh 规则，证据应来自“非欧几何合金碎片”“巨型遗迹表面的能量纹路”这类明确短语，避免裸 `巨型遗迹` 误匹配。
- 对新增 `technology.fibonacci.phase_shift_parameter` 判定是否属于应 archive 的 technical stale 项；当前正文未发现相位偏移证据。
