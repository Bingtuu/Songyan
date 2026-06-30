# Task 138b: 基于分类结果确定最小动作

> **类型**: 决策 / 任务拆解
> **状态**: 完成
> **前置**: Task 138a

## 背景

Task 138a 已输出 `run-4ba8de9d` Ch12 剩余 19 个 orphan 的分类表。Task 138b 只基于该证据决定下一步最小动作，不直接改代码、不直接复跑。

## 目标

为每一类 orphan 根因确定处理方式：代码修复、阈值/规则调整、human mark、文档收尾或暂不处理。

## 待办

- [x] 对 Task 138a 的每类根因做处理决策。
- [x] 明确本轮做什么、不做什么。
- [x] 明确不直接扩大到 Ch1-Ch20/default run 的理由，除非 Task 138a 证明 Ch12 orphan 已无法通过局部修复继续下降。
- [x] 写明 Task 138c 的验收指标。
- [x] 更新 Task 137 文档与本任务文档。

## 输入摘要

- 数据源: `.tmp/task137_ch10_focus_20260628_183255.db`、`run-4ba8de9d`、Ch12 accepted `v-12-6-75a4b0c7`、continuity report `cont_e754c0a9`。
- Ch12 continuity baseline: `health=3.0`、`orphaned=19`、`forgotten=2`、`mismatches=0`。
- 原始 orphan category: `critical=4`、`background=13`、`technical=2`。
- tracking/snapshot 状态: 19/19 均为 `setting_tracking.status=active`、`recovery_required=0`、`setting_snapshots.lifecycle_status=active(1)`。
- human mark: 8/19 存在 active unresolved setting mark；11/19 无 active human mark。

## 决策表

| Task 138a 分类 | 数量 | 代表项 | 处理方式 | Task 138c 最小动作 |
|---|---:|---|---|---|
| `critical 未刷新/未合并` | 2 | `organization.expedition.team_7`、`artifact.ruin.phase_flush_mechanism` | 代码修复 + human mark 闭环，不 archive、不从评分中过滤。 | 将 active unresolved critical mark 或 critical stale setting 纳入 CreativeDirector/回收输入的高优先级目标；若存在同簇 setting，走 canonical/alias 合并；若仍无正文证据，保留为人工待回收项，不能静默 resolve。 |
| `background/technical 未 archive` | 9 | `artifact.ruin_channel.palm_groove`、`artifact.quantum.state_data_crystal`、`artifact.ruin_channel.radiation_markings` | 阈值/规则调整为主，human mark 分流。 | 对 `category in {background, technical}`、`recovery_required=0`、非 critical/recurring 的长期沉寂项执行 archive 或 ContinuityAuditor 评分过滤；其中有 active human mark 的 `artifact.silent_ruins.gate_inscription`、`artifact.mega_ruin.space_folding_defense` 先进入人工保留/待回收判定，不自动 archive。 |
| `命名/别名/canonical 未命中` | 7 | `location.perseus.arm_mega_ruin`、`artifact.ruin.nonlocal_spacetime_marking`、`signal.fibonacci.frequency_hopping_sequence` | 代码修复，不 archive、不 human mark。 | 扩展正文引用检测与 canonical alias 规则，覆盖“巨型遗迹外层/巨型遗迹”、“斐波那契序列频率/频率跳变序列”、“时空标记系统/非本地时空标记”等同簇表达；匹配必须保留边界与长度约束，避免把宽泛词当成回收。 |
| `应转 human mark 或人工保留` | 1 | `law.emergency.conscription_act_article_7` | human mark + 文档收尾，不做代码静默吞并。 | 明确该项为人工保留世界观前提或取消回收压力：若保留，写入可查询 human mark/等价事实源并从自动 orphan 惩罚中豁免；若不保留，按 background stale archive。Task 138c 默认选择“人工保留并豁免自动惩罚”，除非新证据证明应 archive。 |
| `真实 orphan` | 0 | - | 暂不处理。 | 本轮没有证据证明存在必须强制回收且无法通过 alias/archive/human-mark 处理的真实 orphan；Task 138c 不新增正文重写或大范围 prompt 改造。 |

## 本轮执行边界

本轮做:

- 只把 Task 138a 的五类统计转成处理决策。
- 明确 Task 138c 的代码、规则、human mark 与测试输入。
- 更新 `tasks/138b-orphan-root-cause-decision-DONE.md`、`tasks/137-setting-recycling-closed-loop.md`、`.trae/specs/complete-v51-remaining-tasks/tasks.md`。

