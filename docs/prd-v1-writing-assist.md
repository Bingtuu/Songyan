# Songyan V1.0 产品需求：人主导的写作助手

- **状态：** 规划稿。2026-10-26（Asia/Shanghai）。待 owner（diupy / Bingtuu）接受。
- **本文做什么：** 锁定 V1.0 的产品定义、对象、工作流、命令表面和分阶段出口。接受之前不开实现。
- **本文不做什么：** 不改代码，不把包版本升到 `1.0.0`，不打名为 `v1.0` 的 git tag。当前 tip 仍是 **v0.5**（包版本 `0.5.0`）。
- **产品代际名 vs 包版本：** 文中的「V1.0」是写作助手这一代产品的规划名称。它不是 `pyproject.toml` 里的版本号。

读者：owner，以及接受本文之后按切片实现的人。架构方向仍以 [ADR-0001](adr/0001-plan-first-facts.md) 为准。Plan-first 阶段 A–C 已在 [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 收束；本文是下一代产品框架，不重开那 90 天的召回实验。

材料来自 2026-10-26 的写作助手设计包，以及工作台调研附录。工作台包当时的口径是「事实工作台，写作为可选」。Owner 已改口：**保留现有管线能力，主定位是人主导的写作助手**。调研里的对象和确认闸门仍然有效；「几乎不写正文」不再是产品定义。本文是现行口径。

文中命令凡现网还没有的，一律标 **`[proposed]`**。没有实现的能力，对外 README 不得写成「已经支持」。

---

## 1. 愿景

**一句话：** Songyan 是人主导的连载写作助手。结构化 Canon 管住设定与承诺；单章多草稿抽卡用来探索写法；确认闸门把抽取变成可审计事实。静默改 Canon 不在产品里。自动写完一本小说不在产品里。

### 1.1 落点

三条路里只取中间这条。

| 路 | 含义 | V1.0 |
|----|------|------|
| 自动成书 | 无人值守连载，闸门绿即当写完 | 不做 |
| 纯设定台账 | 只记账，几乎不生成正文 | 过窄；写作辅助留在产品里 |
| **写作助手 + Canon** | 人定方向和终稿；Songyan 出草稿、管事实、做审读 | **V1.0** |

现有 `run`、质量门、结算、导入、计划卡都留着，当引擎和诊断。作者每天走的路径改成 Canon、检查、抽卡和短续写。

### 1.2 为什么停在这里

两份已经有的记录把「再自动跑一轮」排除掉了：

- Plan-first 阶段 C（都市灵异）召回 1/5，退出未过。Owner 已接受薄封装：**人维护事实圣经，模型按圣经写。**
- 《轨道蜃景》Ch1–10：流水线 10/10 accepted，质量门 / 结算 / 导出为绿；DG-1 失败（平均 revision 1.7，ContextEmergency 十章都出现）。跨章时间线、专名、复读和尺度在人工阅读里站不住。**这是管线证据，不是文学验收。** 详见第 12 节。

过程门禁抓得住「这一章有没有走完」。它抓不住全书编辑纪律，也代替不了文学所有权。

---

## 2. 非目标

V1.0 不做下面这些事。它们不是「以后第一刀」，解冻需要 owner 另说。

1. 把多智能体无人值守连载当成作者主路径，或把「写完整本」写成卖点。
2. 把产品收成没有正文的纯 wiki。
3. 默认句级幽灵补全。脚手架停在章纲、设定、冲突报告、整章草稿变体。
4. 抽取、结算摘要、审读建议在无人确认时写入 Canon。
5. 为追召回再堆题材专用检查器。窄检查保持薄封装。
6. 在 Phase 0–3 做 Git 式整树 Canon 分支（`branch`）。
7. 用一次开放式 LLM「找全书漏洞」代替结构化 `check`。
8. 把 Ch1–10 或任何 `run --auto-confirm` 的绿灯写成文学质量已验证。
9. Obsidian 当作唯一库，或云端锁定正文。
10. 在命令尚未落地时，对 README 声称已支持抽卡。

---

## 3. 用户与成功

### 3.1 谁在用

| 人 | 角色 |
|----|------|
| 连载作者（主） | 自己维护 Canon，挑草稿，改终稿，确认事实。能配置本机 CLI 和模型 API key。 |
| 责编 / 审读（次） | 只看冲突和承诺，不负责生成。走 W6。 |
| 维护者 | 跑 `doctor`、`run` 冒烟、备份和诊断包。不代表作者日常。 |

空白开书、导入旧稿、日更、改一处硬设定、清伏笔债，都是同一个人在不同天的事，所以工作流按场景拆，不按「另一种产品」拆。

### 3.2 成功指标

优化作者对账本的控制和单章探索，不用日产字衡量。

| ID | 指标 | 初期怎么看 | 备注 |
|----|------|------------|------|
| M1 | 每周确认入典的事实数 | 有记录，且 dismiss 比例说得通 | 不是越多越好 |
| M2 | 冲突关闭周期 | Issue 从 open 到 closed 或 dismiss 有记录 | 含误报驳回 |
| M3 | 开放伏笔年龄 | P50 不超过约定章数 | 章数按书另定，不写死一个全题材数字 |
| M4 | 抽卡采纳分布 | 被 pick 的 slot 不全是 1 号 | 用来发现 N 稿塌成同一篇 |
| M5 | 人改率 | pick 之后工作正文相对原稿的 diff 非空比例 | 所有权的代理，不是文学分 |
| M6 | `today` 打开天数 | 狗食周 ≥ 3 天 | 主观留存，要记日志 |
| M7 | 单章成本 | 预算内完成率，含 N 个 variant | 口径沿用 ¥2/M 输入、¥8/M 输出，这是估算不是账单 |
| M8 | pending 泄漏 | **0** 条未确认抽取进入 `load_chapter_plan_bible` | 硬门，进 CI |
| M9 | 文学 | 人工抽读 | 不进自动绿灯 |

**不用作主 KPI：** 日产字、accepted 章数、质量门通过率、星标、参数量。质量门通过率仍是工程回归指标，只是不再拿来代表书写得好。

---

## 4. 已锁定的默认

这些是 V1.0 规划的决定。Phase 2 开工前 owner 仍可改数字；实现时按这里写，不再把它们当开放题。

| 决定 | 内容 |
|------|------|
| 交互 | **CLI 优先。** 继续 Python Click。TUI / 本地 Web 在 V1.0 之后。 |
| 抽卡粒度 | **章内 Variant。** 每章 N 个并列草稿槽，共享同一章号和同一份 Canon 快照。 |
| 默认 N | **2。** `variant generate --n` 的默认值。作者可显式加大，并受 `--budget-cny` 约束。 |
| 入典 | **Confirm-to-canon。** 写入 Canon 的作者路径只有 triage / confirm。 |
| `run` | **保留命令，降为引擎 / 冒烟 / 长窗实验。** 作者日用卡片不推荐 `run --chapters 1-N --auto-confirm`。 |
| 阶段顺序 | **Phase 0 → 1 → 2 → 3**，出口见第 9 节。不并行铺 Web。 |
| Phase 1 优先 | **Canon + `check` + triage，并且包含 W0（零生成的事实管理）。** |
| 重审计 | 文学向重审计默认只对 **picked** 稿。其余 variant 可只带轻分数。 |
| 调试旧结算 | 允许维护者开关把抽取写回**运行时结算库**做对照。默认关。这个开关**不能**把未确认行写成 `approval_status=approved` 的 plan 行。 |

Git 式 Canon 分支不在上述默认里。口语里的「分支」在文案中写成「草稿变体 / 抽卡」。

---

## 5. 对象模型

**正文草稿不是唯一真相。** 经 Settlement（确认入典）的 Fact 才是 Canon。草稿可以改、可以丢。Canon 的变更必须显式、可回溯、带来源。系统不因为生成了一稿就改写权威事实。

### 5.1 对象

| 对象 | 定义 | 与 v0.5 的关系 |
|------|------|----------------|
| **Project** | 一部小说工程：元数据、体裁模板、SQLite 绑定 | 已有。`create-project` / `list-projects` |
| **Canon / Fact Bible** | 已确认的权威事实：硬规则、实体属性、地名、道具、关系 | 部分已有。真源是 `approval_status=approved` 的 plan 事实行。旧结算库只作对照 |
| **Timeline** | 有序故事事件 + 故事历 / 历史历锚点 | 半有。`plan_events`、`plan_time_anchors` 在；作者向时间线阅读视图要补 |
| **CharacterState** | 人物在章索引上的切片：生死、境界、关系、知情 | 运行时已有。语义要和 Canon 的有效章区间对齐，不能另养一套权威 |
| **Promises** | 叙事承诺债务。作者看见的是现网状态：`planted` / `due` / `overdue` / `resolved` / `archived` | 已有 `foreshadowings`（含 `resolved_chapter` / `resolved_version_id`，现为 write-only）。要变成作者看得见的队列 |
| **Chapter** | 章槽：序号、作者可见状态、当前工作正文指针 | 已有章节与版本。作者状态机是新建的一层解释 |
| **Variant** | 章内抽卡槽。一个 slot 一份草稿 | **新建。** 不是 Git 分支 |
| **ConsistencyReport** | 结构化问题列表：证据跨度、严重度、建议动作 | 部分已有（run report、continuity、`plan_fact_gate`）。缺统一的作者向 `check` 报告 |
| **Settlement / Proposal** | 确认入典的动作与队列：抽取或审读产生提案，人 triage 之后才写入 Canon | 语义要改建。今天 `SettlementExtractor` 仍写结算库，不写 plan canon |
| **Plan Card** | 章级事实圣经：必须提及、主张、线索 | 已有。W2 的章前输入 |

### 5.2 Canon 条目最小字段

```text
fact_id
kind                 entity | attribute | event | rule | promise | relation
subject, key, value
valid_from_ch
valid_to_ch | null
hardness             hard | soft          # 死生、境界、专名 对 动机、秘密
approval_status      pending | approved | rejected | superseded
source               plan | human | extract_proposal
evidence_refs[]      # 章号、段落锚、variant_id
created_at, confirmed_by, note
```

`hardness=hard` 的变更会把覆盖到的章标成 `stale`（W4）。`soft` 可以改注记而不强制全章重写。知情分层（谁知道秘密）只预留字段，V1.0 不做成完整 POV 系统。

### 5.3 Chapter 状态

```text
empty → outlined → drafting → variants_ready → picked → human_rewriting
  → in_review → needs_settlement → settled → stale
```

允许的跳转：`picked → in_review`（人几乎没改）；`settled → stale`（事后改了 Canon）；`stale → drafting`（按新 Canon 重抽）。`stale` 只是标记。系统不自动改正文。

### 5.4 Proposal 状态

```text
proposed → accepted → approved（进入 Canon）
         → edited → approved
         → dismissed（可带 suppress_rule）
```

没有自动边进入 `approved`。`accepted` 表示人在 triage 里接受了这条提案；`approved` 表示它已经写入 Canon。一次 confirm 可以连续完成这两步。若实现把它们合成一个状态，仍然必须保证：还没写入 Canon 的提案，下一章上下文读不到。事实行上的 `rejected` 对应提案的 `dismissed`，不入 Canon。`dismiss` 是一等动作，用来压误报，而不是为了把召回数字做高去加题材硬规则。

### 5.5 Variant

```text
variant_id, project_id, chapter_no
slot_index            1..N
status                generated | picked | abandoned | archived
parent_canon_fingerprint
prompt_seed / diversify 说明
prose 存储引用
scores                可选：过程门、plan gate、备注
created_at, cost_cny_est
```

规则：

- 同一章同一时刻最多一个 `picked`。
- `pick` 只移动工作正文指针。它不结算，也不改 Canon。
- 生成时绑定 `parent_canon_fingerprint`。Canon 变了之后，variant 标 `stale_vs_canon`：仍可阅读，不能当作默认续写底稿。
- `abandon` 是软删除，成本记录留下。
- 新的 variant 不得静默覆盖已 `picked` 的正文。

### 5.6 抽卡槽和 Git 分支

| | 章内 Variant（V1.0） | Git 式 Canon Branch（V1.0 之后） |
|--|----------------------|----------------------------------|
| 分叉什么 | 一章里的 N 份草稿 | 整棵 Canon 和后续章历史 |
| 适合 | 单章试写法、试情节分叉 | 重大设定分叉、平行卷 |
| V1.0 | **采用** | **不做** |

平行设定若在 V1.0 就必须试，用另一个 Project（或复制一份本地 DB）。不提供 `branch create|switch|merge`。

---

## 6. 确认入典

1. 任何模型抽取、结算摘要、审读建议，默认是 **Proposal**，不是 Canon。
2. 作者写入 Canon 的路径：`canon triage` / `canon confirm`。维护者脚本里的强制开关不进入默认作者路径。
3. `SettlementExtractor` 的输出在助手主路径上进入提案队列。下一章上下文只读已确认 Canon 和已批准计划卡。这与 ADR-0001、薄封装一致，并把「抽取不进 plan canon」做成作者可操作的队列。
4. 旧结算库可以留下，供 `canon show --include-legacy-settlement` 只读对照，条目标 `untrusted_until_confirmed`。
5. `status` / `today` 要能看见本会话的提案数、新确认数、未关闭冲突数。避免作者以为「选了一稿」等于「设定已更新」。

**当前代码还没翻转。** 本规划不改变 v0.5 里 `run` 的行为。权威路径的改建是 Phase 1 的实现切片，并且要用测试钉住 M8：未 confirm 的抽取不出现在 `load_chapter_plan_bible`。在那之前，结算库仍是运行时观测；助手文档不再把它写成下一章的权威事实。

---

## 7. 工作流 W0–W6

七条流共享同一套对象和确认闸门。差别是这一天要不要生成、先文还是先典、动的是正文还是账本。

| ID | 名字 | 何时用 | 生成正文？ | 默认会入典？ |
|----|------|--------|------------|--------------|
| **W0** | 只典 | 整理设定、核对数据、今天不写章 | 否 | 只有人 confirm 才入 |
| **W1** | 抽卡后沉淀 | 想先看几种写法，再锁事实 | 是（章内 N 稿） | 两次提案都要人确认 |
| **W2** | 先典后续 | 日更；本章计划卡已经能用 | 是（默认 1 章） | 章末一次提案，人确认 |
| **W3** | 导入旧稿 | 已有书稿要进工程 | 导入本身不新写；续写可选 | replay 抽取仍是提案 |
| **W4** | 改典涟漪 | 硬事实改了，要看哪些章过期 | 否（人决定改文或改典） | 改典本身就是一次 confirm |
| **W5** | 承诺债务 | 清点伏笔、承诺、未兑现的钩子 | 否 | 销账 / 作废要人确认 |
| **W6** | 只审 | 责编或作者只想要一份问题清单 | 否 | **默认不入典** |

### 7.1 W0 — 只典：事实管理 + 审读，零生成

**何时用：** 建圣经、改硬规则、看时间线和人物切片、跑一致性。这一天的产出是账本和报告，不是新章节。

**步骤：**

1. `project new` 或打开已有 Project。可选 `project init`：3–10 条硬规则草案进入 triage，不直接 `approved`。成功标准是十分钟内能打印一页「硬规则 + 主角 + 核心冲突」。
2. `canon show` / `canon edit` 维护事实、时间锚、人物状态。
3. `check` 出 ConsistencyReport。`review` 把问题列成清单。
4. 人决定改事实、驳回误报，或什么都不改。
5. `today` 看未关闭项和开放承诺。

**零生成：** 不调用 `variant generate`、`chapter continue`、`run`。W0 是 Phase 1 的第一条狗食路径。

### 7.2 W1 — 抽卡 → 提案沉淀 → 人改 → 审读 → 再确认

**何时用：** 灵感向；设定还薄；想比较同一章的不同写法。Phase 2 起抽卡可用。Phase 1 可以用外置的一份草稿走「提案 → 人改 → check → 再确认」，用来验证闸门，不假装已经有多稿槽。

**快乐路径：**

```text
variant generate (N=2) → pick → extract propose → canon triage
  → 人在外置编辑器改工作正文 → check / review
  → extract propose（只提 delta） → canon triage → settled
```

| 步 | 人在做什么 |
|----|------------|
| 生成 | 设定 N 和预算 |
| pick | 做文学选择。pick 不是入典 |
| 第一次 triage | 决定哪些事实成真 |
| 改稿 | 结构、文笔、删复读。可用 `mark` 记下禁忌 |
| 审读 | 决定改文、改典，或回到抽卡 |
| 第二次 triage | 确认人改带来的新事实 |

**失败与恢复：**

| 失败 | 恢复 |
|------|------|
| 预算在生成中途耗尽 | 降低 N；重审计只跑 picked；`--budget-cny` |
| ContextEmergency | 本模式已是单章；仍超则减注入的 lore / marks |
| N 稿几乎相同 | 加强 diversify，或先补章拍再生成 |
| 把 pick 当成已入典 | `status` 显示 pending；续写可要求本章已 settled |
| 抽取写进了圣经 | 产品禁止。测试钉住 pending 不进 bible |
| check 把体裁惯例当冲突 | `dismiss`，不为此加题材硬编码 |
| 人改和 Canon 打架 | 改文、改典，或新开 variant。不开 Git 分支 |
| 过程门绿、读起来不行 | `review` 可列复读和专名启发式。不宣称可发表 |

### 7.3 W2 — 先典 / 计划 → 短续写 → 共审 → 下一章

**何时用：** 日更；圣经或本章计划卡已经够硬。这是 plan-first 薄封装的产品化主路径，在 Phase 3 闭合。

**快乐路径：**

```text
canon / plan(ch N) → today → chapter continue（默认 1 章，可选 --variants 2）
  → check / review（人机一起看） → propose → canon triage → settled
  → 准备 ch N+1
```

- 章前输入是已批准计划卡（必须提及、主张、线索），经现有 `load_chapter_plan_bible` 注入。
- `continue` 的 `--count` 默认 **1**。助手文档不鼓励无审连跑超过 3 章。
- 缺关键硬约束时，`continue` 拒绝或强警告（`--require-plan`）。
- `plan_fact_gate` 的失败进 `review`，不自动改文、不自动入典。
- 召回不够时加人维护的卡，不加题材检查器丛林。阶段 C 的 1/5 是这个策略的证据，不是待修复的召回 KPI。

### 7.4 W3 — 导入书稿 → 抽取提案 → triage → Canon

**何时用：** 已有正文要变成工程，而不是从空模板开写。

```text
import ingest → segment → confirm → replay / synthesize → publish
  → 抽取结果进入提案队列 → canon triage → check
  → 可选：问题章走 W1，或从某一章起走 W2
```

现网 `import` 子命令保留（`ingest` / `segment` / `confirm` / `status` / `replay` / `synthesize` / `publish`）。`publish` 之后 `run` 才解除阻塞，这条工程闸门不变。

助手模式多加一条：**replay / synthesize 抽出的事实默认不可信。** 它们进提案，人 triage 之后才进 Canon。

**真实 LLM 的「导入后再续写」尚未验收**（见 [STATUS](STATUS.md)）。W3 可以承诺「能把书稿导入并交给人确认事实」。它不承诺「导入后的续写质量已验证」。续写是可选步骤，落在 Phase 3 的 `chapter continue`，在验收报告出现之前文档保持降级。

### 7.5 W4 — Canon 变更 → 标脏 → 检查受影响章 → 人改文或改事实

**何时用：** 改了硬属性（生死、专名、时间锚、有效章区间），需要知道哪些章和草稿过期。

```text
canon edit / confirm（hard）
  → 覆盖到的 Chapter 与 Variant 标 stale / stale_vs_canon
  → check 受影响范围
  → 人选择：改正文，或再改事实，或驳回
```

系统不自动重写正文，也不自动重抽卡。人可以随后对某一脏章进入 W1。`soft` 事实（动机、秘密注记）默认不把整章标脏，除非作者显式要求。

受影响范围按 `valid_from_ch` / `valid_to_ch` 和 `evidence_refs` 里的章号计算。算不到的章节不猜测成脏。

### 7.6 W5 — 伏笔与承诺债务队列

**何时用：** 要看已经埋下、尚未兑现或已经作废的叙事承诺。这是账本工作，不是生成工作。

- 数据来自现有 `foreshadowings`，并在 Canon 里用 `kind=promise` 对齐。状态沿用现网 `planted`（已埋）、`due` / `overdue`（开放债务）、`resolved`（已兑现）、`archived`（作废或撤下）。不另起一套 plant / open / paid / broken 枚举。
- `today` 列出 open 项和年龄（相对当前章）。
- 兑现或作废是一次确认：人给出章号和证据，经 triage / confirm 写入，而不是模型在结算时静默销账。
- 现有 `resolved_chapter` / `resolved_version_id` 列保持可追溯。V1.0 不把它们升级成新的质量门口径。
- M3 用这条队列计算，不另造一套伏笔表。

V1.0 不单开 `promise` 命令组。表面是 `today` 加 `canon show --kind promise`（`[proposed]`）。

### 7.7 W6 — 只审：默认不入典

**何时用：** 责编要一份问题清单；作者想先看冲突，今天不改圣经。

```text
check → review → ConsistencyReport（Markdown，可选 JSON）
```

`check` / `review` **不调用** confirm，不把抽取写入 Canon，不改正文。报告里可以建议「若要入典，离开 W6，改走 `canon triage`」。这个建议不是默认动作。

W6 与 W0 的差别：W0 包含事实的编辑和确认；W6 停在只读审读。

### 7.8 切换

| 从 | 到 | 条件 |
|----|----|------|
| W0 | W2 | 本章硬约束已经确认，作者准备短续写 |
| W1 | W2 | 该章 `settled`，下一章改为先写计划卡 |
| W2 | W1 | 这一章不满意，要重抽。旧 picked 归档，Canon 不删 |
| W3 | W0 / W1 / W2 | triage 之后。续写仍受「导入续写未验收」约束 |
| W4 | W0 或 W1 | 人选定改事实或重写脏章 |
| W5 | W0 | 销账需要 confirm |
| W6 | W0 | 人显式开始 triage |
| 任意 | W6 | 任何时刻都可以只跑检查 |

切换时，未确认提案不得静默并入 Canon。同一 Project 里可以主线走 W2、某一章走 W1。`today` 说明建议的下一步，不自动开跑。

### 7.9 冲突出来之后

`check` 给出问题后，作者四选一：

| 策略 | 动作 |
|------|------|
| A 改事实 | `canon edit`，写上有效章区间；相关章 `stale`（W4） |
| B 改正文 | 改工作正文；需要新写法时再 `variant generate` |
| C 另开变体 | 新的章内 Variant。不是 Git branch |
| D 驳回误报 | `dismiss`，可选 suppress |

审读阶段不自动改 Canon，也不自动改正文。

---

## 8. CLI 表面

MVP 只有 CLI。新分组是 **`[proposed]`**，实现时用别名或薄包装调用现有命令。与现网不一致的名字都还没落地。

### 8.1 作者向命令树（proposed）

```text
songyan
├── doctor
├── project new | list | init          # new/list 映射 create-project / list-projects
├── chapter list | new | continue | status
├── variant generate | list | diff | pick | abandon
├── canon show | edit | triage | confirm
├── check
├── review
├── status
├── today
└── branch                             # deferred，Phase 0–3 不实现
```

### 8.2 保留的现网命令

这些命令继续存在，测试保持绿。助手日用卡片不把它们当主路径。

| 命令 | V1.0 归宿 |
|------|-----------|
| `doctor` | 环境自检，不变 |
| `create-project` / `list-projects` | 保留；`project new` / `project list` 是别名 |
| `run` | 保留。定位改为生成引擎、冒烟、长窗实验 |
| `report` / `metrics` / `five-gate` / `t9` | 诊断与过程门报告。`check` / `review` 可以引用其中的信号 |
| `export` / `backup` / `restore` / `bundle-run` | 保留 |
| `import ingest\|segment\|confirm\|status\|replay\|synthesize\|publish` | 保留，服务 W3 |
| `profile show\|diff\|validate\|upsert\|history\|rollback` | 体裁配置，不是每天写作的主路径 |
| `mark add\|list\|remove\|update-priority` | 人的偏好和禁忌，喂给生成与审读 |
| `index` | 已有 RAG 索引。助手 MVP 不依赖它；加强预算化设定注入放到 V1.0 之后 |

`run` 的帮助文本在实现时加上一句：多章 `--auto-confirm` 适合管线验证；文学创作使用 `chapter` / `variant` / `canon`。这句文案随 Phase 0/1 的命令切片落地，本规划不改帮助文本。

### 8.3 行为约束（实现时不得改语义）

| 命令 | 约束 |
|------|------|
| `variant generate --n` | 默认 **2**。只读 Canon 快照。不自动 `pick`。费用按 slot 记账 |
| `variant pick` | 只改工作正文指针 |
| `variant abandon` | 软删除。若丢掉的是当前 picked，章回到 `variants_ready` |
| `chapter continue --count` | 默认 **1**。W2 可 `--require-plan`。可 `--variants 2` 转入抽卡 |
| `canon triage` | accept / edit / dismiss。支持 `--json`。没有「抽取完自动 confirm」 |
| `check` | 规则优先，可选模型做定位。输出 Markdown 报告，可选 JSON。不改库 |
| `review` | 清单 = check 问题 ∪ 复读 / 专名提示 ∪ variant 备注 ∪ 人的 mark。不自动改文、不入典 |
| `today` | 下一步导航：待 triage、未 pick、stale 章、open promises、建议走哪条 W |
| `branch` | 不注册为可用功能。若文档提到，标 deferred |

作者向命令提供 `--json`，与 `doctor --json` 同一习惯，方便以后的 TUI，但 V1.0 不交付 TUI。

建议退出码：`0` 成功；`1` 用户 / 配置 / 项目错误；`2` 业务闸门未过（check 有 blocker，或 continue 缺 Canon）；`3` 预算耗尽。

### 8.4 日用最小口令（目标形态，尚未实现）

```bash
songyan today --project-id <id>
songyan canon triage --project-id <id>
songyan check --project-id <id> --chapter N
songyan variant generate --project-id <id> --chapter N --n 2
songyan variant pick --project-id <id> --chapter N --slot 2
songyan chapter continue --project-id <id> --count 1
```

W0 的一天可以停在前三行，并且不调用 `variant` / `continue`。

### 8.5 兼容

1. 不删除现网命令名。
2. 新分组是别名或薄包装。
3. 默认权威改为「助手安全」时用开关：提案不入典。维护者可打开「写回运行时结算库」做对照，默认关，且永不写 approved plan 行。
4. 旧 CLI 测试保持绿。新命令先测参数解析；Phase 0 的桩可以只打印未实现并返回非零，但那是接受本文之后的代码切片。

Flag 名是草案。实现评审可以改名，不能改「确认才入典」和「抽卡不覆盖 picked」。

---

## 9. 路线图（V1.0 = Phase 0–3）

顺序固定。上一阶段出口未过，不把下一阶段的生成能力当成主路径来做。

### Phase 0 — 规划锁定，然后才是命令桩

**现在这一步（本文件）：** 对象模型、W0–W6、N=2、Variant、确认入典、`run` 降级，写进仓库供 owner 接受。

**接受之后仍属 Phase 0 的代码（本 PR 不含）：** 作者向 `[proposed]` 命令的 `--help` 桩（`project` / `chapter` / `canon` / `check` / `status` / `today` 先行；`variant` 的桩可以同时注册，执行仍是未实现）；Variant / Proposal 的 schema 草案；`run` 帮助文案。桩不调用模型。`branch` 不注册成可调用命令；帮助里若提到，只写明延后。

**出口：** Owner 书面接受本文。尤其是：Variant 不是 Git 分支；未确认不得入典；默认 N=2；Phase 1 包含 W0。

**不做：** 真生成、真抽卡、改 `SettlementExtractor` 的写入。

### Phase 1 — Canon + check + triage（含 W0）

**做：**

- `canon show|edit|triage|confirm`
- 规则型 `check` + Markdown 报告
- `status` / `today`（含开放承诺，服务 W5 的阅读面）
- 抽取输出进入提案队列（最小改建）
- 可选 `project init`
- `chapter list|status`
- W0 全程可走完（零生成）
- W6：`check` 默认不入典
- W4：硬事实变更把相关章标 `stale`，不自动改文
- W3：导入抽取进提案队列（`import` 命令本身已有）
- W5：`today` 展示 open promises；销账走 confirm

**出口：**

1. 一本小项目上，作者能走完「提案 → 确认 → `check` 看见至少一类已知硬伤」。
2. 自动化测试：未 confirm 的抽取不出现在 `load_chapter_plan_bible`（M8）。
3. 连续 3 天狗食愿意打开 `today`（M6，记日志）。

**不做：** 多 variant、把长窗 `run` 当主路径、Web、`branch`、真实抽卡。

### Phase 2 — 单章 Variant 抽卡（W1 的生成半边）

**做：** `variant generate|list|diff|pick|abandon`；Canon fingerprint；每章成本上限；默认 N=2；重审计默认只覆盖 picked。多样化先用温度或不同 diversify 提示，不把 `--tone` 一类旋钮当成出口条件。

**出口：**

1. 同一章 2 稿可以 diff；`pick` 不改 Canon。
2. 报告里有 per-slot 费用字段。
3. 至少一次真实狗食记录「人选的不是第一稿」的比例（M4）。若两次都只选第一稿，先查塌缩，不直接加 N。

**不做：** 自动选优、自动发表、跨章 `branch`。

### Phase 3 — W2 短续写闭环

**做：** `chapter continue` 默认 1 章；`review` 补上共审项（上章动作指纹、未改就想 settled 的可配置警告）；`--require-plan` / `--require-settled`；章末 triage 清单。W1 的「人改 → 再确认」与 W2 在这里接成可切换的环。W3 的续写若要试，走这条命令，并在记录里保持「未验收」。

**出口：**

1. 完整走通 3 章 W2，没有任何自动入典。
2. ContextEmergency 相对 Ch1–10 长跑有对照记录。期望下降，不保证。
3. 作者只看 `today` 能说出下一章该干什么。

**不做：** 无人值守 10 章以上；宣称文学质量可以连载；把导入续写写成已验证。

### 9.1 工作流落在哪一阶段

| 工作流 | 可用阶段 | 说明 |
|--------|----------|------|
| W0 | Phase 1 | 第一价值，零生成 |
| W6 | Phase 1 | 只审；`review` 的共审增强在 Phase 3 |
| W5 | Phase 1 | 阅读和确认销账；不新造命令组 |
| W4 | Phase 1 | 标脏 + 人修；不自动改文 |
| W3 | Phase 1 到 triage；续写 Phase 3 | 续写质量未验收 |
| W1 | 闸门 Phase 1；抽卡 Phase 2 | Phase 1 允许外置单稿走提案 |
| W2 | Phase 3 | 短续写闭环 |

### 9.2 V1.0 之后（明确延期）

| 项 | 为何不进 V1.0 |
|----|----------------|
| Git 式 Canon Branch / `branch` | 心智和合并成本高；抽卡已覆盖单章探索 |
| Rich / Textual 全屏 TUI | 先让 CLI 日用稳定；triage 用普通列表即可 |
| 本地 Web：关系图、时间线、甘特 | 高价值，不是第一道门 |
| MCP 暴露同一 Canon | 先稳住 SQLite 真源 |
| 多书共用 World Bible | 范围会漫出一部小说 |
| 完整 POV 知情分层 | schema 预留 soft 字段即可 |
| Obsidian 双向同步 | 可选适配器，不是内核 |
| 预算化 RAG / lore 注入加强 | `index` 已在；MVP 不依赖 |
| 从已确认事实回写「回顾性计划卡」 | W1 的便利功能，不挡 Phase 1–3 |

下列各项即使用户以后再提，也仍是第 2 节的非目标，除非 owner 显式解冻：无人值守成书、默认句级补全、题材检查器堆叠、静默入典、云锁定正文。

---

## 10. 能力地图

图例：**复用** = 留下并接到新工作流；**改建** = 实现还在，默认权威或作者路径变了；**新建** = V1.0 必需且现在没有；**延后** = 不进 Phase 0–3。

### 10.1 复用

SQLite 长期记忆；体裁与项目模板；`doctor`；质量门 / literary auditor / `five-gate` / `t9`（作为过程信号和 variant 侧车分数，单独通过不等于可发表）；`load_chapter_plan_bible` 与 `plan_fact_gate`；主张摘录与锚（进提案或审读证据，不静默写库）；`foreshadowings`；continuity / setting 跟踪（喂 ConsistencyReport）；`export` / `backup` / `restore` / `bundle-run`；`profile`；`mark`；按角色的模型路由和成本记录；`import` 全组。

计划事实表（entity / attribute / event / time anchor / clue + `approval_status`）是 Phase 1 Canon 的真源，属复用里的核心，不是另起一张平行圣经。

### 10.2 改建

| 项 | v0.5 语义 | V1.0 语义 |
|----|-----------|-----------|
| `run --auto-confirm` 多章 | 文档中的主路径「写下去」 | 维护者冒烟 / 实验。作者主路径改为 chapter / variant / canon |
| SettlementExtractor | 接受章节后写入结算库，影响后续章 | 助手路径改为提案。下一章只读已确认 Canon / 已批准计划卡 |
| 质量门 PASS | 容易被读成书写合格 | 过程门禁。文学结论分开写 |
| 上下文组装 | 为长连跑准备 | 助手默认「本章卡 + 有预算的硬事实」，并暴露 ContextEmergency |

### 10.3 新建（按最早阶段）

| 能力 | 阶段 |
|------|------|
| `canon *`、提案队列的 accept / edit / dismiss | 1 |
| 作者向 `check`、基础 `review`、`status`、`today` | 1 |
| 硬事实变更后的 stale 标记 | 1 |
| Chapter Variant 存储、fingerprint、`variant *` | 2 |
| `chapter continue` 与 W2 共审清单 | 3 |

### 10.4 延后

见第 9.2 节。另：SillyTavern 式角色扮演前端、SaaS、把某一开源项目的 API 当成依赖。调研里的项目只提供模式（提案确认、状态字段、多变体不覆盖、粗粒度脚手架），不引入为运行时依赖。

### 10.5 能力 × 工作流

● 主路径，○ 可选，— 这条流不用。

| 能力 | W0 | W1 | W2 | W3 | W4 | W5 | W6 |
|------|----|----|----|----|----|----|-----|
| Canon 读写 / triage | ● | ● | ● | ● | ● | ● | — |
| `check` / `review` | ● | ● | ● | ○ | ● | ○ | ● |
| `today` / `status` | ● | ● | ● | ○ | ● | ● | ○ |
| Variant 抽卡 | — | ● | ○ | — | ○ | — | — |
| 人改正文 | — | ● | ● | — | ● | — | — |
| `chapter continue` | — | ○ | ● | ○ 未验收 | — | — | — |
| `import` | — | ○ | ○ | ● | — | — | — |
| 长窗 `run` | — | — | — | — | — | — | — |

---

## 11. 风险

### 11.1 成本 × N

抽卡近似按 N 放大写作和部分审查费用。Ch1–3 冒烟约 ¥1 / 三章量级，Ch1–10 约 ¥3.4，都市灵异对照约 ¥6.8 / 三章（owner 口径，¥2/M 入、¥8/M 出）。这些是已有记录的数量级，不是 Variant 的报价。

若每个 variant 都开满 literary auditor，账单更陡。缓解：默认 N=2；重审计只对 picked；`--budget-cny`；生成可以用更便宜的角色，贵模型只审选中稿。示意（单章写作+轻审按 ¥0.3–0.8 估，不是账单）：W2 单稿约 ×1；N=2 且全审约 ×2–2.5；N=3 且只审 picked，生成仍约 ×3、总账约 ×1.3–1.8。单章停线参考现网 ¥7.66 的记录方式，并加 per-chapter cap。实现时沿用 `SONGYAN_RUN_COST_BUDGET` 的语义。

### 11.2 ContextEmergency / DG-1

Ch1–10 上平均 revision 1.7，ContextEmergency 十章都出现。抽卡不会修好上下文；N 次生成可能是 N 次应急。缓解：助手默认单章；Canon 注入有预算；`status` 露出 emergency 次数；超过阈值则拒绝 `continue`，直到人裁剪 marks 或 Canon。这是减轻，不是根治。

### 11.3 所有权

脚手架越细，作者越可能觉得稿子不是自己的，或直接采纳抽卡、不再改。缓解：文案把产出叫做草稿；成功看 M5（人改痕迹）而不是生成字数；`review` 可以警告「几乎没改就进入 settled」（可关，Phase 3）。默认不做句级补全。

### 11.4 导入未验收

`import` 的自动化测试和 CLI 冒烟已有。真实模型上「导入一本原稿再续写」还没有验收报告。W3 的续写在文档、`today` 和命令帮助里保持未验证，直到那份报告出现。在此之前，导入路径的完成定义停在 triage 入典。

### 11.5 其他

| 风险 | 缓解 |
|------|------|
| 抽取噪声污染 Canon | 确认闸门；M8 测试；旧结算库只读打标 |
| 作者以为 pick 已入典 | `status` 显示 pending；`pick` 的输出写明未入典 |
| 命令变多 | 阶段门禁；日用只印第 8.4 节那几行；旧命令留在排错文档 |
| 两套产品声音（工作台 vs 助手） | 以本文为准。调研降为附录，不删证据 |
| 过程门绿、稿子不可读 | 指标分离（第 12 节）；不把 QG 当发表标准 |

---

## 12. 文学质量仍属于人

1. **文学质量由人拥有。** Songyan 提供探索、账本和审计。它不宣称稿子可上架、可连载、可发表。
2. **质量门通过 ≠ 书写合格。** Accepted、QG、结算、导出成功，只说明管线走完。
3. **Ch1–10 只是管线证据。** 《轨道蜃景》这次长跑：10/10 accepted，过程门与导出为绿，DG-1 失败，人工阅读未通过（时间线回滚、专名漂移、套路复读、尺度崩坏）。它证明「自动绿灯不够」，不能写成「十章已验证可读」。运行标识和本机路径以 [STATUS](STATUS.md) / [HANDOFF-mew.md](HANDOFF-mew.md) 为准，不把书稿收进仓库。
4. 下表是产品响应，不是自动根治：

| 已观察到的问题 | 助手路径怎么接 | 能否自动根治 |
|----------------|----------------|--------------|
| 跨章时间线回滚 | W2 先写计划；`check` 对时间锚；禁止无审连跑 | 否，要人改结构 |
| 专名漂移 | Canon 硬名册；`review` 的变体启发式 | 部分 |
| 套路复读 | `review` 提示上章动作指纹；人删 | 否 |
| 生死 / 尺度崩坏 | 硬属性的有效章区间 + `check` | 部分 |
| 门绿稿红 | M9 与过程门分开；文案保持这一节的说法 | 靠产品边界，不靠再加一个门 |
| DG-1 / ContextEmergency | 短窗、预算注入、把次数露出来 | 减轻 |
| 结算清单不像人写的摘要 | 抽卡和人改优先于把清单打勾 | 减轻 |

5. M9 永远是人工抽读。一次 LLM judge 不能代替结构化 `check`，也不能给文学签字。

---

## 13. 接受本文之后

本文合并只表示规划进了仓库。**实现等 owner 接受这份 PRD 之后再开。**

接受后的第一刀仍是 Phase 0 的薄代码：命令桩和 schema 草案，不调用模型，不翻转结算权威。第一段用户价值是 Phase 1 的 W0：`canon show` + triage 读 pending + 规则型 `check`。那一刀仍然不改质量门路由，不加题材检查器，不重记阶段 C 召回，不写《规则年代》。

狗食可以在命令未齐时先用纸面走一遍（一条硬规则、两份外置草稿、人只批其中一部分、再改再批），用来调整 Phase 1 的清单顺序。纸面狗食不是实现。

---

## 14. 文档关系

| 文档 | 和 V1.0 的关系 |
|------|----------------|
| 本文 | 现行产品规划 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实写入方向：计划与人写 Canon，抽取不自动成为权威 |
| [ROADMAP-plan-first.md](ROADMAP-plan-first.md) | 阶段 A–C 已收束。本文不重开那张召回计分板 |
| [STATUS](STATUS.md) | v0.5 工程现状与已知限制。实现状态以 STATUS 为准，不以本文的 proposed 命令为准 |
| [HANDOFF-mew.md](HANDOFF-mew.md) | 每日切片。在 owner 接受本文前，下一刀不是按本文改代码 |
| 工作台调研（2026-10-26） | 附录。对象、triage、所有权文献仍可引用；「写作可选 / 纯台账」不是现行定义 |