本轮不做:

- 不改 `src/`、`prompts/`、数据库或 run 脚本。
- 不运行 pytest、ruff、Ch10-Ch12 复跑或任何长跑。
- 不直接修改 Ch11/Ch12 正文，也不把 critical 缺口通过文档声明为已回收。
- 不把 active human mark 项静默 archive；人工保留必须有 human mark 或等价事实源。

## 不扩大到 Ch1-Ch20/default run 的理由

- Task 138a 已证明 Ch12 剩余 19 个 orphan 主要是局部可处理问题：9 个 stale background/technical、7 个 alias/canonical miss、1 个 human mark 决策项、2 个 critical 回收输入缺口。
- 当前 baseline 是 Ch10-Ch12 聚焦复跑 `run-4ba8de9d` completed，且 settlement/summary/QG 已通过；直接扩大窗口会把 orphan 局部规则问题与长窗口生成波动混在一起，无法判断修复是否有效。
- Ch1-Ch20/default run 成本更高，且会引入 Writer 生成差异、human mark 生命周期和后续章节累积效应；在最小规则闭环未完成前，它不能替代局部因果验证。
- 只有 Task 138c 完成最小修复或 human mark 输入后，才进入 Task 138d 使用副本 DB 复跑 Ch10-Ch12；若 Ch12 orphan 仍无法下降，再回到 138a 分类新证据，而不是直接跳到默认长跑。

## Task 138c 输入

### 改动范围

- 可改: SettingEvaporator/archive 触发、ContinuityAuditor orphan 评分过滤、setting reference/alias 检测、CreativeDirector/回收输入组装、human mark resolve/豁免逻辑，以及对应任务文档。
- 不可改: Writer 直接重写策略、RevisionHandler 整章改写、LLMAuditor/LiteraryAuditor 职责、LangGraph state 契约、settlement 硬校验、数据库事实源规则。
- DB 写入边界: 若需要新增/调整 human mark，必须通过既有 Service/UnitOfWork 或等价事实源路径；不直接拿 DB connection。
- prompt 边界: 仅在回收输入说明不足时补充小范围 prompt/card 文档；不做 V5.1 Prompt 大改。

### 测试范围

- 新增/补强目标单测覆盖三条主分支：stale background/technical archive 或过滤、alias/canonical 刷新、active human mark 人工保留/豁免。
- 必须有负例：critical/recurring/recovery_required=1 不被 archive；active unresolved human mark 不被静默吞掉；宽泛词不能误刷新 canonical setting。
- 建议目标测试: `tests/test_task137_setting_recycling.py`、`tests/test_task135_continuity_governance.py`、`tests/test_continuity_health_governance.py` 中相关用例或新增同域测试。
- Task 138c 只跑目标测试和 lint；Ch10-Ch12 副本 DB 复跑属于 Task 138d。

### 风险边界

- 最大风险是 alias 过宽导致伪回收；必须限制词长、边界、同簇来源，并要求 evidence quote 或 accepted 正文命中。
- stale archive/过滤不能影响 `critical`、`recurring`、`recovery_required=1`、active 人工保留项。
- human mark 豁免不能成为永久屏蔽机制；需要保留 unresolved 状态或明确人工保留类型，供后续章节重新评估。
- 所有改动必须保持 `run-4ba8de9d` baseline 可比较：Task 138d 仍从 Ch10 锚点副本 DB 复跑，不污染主库。

### 验收指标

- 代码/规则层面: 目标测试证明 7 个 alias/canonical miss 可被刷新或同簇识别；9 个 stale background/technical 中无 active human mark 的项可 archive/过滤；active human mark 项不会被静默 archive；2 个 critical 缺口进入高优先级回收输入或人工待回收事实源。
- 文档层面: `tasks/138c-orphan-minimal-fix-DONE.md` 与 Task 137 文档记录实际改动、测试结果、风险边界和是否需要 Task 138d。
- 复跑前置: 目标 pytest 与 `ruff check src/ tests/` 通过后，才进入 Task 138d。
- Task 138d 运行指标: 使用副本 DB 复跑 Ch10-Ch12，至少要求 Ch11/Ch12 settlement、summary、QG 均通过，`settlement_validation_errors=[]`；Ch12 `orphaned` 必须低于 baseline 19，目标降至 8 以下或 health 脱离 `3.0`，否则回到 Task 138a 重新分类剩余项。

## 验收

- [x] 每类 orphan 都有处理决策。
- [x] Task 138c 的改动范围、测试范围和风险边界明确。
- [x] 没有把不确定项静默吞掉；人工保留项必须走 human mark 或等价事实源。

---

## Round 2 / run-4fd48756

> **类型**: 决策 / 任务拆解
> **状态**: 完成
> **前置**: Task 138a-R2

### 输入摘要

- 数据源: `.tmp/task138d_ch10_focus_20260628_201716.db`、`run-4fd48756`、Ch12 accepted `v-12-3-a240b75d`、continuity report `cont_6ff93a98`。
- Ch12 continuity: `health=3.0`、`orphaned=16`、`forgotten=2`、`mismatches=0`。
- Task 138a-R2 分类统计: `critical 真缺口=3`、`background/technical 未 archive=12`、`alias/canonical 未命中=1`、`human mark/人工保留=0`、`真实 orphan=0`。
- 与上一轮对比: 旧项消失 4 个，新增 1 个，净减少 3；Task 138c 的局部修复有效但不足以归档 Task 137。
- 本轮只基于既有证据做下一步最小动作决策；不改代码、不复跑、不运行测试。

### 16 项处理决策表

| # | setting_key | 分类 | 处理方式 | Task 138c-R2 最小动作 |
|---:|---|---|---|---|
| 1 | `artifact.mega_ruin.surface_material` | alias/canonical 未命中 | 代码修复；不 archive、不 human mark。 | 补窄 alias/canonical refresh，允许“非欧几何合金碎片”“巨型遗迹表面的能量纹路”指向表面材料特性；禁止裸 `巨型遗迹`、裸 `能量纹路` 触发刷新。 |
| 2 | `organization.expedition.team_7` | critical 真缺口 | 代码修复 + human mark 待回收；不 archive、不评分过滤。 | 将 stale critical setting 本身纳入 Ch11/Ch12 前置回收输入，不只依赖 continuity report 事后新建 mark；保留 Ch12 P1 mark 作为人工待回收证据。 |
| 3 | `artifact.ruin.phase_flush_mechanism` | critical 真缺口 | 代码修复 + human mark 待回收；不 archive、不评分过滤。 | 同上，作为 critical recovery target 注入 CreativeDirector/回收输入；若未来有同簇机制证据，再走 canonical merge，当前不静默 resolve。 |
| 4 | `artifact.mega_ruin.wall_living_properties` | critical 真缺口 | 代码修复 + human mark 待回收；不 archive、不评分过滤。 | 当前 accepted 正文无“墙壁/活体/意识结构/核心舱”证据，不能再按 alias miss 处理；进入 critical stale 回收输入与人工待回收队列。 |
| 5 | `artifact.ruin_channel.palm_groove` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 非 critical、非 recurring、`recovery_required=0`、长期未提及，允许 archive 或从 orphan 评分中过滤；Ch12 新建 mark 不应把它升级为人工保留。 |
| 6 | `artifact.quantum.state_data_crystal` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 同上；“量子态信息流”不是数据晶体证据，不能 refresh。 |
| 7 | `artifact.ruin.fibonacci_time_loop` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 同上；“斐波那契螺旋”只是视觉 motif，不作为“时间闭环/周期循环”证据。 |
| 8 | `artifact.ruin.radiation_pulse_pattern` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 同上；疼痛/按键反馈中的 `脉冲` 不作为辐射脉冲模式证据。 |
| 9 | `artifact.ruin.nonlocal_spacetime_marking` | background/technical 未 archive | 规则调整；暂不处理 alias。 | 当前 Ch11/Ch12 无 `时空标记/非本地/标记系统` 证据，按 stale background 处理。 |
| 10 | `artifact.ruin.time_rewind_mechanism` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 长期未提及且无回滚/倒流证据，允许 archive 或 orphan 评分过滤。 |
| 11 | `technology.neural_signal.segmented_storage` | background/technical 未 archive | 规则调整；不 human mark 保留。 | “神经信号通路切换”不是“分段存储”证据，按 stale background 处理。 |
| 12 | `artifact.ruin.loop_origin_at_time_zero` | background/technical 未 archive | 规则调整；不 human mark 保留。 | `零点七秒` 不是时间原点证据，按 stale background 处理。 |
| 13 | `technology.nanite.swarm_self_check_window` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 无纳米机械蜂群/自检窗口证据，按 stale background 处理。 |
| 14 | `signal.fibonacci.frequency_hopping_sequence` | background/technical 未 archive | 规则调整；暂不处理 alias。 | Ch12 只有“斐波那契螺旋”，无频率跳变证据；按 stale technical 处理。 |
| 15 | `technology.fibonacci.phase_shift_parameter` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 新增 technical stale 项；`0.1毫米` 是导线直径，不是相位偏移参数证据，允许 archive 或过滤。 |
| 16 | `artifact.ruin_channel.radiation_markings` | background/technical 未 archive | 规则调整；不 human mark 保留。 | 泛化 `标记` 指 SS-047 继承者，不是通道辐射标记；按 stale technical 处理。 |

### 分类决策统计

| 分类 | 数量 | 本轮处理方式 | 说明 |
|---|---:|---|---|
| critical 真缺口 | 3 | 代码修复 + human mark 待回收 | 不 archive、不评分过滤；关键点是让 stale critical 在章节生成前进入高优先级回收输入，而不是等 Ch12 continuity report 事后生成 mark。 |
| background/technical 未 archive | 12 | 规则调整为主 | 非 critical/recurring、`recovery_required=0`、长期未提及且无 accepted 正文证据；应 archive 或从 orphan 评分中过滤。Ch12 本轮新建 mark 只作为诊断，不升级为人工保留。 |
| alias/canonical 未命中 | 1 | 代码修复 | 只补 `artifact.mega_ruin.surface_material` 的窄证据短语；不恢复上一轮已消失的大范围 alias 扩展。 |
| human mark/人工保留 | 0 | 暂不处理 | 当前没有复跑前已存在且应人工保留的 setting mark；8 条 active mark 均为本轮 report 新建诊断。 |
| 真实 orphan | 0 | 暂不处理 | 没有证据证明非 critical 项必须强制回收；待 138c-R2 完成 archive/过滤后再由 138d/138a-R3 复核。 |

### 本轮执行边界

本轮做:

- 将 Task 138a-R2 的 16 项分类转成 Task 138c-R2 可执行决策。
- 明确 3 个 critical 真缺口、12 个 background/technical stale 项、1 个 alias/canonical miss 的处理方式。
- 更新 `tasks/138b-orphan-root-cause-decision-DONE.md`、`tasks/137-setting-recycling-closed-loop.md`、`.trae/specs/complete-v51-remaining-tasks/tasks.md`、`.trae/specs/complete-v51-remaining-tasks/checklist.md`。

本轮不做:

- 不改 `src/`、`prompts/`、数据库、run 脚本或测试文件。
- 不运行 pytest、ruff、Ch10-Ch12 复跑、Ch1-Ch20/default run。
- 不直接修改 Ch11/Ch12 正文，不把 critical 缺口通过文档声明为已回收。
- 不把 Ch12 report 新建的 non-critical human mark 当成人工保留事实；人工保留必须是复跑前已有且明确需要保留的事实源。

### 为什么仍不扩大到 Ch1-Ch20/default run

- `run-4fd48756` 已证明局部修复仍能让 orphan 从 19 降到 16，说明尚未到“局部修复无法继续下降”的阶段。
- 剩余 16 项的根因仍高度集中: 12 个 stale background/technical、3 个 critical 回收输入缺口、1 个窄 alias miss；这些都可以通过局部规则/输入修复验证。
- Ch10-Ch12 已 completed，settlement/summary/QG 均通过，`settlement_validation_errors=[]`；当前问题是 continuity orphan 收口，不是生成链路可运行性。
- 直接扩大到 Ch1-Ch20/default run 会引入 Writer 生成波动、后续章节累积、人为 mark 生命周期和 default 配置差异，无法隔离 138c-R2 的因果效果。
- 正确顺序仍是 Task 138c-R2 最小修复和目标测试后，再由 Task 138d-R2 使用副本 DB 复跑 Ch10-Ch12；若 orphan 仍不下降，再回到 Task 138a-R3 分类新证据。

### Task 138c-R2 输入

#### 改动范围

- 可改:
  - ContinuityAuditor orphan 评分过滤或 SettingEvaporator/archive 触发，专门处理 non-critical、non-recurring、`recovery_required=0` 的 stale background/technical 项。
  - CreativeDirector/ContextManager 回收输入组装，让 stale critical setting 在章节生成前进入高优先级回收目标，不依赖同章 continuity report 事后新建 mark。
  - setting reference/alias 检测，只补 `artifact.mega_ruin.surface_material` 的窄 canonical 证据短语。
  - human mark 解释逻辑: 区分“复跑前已有人工保留 mark”和“当前 report 新建诊断 mark”，后者不自动豁免 non-critical stale orphan。
- 不可改:
  - Writer 直接重写策略、RevisionHandler 整章改写、LLMAuditor/LiteraryAuditor 职责边界。
  - settlement numerical ledger 硬校验、SQLite 事实源规则、LangGraph state 只存 ID 的契约。
  - 不新增 Genre/Mode/Agent/Workflow 节点，不做 V5.1 Prompt 大改。
- DB 写入边界:
  - 如需调整 human mark 或 lifecycle，必须走既有 Service/UnitOfWork 或 repository 路径；Agent 不直接拿 DB connection。
  - `setting_snapshots` 仍保持 INSERT-only；不得 UPDATE 快照正文状态。

#### 测试范围

- 目标单测覆盖:
  - 12 个 stale background/technical 类型的 archive 或 orphan 评分过滤。
  - 3 个 critical stale setting 进入章节生成前回收输入，且不被 archive/过滤。
  - `artifact.mega_ruin.surface_material` 可由“非欧几何合金碎片”“巨型遗迹表面的能量纹路”刷新。
  - 当前 report 新建的 non-critical human mark 不等同于人工保留，不应永久豁免 stale orphan。
- 负例必须覆盖:
  - `critical`、`recurring`、`recovery_required=1` 不被 archive/过滤。
  - 裸 `巨型遗迹`、裸 `能量纹路`、视觉 motif `斐波那契螺旋`、`0.1毫米`、泛化 `标记` 不能误刷新对应 canonical setting。
  - 复跑前已有 active unresolved 人工保留 mark 仍可豁免自动 orphan 惩罚，不能被静默 archive。
- 建议目标测试文件:
  - `tests/test_task137_setting_recycling.py`
  - `tests/test_task135_continuity_governance.py`
  - `tests/test_continuity_health_governance.py`
  - 必要时新增同域小测试，不新增重型 E2E。
- Task 138c-R2 完成前只跑目标测试与 `ruff check src/ tests/`；Ch10-Ch12 副本 DB 复跑属于后续 Task 138d-R2。

#### 风险边界

- alias 过宽是最大误报风险；所有新 alias 必须有具体短语、长度/边界约束和 accepted 正文证据。
- stale archive/过滤不能吞掉关键设定；critical/recurring/recovery_required 始终保留。
- 当前 report 新建 mark 若被当成永久豁免，会掩盖 stale background/technical；138c-R2 必须区分诊断 mark 与人工保留 mark。
- critical 回收输入不能变成正文硬改写；它只提高规划/回收优先级，最终是否回收仍由生成与审查证据判断。
- 继续保持与 `run-4fd48756` baseline 可比较；后续复跑使用副本 DB，不污染主库。

#### 验收指标

- 代码/规则层面:
  - 目标测试证明 12 个 stale background/technical 类项可被 archive 或从 orphan 评分中过滤。
  - 目标测试证明 3 个 critical stale 项不会被 archive/过滤，并进入章节生成前的高优先级回收输入或人工待回收事实源。
  - 目标测试证明 `artifact.mega_ruin.surface_material` 的窄 alias/canonical refresh 生效，且宽泛词不误命中。
  - 目标测试证明当前 report 新建 non-critical mark 不会被误当成人工保留，复跑前已有人工保留 mark 仍受保护。
- 文档层面:
  - `tasks/138c-orphan-minimal-fix-DONE.md` 与 Task 137 文档记录实际改动、测试结果、风险边界和是否进入 Task 138d-R2。
- 复跑前置:
  - Task 138c-R2 目标 pytest 与 `ruff check src/ tests/` 通过后，才进入 Task 138d-R2。
- Task 138d-R2 运行指标:
  - 使用副本 DB 复跑 Ch10-Ch12，Ch11/Ch12 settlement、summary、QG 均通过，`settlement_validation_errors=[]`。
  - Ch12 `orphaned` 必须低于 `run-4fd48756` baseline 16；目标降至 8 以下或 health 脱离 `3.0`。
  - 若 orphan 未下降或出现新阻断，回到 Task 138a-R3 重新分类，不直接扩大到 Ch1-Ch20/default run。
