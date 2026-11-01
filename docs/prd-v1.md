# Songyan V1.0 产品需求

- **状态：** 2026-11-01 重写稿。待 owner（Bingtuu）书面接受。接受之前不开实现，不写 `tasks/200`。
- **本文做什么：** 把已接受的总体框架写成可审的完整需求：两条主路径、每步的目标与分支、里程碑边界、可测验收。
- **本文不做什么：** 不改应用代码，不把包版本升到 `1.0.0`，不打名为 `v1.0` 的 git tag。当前 tip 仍是 **v0.5**（`pyproject.toml` 的 `0.5.0`）。
- **产品代际名 vs 包版本：** 「V1.0」是写作助手这一代产品的名字，不是包版本号。
- **和上一稿的关系：** Owner 已接受 [2026-10-26 稿](archive/prd-v1-writing-assist-2026-10-26.md) 的总体框架。本文继承该框架并补全路径与验收。旧路径 `docs/prd-v1-writing-assist.md` 只留指针。冲突时以本文为准。

读者：owner，以及书面接受之后按里程碑实现的人。事实写入方向仍是 [ADR-0001](adr/0001-plan-first-facts.md)。Plan-first 阶段 A–C 已收束，见 [ROADMAP-plan-first.md](ROADMAP-plan-first.md)。不要重开题材检查器召回 KPI。

文中命令凡现网还没有的，一律标 **`[proposed]`**。README 只在对应代码合并之后才能写成「已经支持」。

---

## 1. 产品

**一句话：** Songyan（松烟）是人主导的连载写作助手，接在现有的事实 / 故事线工作台上面。人设计并决定复杂事实、数据、人物、时间、道具、伏笔和故事线；系统负责记录、检索、发现冲突、审计变更、报告一致性。终稿由人定。

两条主路径（日常就这两条，不是两种产品）：

| ID | 名字 | 顺序 |
|----|------|------|
| **P-draft** | 先稿后典 | 生成草稿 → 结算事实 / 数据 → 人改编 → Songyan 审读 / 检查 |
| **P-bench** | 工作台先行 | 人编辑事实与故事线，系统做记录、检索、冲突、审计和一致性支持 |

静默改 Canon 不在产品里。无人值守写完一本小说不在产品里。把一本旧稿自动改写成「更好的一版」不在产品里。

### 1.1 为什么是这一档

| 路 | 含义 | V1.0 |
|----|------|------|
| 自动成书 | 无人值守连载，闸门绿即当写完 | 不做 |
| 纯设定台账 | 只记账，几乎不生成正文 | 过窄。写作辅助留在产品里 |
| 自动改写 | 系统替人重写终稿 | 不做 |
| **写作助手 + 工作台** | 人定方向、事实和终稿；系统出草稿、记账、做窄检查 | **V1.0** |

已有记录把「再自动跑一轮」排除掉了：

- Plan-first 阶段 C（都市灵异）召回 1/5，退出未过。Owner 已接受薄封装：人维护事实圣经，模型按圣经写。都市灵异留作试点例子，不是以后唯一题材。
- 《轨道蜃景》Ch1–10（`47954cb`，`run-33841231`）：管线走完，人工阅读未通过。这是管线证据，不是文学验收。数字与路径以 [STATUS](STATUS.md) 为准。

过程门禁抓得住「这一章有没有走完」。它抓不住全书编辑纪律，也代替不了文学所有权。

### 1.2 谁在用

| 人 | 角色 |
|----|------|
| 连载作者（主） | 维护事实和故事线，挑草稿，改终稿，确认入典。能配置本机 CLI 和模型 API key。 |
| 责编 / 审读（次） | 只看冲突和承诺，不负责生成。走 W6。 |
| 维护者 | `doctor`、`run` 冒烟、备份、诊断包。不代表作者日常。 |

空白开书、导入旧稿、日更、改一处硬设定、清伏笔债，是同一个人在不同天的事。按场景拆工作流，不按另一种产品拆。

### 1.3 试点题材

Phase C 和现成夹具用的是 **都市灵异**（内置计划卡《末班铜牌》，`project_id=dushi-lingyi`）。M0 验收用这份夹具，避免再跑一轮真实模型长篇。

科幻、玄幻、武侠模板仍然留在引擎里。V1.0 不为某一题材加专用检查器。换书时换人维护的卡，不换产品。

---

## 2. 已锁定的决定

这些决定从上一稿继承。实现时按这里写。数字若要改，先改本文再改代码。

| 决定 | 内容 |
|------|------|
| 交互 | **CLI 优先。** Python Click 不变。章节编排仍是现有 LangGraph。TUI / 本地 Web 在 V1.0 里程碑之外。 |
| 真源 | **SQLite 是唯一长期事实源。** 不另起权威库。 |
| 入典 | **Confirm-to-canon。** 模型抽取、结算摘要、审读建议默认是提案。写入 Canon 的作者路径是 triage / confirm。 |
| 抽卡 | **章内 Variant，不是 Git 分支。** 同一章 N 个草稿槽，共享章号和同一份 Canon 快照。 |
| 默认 N | **2。** 作者可显式加大，并受预算约束。 |
| `run` | **保留，降为引擎 / 冒烟 / 长窗实验。** 作者日用不推荐 `run --chapters 1-N --auto-confirm`。 |
| 章节版本 | **只追加。** 草稿、修订、已接收版本都留下。 |
| 提示词 | 长提示词在 `src/songyan/prompts/cards/`。不嵌进 Python。 |
| 计划卡 | 只有 `approval_status=approved` 的行进入本章事实圣经。`pending` 不能被下一章当成已成立事实。 |
| 重审计 | 文学向重审计默认只对 **picked** 稿。其余 variant 可只带轻分数。 |
| 包版本 | 实现这些里程碑时 **不** 为了「进入 V1.0」去改 `0.5.0`。正式 tag 由维护者另决定。 |

Git 式整树 `branch` 不在 V1.0。口语里的「分支」写成「草稿变体 / 抽卡」。平行设定若必须试，另开一个 Project（或复制本地库）。

调试用的「写回运行时结算库」可以留给维护者开关，默认关。这个开关不能把未确认行写成 `approval_status=approved`。

---

## 3. 非目标

下面这些不是「下一刀顺手做的」。解冻需要 owner 另说。

1. 把无人值守连载当成作者主路径，或把「写完整本」写成卖点。
2. 把产品收成没有正文的纯 wiki。
3. 系统自动重写或自动替换终稿。
4. 默认句级幽灵补全。脚手架停在章纲、设定、冲突报告、整章草稿变体。
5. 抽取或审读在无人确认时写入 Canon。
6. 为追召回再堆题材专用检查器。窄检查保持薄封装。
7. Git 式整树 Canon 分支。
8. 用一次开放式 LLM「找全书漏洞」代替结构化 `check`。
9. 把质量门通过、Ch1–10，或任何 `run --auto-confirm` 写成文学已验证。
10. Obsidian 当作唯一库，或云端锁定正文。
11. 命令还没落地时，README 声称已支持抽卡、`canon` 或 `today`。

---

## 4. 对象

**正文草稿不是唯一真相。** 经人确认的计划事实才是 Canon。草稿可以改、可以丢。Canon 的变更必须显式、可回溯、带来源。系统不因为生成了一稿就改写权威事实。

故事线骨架（大纲、弧、线索）是人设计的规划，**不是** Canon 的别名。两边都在同一份 SQLite 里，分表存放，分开展示。

### 4.1 对象与现码

| 对象 | 定义 | 现码 | 权威？ |
|------|------|------|--------|
| **Project** | 一部小说工程 | `projects`；`create-project` / `list-projects` | 工程元数据 |
| **Canon** | 已确认事实：实体、属性、事件、时间锚、线索卡 | `plan_entities` / `plan_attributes` / `plan_events` / `plan_time_anchors` / `plan_clues`。读路径 `list_canon_*` 只返回 `approved`，属性还要求 `source` 为 `plan` 或 `human` | **是** |
| **Pending** | 同一批表里尚未确认的行 | `list_pending_*`；`approval_status=pending` | **否** |
| **Storyline** | 全书大纲、弧、剧情线索 | `StoryOutline` / `ArcPlan` / `PlotThread`（`NarrativeRepository`） | 规划骨架，不是 Canon |
| **Promises** | 叙事承诺。作者看见现网状态 `planted` / `due` / `overdue` / `resolved` / `archived` | `foreshadowings`（结算库；`resolved_chapter` / `resolved_version_id` 现为可追溯列） | 运行时债务。销账要人确认之后才算 Canon 侧承诺 |
| **Character / 数值 / 道具** | 人物切片、数值账、设定快照 | 结算写入的角色状态、`NumericalLedger`、setting 快照 | 运行时观测，不是 plan canon |
| **Chapter / Version** | 章槽与只追加的正文版本 | 现有章节表 | 正文历史，不是事实权威 |
| **Variant** | 章内抽卡槽 | **还没有** | 草稿。`pick` 不入典 |
| **Plan Card / Bible** | 注入本章的已批准卡 | `load_chapter_plan_bible` | 只读 approved |
| **ConsistencyReport** | 结构化问题：证据、严重度、建议动作 | `plan_fact_gate`（必须提及、主张、类型化属性）已有；作者向 `check` 还没有 | 报告不写库 |
| **Proposal** | 抽取或审读产生的待确认项 | 语义要建。今天 `SettlementExtractor` 写结算库，不写 plan 表 | 确认前不是 Canon |
| **质量门** | CED / T9 / 五门 / 文学审查 | `report`、`five-gate`、`t9`、LangGraph 审查节点 | 过程信号。通过 ≠ 可发表 |

现码 `approval_status` 只有 `approved` 和 `pending`。上一稿写过 `rejected` / `superseded` 和 `hardness=hard|soft`。那些字段 **M0 不加**。M1 的技术方案再决定「驳回」是删掉 pending 行，还是加状态；在那之前不得把未确认行读成 Canon。

### 4.2 Chapter 与 Variant（目标语义，表还未建）

章节作者状态（解释层，不是现网列）：

```text
empty → outlined → drafting → variants_ready → picked → human_rewriting
  → in_review → needs_settlement → settled → stale
```

允许的跳转：`picked → in_review`（人几乎没改）；`settled → stale`（事后改了硬事实）；`stale → drafting`（人决定重写）。`stale` 只是标记。系统不自动改正文。

Variant 目标字段：`variant_id`、`chapter_no`、`slot_index`（1..N）、`status`（`generated|picked|abandoned|archived`）、`parent_canon_fingerprint`、正文引用、可选分数、费用估计。同一章同时最多一个 `picked`。`pick` 只移动工作正文指针。Canon 变了之后，variant 标 `stale_vs_canon`：仍可阅读，不能当作默认续写底稿。新 variant 不得覆盖已 picked 的正文。`abandon` 是软删除。

这套表属于 **M3**。M0–M2 不建 variant 表，不注册 `variant` 命令。

### 4.3 Proposal（目标语义）

```text
proposed → accepted → approved（进入 Canon）
         → edited → approved
         → dismissed
```

没有自动边进入 `approved`。`accepted` 是人在 triage 里点头；`approved` 是已经写入 Canon。一次 confirm 可以连续完成这两步。还没写入 Canon 的提案，下一章上下文读不到。`dismiss` 用来压误报，不是为了把召回数字做高去加题材硬规则。

M1 只做人直接写入的计划行。把 `SettlementExtractor` 的输出接进提案队列是 **M2**，避免同一步又改 CLI 又翻结算权威。

---

## 5. 里程碑

顺序固定。上一里程碑的验收未过，不把下一里程碑的生成能力当成主路径来做。

**本文件、`docs/tech-m0.md`、新的 `AGENTS.md` 与 `docs/STATUS.md` 不是 M0 的实现。** 它们是开工门。Owner 书面接受这四份之前，禁止按本文改 Python。M0 的实现只写在 [tech-m0.md](tech-m0.md)。M1 及以后各自另写技术方案，不在 M0 的技术文里预做。

| 里程碑 | 边界内 | 边界外 |
|--------|--------|--------|
| **M0** | 只读工作台：`canon show`、`today`。看见 approved、pending、故事线骨架。零生成，零写入 | 不 confirm、不 check、不抽卡、不续写、不改结算器、不加表、不加迁移 |
| **M1** | 人确认入典（edit / triage / confirm）+ 规则型 `check`。W0 能走完「看见 → 人确认 → 再看见」。W6：`check` 不写库 | 不接结算抽取进提案，不抽卡，不 `continue`，不自动标脏 |
| **M2** | 硬事实标脏（不改文）；承诺队列可读，销账要人确认；导入 / 抽取结果进提案而不是 Canon | 不抽卡，不把短续写当主路径，不自动重写脏章 |
| **M3** | 章内 Variant。默认 N=2。`pick` 不改 Canon | 不自动选优，不做 Git `branch`，不无人值守连载 |
| **M4** | `chapter continue` 默认 1 章。W2 短环：计划卡 → 一章 → 共审 → 人确认 → 下一章 | 不把 10 章以上无审连跑写成作者路径；不宣称文学可连载 |

上一稿的 Phase 0–3 收进这张表：Phase 0 的「命令桩」不单列，M0 直接做只读真命令；旧 Phase 1 拆成 M0+M1+M2；Phase 2 = M3；Phase 3 = M4。

### 5.1 工作流落在哪

稳定 ID 仍是 **W0–W6**。

| ID | 名字 | 主路径 | 可用里程碑 |
|----|------|--------|------------|
| W0 | 只典，零生成 | P-bench | 读在 M0；写与确认在 M1 |
| W6 | 只审，默认不入典 | P-bench | M1 起 `check`；共审增强在 M4 |
| W5 | 承诺债务 | P-bench | M2 |
| W4 | 改典涟漪 | P-bench | M2 |
| W3 | 导入旧稿 | 两边的入口 | 现网 `import` 已有；抽取进提案在 M2；续写在 M4，且保持未验收 |
| W1 | 抽卡后沉淀 | P-draft | 闸门语义 M1 可用外置单稿验证；抽卡在 M3 |
| W2 | 先典后续写 | P-draft | M4 |

### 5.2 指标

上一稿用 M1–M9 表示指标。本文起里程碑占用 M0–M4，指标改称 **S1–S9**。含义不变。

| ID | 指标 | 怎么算通过 | 从哪一程开始记 |
|----|------|------------|----------------|
| S1 | 每周确认入典的事实数 | 有记录；dismiss 比例说得通。不是越多越好 | M1 |
| S2 | 冲突关闭周期 | open → closed 或 dismiss 有记录 | M1 起能报出问题；关闭动作随 confirm / dismiss 落地后才记周期 |
| S3 | 开放伏笔年龄 | P50 不超过该书约定章数。不写死全题材数字 | M2 |
| S4 | 抽卡采纳分布 | 被 pick 的 slot 不全是 1 号 | M3。若样本都选 1 号，先查塌缩，不直接加 N |
| S5 | 人改率 | pick 之后工作正文相对原稿的 diff 非空比例 | M3 起有 pick；这是所有权代理，不是文学分 |
| S6 | `today` 打开天数 | 狗食周 ≥ 3 天，有日志 | M0 起命令存在之后才记。文档 PR 不算打开 |
| S7 | 单章成本 | 预算内完成率，含 N 个 variant。口径 ¥2/M 输入、¥8/M 输出，是估算不是账单 | M3 起有 per-slot 字段 |
| S8 | pending 泄漏 | **0** 条未确认行进入 `load_chapter_plan_bible` | 现码已是这条语义。M0 用测试守住，M1 再守住写入路径。进 CI |
| S9 | 文学 | 人工抽读 | 永远不进自动绿灯 |

**不用作主 KPI：** 日产字、accepted 章数、质量门通过率、星标、参数量。质量门通过率仍是工程回归，不代表书写得好。

---

## 6. P-bench：工作台先行

**目标：** 作者可以不生成正文，就把事实和故事线管清楚，并在以后的里程碑里得到一致性报告。系统记录人的决定，不替人决定。

**本路径不调用** `variant generate`、`chapter continue`、`run`。

### 6.1 打开工程

**目标：** 有一份本机 SQLite 项目。

**主要路径：** `songyan create-project`（可选模板）→ `list-projects` 看见 `project_id`。

**分支：**

| 分支 | 行为 |
|------|------|
| 模板自带大纲 | 现有初始化会写入故事线骨架。M0 只读它 |
| 空项目 | 事实与故事线都为空。命令成功，输出写明为空 |
| 导入已有书 | 走第 8 节 W3，不在这一步新写正文 |

**里程碑：** 命令已有。M0 不改 `create-project`。

**验收：** 现有建项测试保持绿。M0 不把「建项」算成新功能。

### 6.2 看见 Canon、pending 和故事线（M0）

**目标：** 打开工程后，作者能分清三件事：已经确认的事实、还没确认的行、故事线骨架。

**主要路径：**

```text
canon show --project-id <id>
today --project-id <id>
```

`canon show` 分三段打印：

1. **Canon**：`list_canon_*` 的实体、属性、事件、时间锚、线索。
2. **Pending**：同表的 pending 行，标题写明「不是 Canon」。
3. **Storyline**：`get_outline` / `list_arc_plans` / `list_threads`。标题写明「规划骨架，不是已确认事实」。

`today` 只打印计数和一句下一步：本里程碑不能确认、不能生成。待确认行不会被自动批准。

**分支：**

| 分支 | 行为 |
|------|------|
| 项目不存在，或数据库文件不存在 | 退出码 1。不创建数据库文件 |
| 项目在，三类都空 | 退出码 0，空段写明为空 |
| 只有故事线、没有计划卡 | Canon 段为空，故事线仍单独显示 |
| `--kind` 过滤 | 只打请求的那一类；故事线用 `--kind storyline` |
| `--json` | 键为 `canon`、`pending`、`storyline`。故事线不得塞进 `canon` |

**里程碑：** 全部是 M0。技术方案只写 [tech-m0.md](tech-m0.md)。

**验收（M0 代码落地时，全部要有自动测试）：**

1. 夹具《末班铜牌》（`dushi-lingyi`）上，`canon show` 退出码 0，approved 段能看见已加载的计划卡。
2. 测试另插入一条 `approval_status=pending` 的实体。它只出现在 pending 段。
3. 同一条 pending 行不出现在 `load_chapter_plan_bible` 的结果里。M0 不改这个函数的过滤条件。
4. 有故事线时，正文标题和 JSON 的 `storyline` 与 `canon` 分开。没有故事线时该段为空，退出码仍为 0。
5. `today` 不调用模型，不写库，不启动 `run`。
6. 不存在的项目或缺失的数据库文件：退出码 1，磁盘上不出现新建的库文件。
7. `SettlementExtractor`、LangGraph 章节图、`_MIGRATIONS`、`pyproject.toml` 版本无行为变化。版本保持 `0.5.0`。

### 6.3 人写入并确认事实（M1）

**目标：** 作者把一条事实变成 Canon 的唯一路径是显式 confirm。下一章圣经只读得到确认后的行。

**主要路径：**

```text
canon edit（人写出一条计划行，默认 pending）
  → canon triage（accept / edit / dismiss）
  → canon confirm
  → canon show 的 Canon 段出现该行
  → load_chapter_plan_bible 能读到它
```

人也可以在 confirm 时一次完成 accept。没有「保存即 approved」的默认，除非该次命令就是 confirm，并且输出写明已入典。

**分支：**

| 分支 | 行为 |
|------|------|
| dismiss | 不进入 `approved`。下一章圣经读不到 |
| 改完再生效 | edit 之后必须再 confirm。只改草稿文本不算入典 |
| 结算器刚抽了一条 | M1 **不**把这条接进队列。它仍留在结算库，不当作 Canon |
| 缺项目或 id 冲突 | 退出码 1，不写半行 |

**里程碑：** M1。M1 开工前另写 `docs/tech-m1.md` 并经 owner 接受。本文不规定 `rejected` 列还是删除行。

**验收：**

1. 未 confirm 的新行不在 `load_chapter_plan_bible`（S8）。测试先红后绿。
2. confirm 之后，同一稳定 id 出现在对应的 `list_canon_*`。
3. dismiss 之后，该 id 不在 `list_canon_*`。
4. 命令路径上不调用模型。
5. `apply_settlement` 的写入目标表与 M1 开工前相同。

### 6.4 规则检查，默认不入典（M1，W6）

**目标：** 作者或责编对一章正文做窄检查，得到带证据的问题清单。检查本身不改 Canon、不改正文。

**主要路径：**

```text
check --project-id <id> --chapter N
  → 只读 run_plan_fact_gate（必须提及、主张、类型化属性）
  → Markdown 报告（可选 JSON）
```

报告可以写「若要入典，另走 canon triage」。这句不是默认动作。

**分支：**

| 分支 | 行为 |
|------|------|
| 该章没有正文 | 退出码 2，说明无章可查。不臆造冲突 |
| 门通过 | 退出码 0。文案不得写成「可以发表」 |
| 有硬伤 | 退出码 2，列出证据。不自动改文、不自动改卡 |
| 体裁惯例被当成冲突 | 人以后可以 dismiss。M1 不为此加题材规则 |
| 想用一次模型通读全书 | 不做。那是第 3 节的非目标 |

**里程碑：** 规则 `check` 在 M1。复读、专名启发式、共审清单在 M4 的 `review`。

**验收：**

1. 夹具中构造一条已批准属性与给定正文不一致。报告点名该实体、键、圣经值和正文侧值。
2. 检查前后，`plan_*` 行数与 `approval_status` 不变。
3. 默认不调用 LLM。主张判断沿用现有确定性锚。
4. W6 全程没有 confirm 调用。

### 6.5 硬事实变更后的涟漪（M2，W4）

**目标：** 人改了硬事实之后，能看见哪些章和草稿过期，再自己决定改文还是改事实。

**主要路径：**

```text
canon confirm（人标明这是硬变更）
  → 覆盖到的章标 stale
  → check 只报告受影响范围
  → 人选择改正文、再改事实，或驳回
```

系统不自动重写，不自动重抽。算不到章号的，不猜成脏。`valid_from_ch` / `valid_to_ch` 和证据里的章号是范围来源。

**分支：** 软注记（动机、秘密）默认不把整章标脏，除非人显式要求。M2 技术方案再定「硬」是命令旗标还是新列。M0/M1 不加这个列。

**验收：**

1. 给定一条覆盖第 2–4 章的硬属性变更，第 2、3、4 章出现 stale，第 1 章和第 5 章不出现。
2. 正文版本表的既有行不被覆盖；若人另存修订，是新版本。
3. 没有任何自动调用的写作节点。

### 6.6 承诺债务（M2，W5）

**目标：** 作者看见已埋下、到期、过期的伏笔，兑现或作废必须经人确认。

**主要路径：** `today` 列出 `foreshadowings` 里 `planted` / `due` / `overdue` 的条数和年龄；`canon show --kind promise` 列出条目。兑现时人给出章号和证据，经 confirm 写入。

**分支：** 模型在结算时把状态改成 `resolved`，在作者路径上只算提案，不算出清。现有列 `resolved_chapter` / `resolved_version_id` 保持可追溯。不另起一套 plant/open/paid 枚举。不单开 `promise` 命令组。

**验收：**

1. 插入一条 `overdue` 伏笔后，`today` 的计数含它，且不把它写成已确认事实。
2. 未经 confirm 的销账，不把该条从 open 集合里抹掉。
3. S3 用这张现表计算，不新建第二张伏笔表。

### 6.7 工作台路径上的切换

| 从 | 到 | 条件 |
|----|----|------|
| 只读（M0） | 确认（M1） | 人显式 edit / confirm。`today` 只提示，不自动执行 |
| W6 | W0 | 人显式开始 triage |
| W0 | W4 | 人确认了一次硬变更 |
| W5 | W0 | 销账需要 confirm |
| 任意工作台步骤 | W6 | 任何时刻都可以只跑检查（M1 起） |

未确认提案不得在切换时并入 Canon。

---

## 7. P-draft：先稿后典

**目标：** 作者可以先看到草稿，再决定哪些事实成立，自己改一版，然后让 Songyan 做审读。生成是探索，不是终稿，也不是入典。

快乐路径（全部里程碑齐了之后）：

```text
已确认的本章计划卡
  → 出草稿（M3 抽卡或 M4 单章续写）
  → 抽取成为提案（M2）
  → 人 triage / confirm
  → 人在外置编辑器改编工作正文
  → check / review
  → 人改带来的新事实再次提案并 confirm
  → 本章 settled
```

M0–M1 期间，作者用外置的一份草稿走「提案语义的纸面或 M1 的人手写卡」，不假装已经有抽卡。

### 7.1 章前只注入已确认卡

**目标：** 写作和修订看见的事实圣经等于本章 approved 计划卡。pending、他章、他项目不混入。

**主要路径：** 现有 `load_chapter_plan_bible` → `wrap_writing_prompt`。空圣经时提示词保持原样。

**分支：** 缺关键硬约束时，M4 的 `continue` 可以拒绝或强警告（`--require-plan`）。M0 不改写作图，所以 M0 不会新增这道拒绝。

**里程碑：** 注入已在 v0.5。M0 只加测试锁定，不改节点。

**验收：** `tests/plan_checks/test_plan_bible_runtime.py` 保持通过。新增的 pending 行不能出现在圣经文本里（S8）。

### 7.2 出草稿

**目标：** 给人一份可丢弃的章稿，供挑选和修改。

**主要路径按里程碑分成三段，不要混用：**

| 阶段 | 作者实际怎么拿到稿 | 系统保证 |
|------|--------------------|----------|
| 现在至 M2 | 外置编辑器，或维护者用 `run` 做冒烟 | `run` 仍会写结算库。文档不把它当作者主路径。它不把抽取写入 plan canon |
| M3 | `variant generate --n 2` | 只读 Canon 快照；不自动 pick；不改 Canon；费用按 slot 记账 |
| M4 | `chapter continue --count 1` | 默认一章。可 `--variants 2` 转入抽卡。无审连跑超过 3 章不写入助手日用说明 |

**分支：**

| 分支 | 行为 |
|------|------|
| 预算耗尽 | 停止生成，已完成的 slot 留下。退出码 3 |
| ContextEmergency | 单章仍超限则减少注入，而不是加长连跑。`status` 在 M4 露出次数 |
| N 稿几乎相同 | 加强 diversify 或先补章拍。不先把默认 N 改成大于 2 |
| 人把 `run --auto-confirm` 当创作 | 帮助文本说明这是管线验证。文案随实现切片落地，本需求不改帮助字符串 |

**验收（M3）：** 同一章两稿可以 diff；`pick` 前后 `plan_*` 的 approved 行不变；报告有 per-slot 费用字段；至少有一次记录人选的不是第一稿，或写明两次都是第一稿并先查塌缩（S4）。

**验收（M4）：** 连续 3 章走 W2，没有任何自动 `approved`；作者只看 `today` 能说出下一章该做什么。

### 7.3 结算事实与数据

**目标：** 稿里新出现的事实、数值、道具变成提案，等人决定，而不是变成下一章的权威。

**主要路径（M2）：** 抽取结果进入提案队列 → `canon triage` → confirm 的才写入 plan 表。人物状态、数值账、道具快照若要进 Canon，走同一条提案，不走第二条静默账。

**分支：**

| 分支 | 行为 |
|------|------|
| 现在的 `run` | `apply_settlement` 仍写结算库（角色、设定、伏笔、数值）。这是运行时观测。M0/M1 不改这条 |
| 作者以为选了一稿等于设定已更新 | `today` / `status` 显示 pending 数。`pick` 的输出写明未入典 |
| 维护者要对照旧结算 | 只读查看可标 `untrusted_until_confirmed`。默认不把这些行 approve |
| 抽取噪声 | dismiss。不加题材硬规则 |

**验收（M2）：** 一次结算写入之后，新事实不在 `list_canon_*`，直到人 confirm。S8 测试仍为 0 泄漏。旧结算表仍在，供对照，不升格为第二真源。

### 7.4 人改编

**目标：** 终稿的句子由人改。系统留下版本，不覆盖旧稿。

**主要路径：** 人在外置编辑器改工作正文。需要新写法时再生成一槽（M3），而不是盖掉 picked。

**分支：** 人几乎不改就想标 settled。M4 的 `review` 可以警告，并且可以关掉。M0–M3 不挡保存。

**验收：** 改稿产生新的章节版本行；旧版本仍可按 id 读回。M5（人改 diff）从第一次 `pick` 之后开始记，不在 M0 伪造这份比例。

### 7.5 审读 / 检查

**目标：** 人机一起看问题清单，再决定改文、改典、重抽或驳回。

**主要路径：**

```text
check（M1，规则）
review（M4：check 的问题 ∪ 复读 / 专名提示 ∪ variant 备注 ∪ 人的 mark）
  → 人四选一
```

| 策略 | 动作 |
|------|------|
| A 改事实 | `canon edit` + confirm；硬变更走 W4 |
| B 改正文 | 改工作正文；要新写法再生成 |
| C 另开变体 | 新的章内 Variant。不是 Git branch |
| D 驳回 | dismiss，可选抑制重复误报 |

审读不自动改 Canon，不自动改正文。过程门绿、读起来不行，仍然算未通过 S9。

**验收：**

1. M1：第 6.4 节的三条。
2. M4：`review` 在不调用 confirm 的测试里，库中 approved 行数不变。
3. 质量门报告可以附在旁边当过程信号，文案与 S9 分开。

### 7.6 抽卡与短续写的衔接

| 从 | 到 | 条件 |
|----|----|------|
| W1 | W2 | 该章已 settled，下一章改为先写计划卡 |
| W2 | W1 | 这一章不满意。旧 picked 归档，Canon 不删 |
| 外置单稿（M1） | W1（M3） | 抽卡命令落地之后。之前不注册一个只会报「未实现」的 `variant` |
| W2 | 下一章 | `today` 建议下一步，人不点头就不开跑 |

---

## 8. W3：导入旧稿

**目标：** 把已有正文收成工程，并把抽出的事实交给人确认。不承诺「导入后的续写已经写得好」。

**主要路径：**

```text
import ingest → segment → confirm → replay / synthesize → publish
  → （M2）抽取进入提案 → canon triage → check
  → 可选：问题章用外置稿或 M3 重抽；从某一章起的续写走 M4，并保持未验收
```

现网子命令保留。`publish` 之后 `run` 才解除阻塞，这条工程闸门不变。

**分支：**

| 分支 | 行为 |
|------|------|
| 只想入库、今天不续写 | 停在 triage。这就是 W3 在续写验收出现之前的完成定义 |
| replay 抽出的事实 | 默认不可信，进提案 |
| 真实模型「导入后再续写」 | 尚无验收报告。`today` 和帮助文本保持未验证，直到报告写进 STATUS |

**里程碑：** 导入命令已有。提案队列在 M2。续写在 M4。

**验收：**

1. 现有 `tests/cli/test_import_commands.py` 保持通过。
2. M2 增加一条：导入抽取的样例行在 confirm 前不进入 `list_canon_*`。
3. 文档与命令帮助不出现「导入续写已验证」。

---

## 9. 命令表面

### 9.1 已经安装的命令

`doctor`、`create-project`、`list-projects`、`run`、`report`、`metrics`、`five-gate`、`t9`、`export`、`backup`、`restore`、`bundle-run`、`profile`（`show|diff|validate|upsert|history|rollback`）、`mark`（`add|list|remove|update-priority`）、`index`、`import`（`ingest|segment|confirm|status|replay|synthesize|publish`）。

这些命令继续存在，测试保持绿。助手日用卡片不把 `run` 当主路径。

### 9.2 提议中的作者命令

```text
songyan
├── project new | list | init     # [proposed] 别名；init 不在 M0
├── chapter list | status | continue   # continue 是 M4
├── variant generate | list | diff | pick | abandon   # M3
├── canon show                    # M0
├── canon edit | triage | confirm # M1
├── check                         # M1
├── review                        # M4
├── today                         # M0 起，只读
├── status                        # 与 today 分工：today 是下一步，status 是本会话计数
└── branch                        # 不做
```

M0 只实现 `canon show` 和 `today`。其余名字在对应里程碑之前 **不注册**。不注册「打印未实现」的空桩，避免帮助列表看起来像已经有抽卡。

`status` 不在 M0。M0 的 `today` 已经打印 canon / pending 计数。会话级计数（本轮 confirm 了几条）要等 M1 有写入之后再做，由 M1 技术方案决定它是 `today` 的加段还是单独的 `status`。

`project init`（几条硬规则草案进入 triage）和 `chapter list|status`（只读现有章节表）都不在 M0。若要做，写进 M1 技术方案，不在实现 M0 时顺手注册。

### 9.3 行为约束

| 命令 | 约束 |
|------|------|
| `canon show` / `today` | 只读。退出码 0 成功，1 项目或配置错误 |
| `canon triage` / `confirm` | 没有「抽取完自动 confirm」 |
| `variant generate --n` | 默认 2。不自动 pick |
| `variant pick` | 只改工作正文指针 |
| `chapter continue --count` | 默认 1 |
| `check` / `review` | 不改库、不入典 |
| `branch` | 不注册 |

作者向新命令提供 `--json`，习惯与 `doctor --json` 相同。V1.0 不交付 TUI。

建议退出码（M1 起的写命令与检查沿用）：`0` 成功；`1` 用户 / 配置 / 项目错误；`2` 业务闸门未过；`3` 预算耗尽。M0 只用 0 和 1。

Flag 名可以在实现评审时改。不能改的是：确认才入典，抽卡不覆盖 picked，故事线展示不等于 Canon。

---

## 10. 能力取舍

图例：**复用** 已有并接到新工作流；**改建** 实现还在，作者路径以后要变；**新建** 现在没有，而且某一里程碑需要；**延后** 不进 M0–M4。

### 10.1 复用

SQLite；体裁与项目模板；`doctor`；LangGraph 章节图（冒烟与日后的生成引擎）；质量门与文学审查（过程信号）；`load_chapter_plan_bible` 与 `plan_fact_gate`；`foreshadowings`；故事线三张规划实体；`export` / `backup` / `restore` / `bundle-run`；`profile`；`mark`；按角色的模型路由和成本记录；`import` 全组。

### 10.2 改建（都不是 M0）

| 项 | 现在 | 作者路径上的目标 | 里程碑 |
|----|------|------------------|--------|
| `run --auto-confirm` | 多章管线 | 维护者冒烟。作者走 chapter / variant / canon | 文案在该命令仍被作者误用时再改，不单为 M0 改 |
| `SettlementExtractor` | 接受后写结算库 | 助手路径改为提案。下一章只读已确认 Canon | M2 |
| 质量门 PASS | 容易被读成书写合格 | 过程门禁。文学看 S9 | 文档从本文件起。不改门的阈值 |
| 上下文组装 | 为长连跑准备 | 默认本章卡加有预算的硬事实，并露出 ContextEmergency | M4 |

### 10.3 新建

| 能力 | 里程碑 |
|------|--------|
| `canon show`、`today`（只读） | M0 |
| `canon edit|triage|confirm`、规则 `check` | M1 |
| stale、承诺阅读与人确认销账、抽取提案队列 | M2 |
| Variant 存储与 `variant *` | M3 |
| `chapter continue`、`review` 共审 | M4 |

### 10.4 延后

Git 式 Canon Branch、全屏 TUI、本地 Web、MCP 暴露 Canon、多书共用世界圣经、完整 POV 知情分层、Obsidian 双向同步、预算化 RAG 加强、从已确认事实回写回顾性计划卡。`index` 留在引擎里，助手里程碑不依赖它。

调研里的外部产品只提供模式（提案确认、状态字段、多变体不覆盖、粗粒度脚手架），不引入为运行时依赖。

---

## 11. 风险

| 风险 | 表现 | 缓解 | 不在哪一程假装修好 |
|------|------|------|--------------------|
| 抽卡费用 | N 份稿近似放大写作费用。Ch1–10 与都市灵异对照的数量级见 STATUS，那不是 Variant 报价 | 默认 N=2；重审计只对 picked；`--budget-cny` | M0–M2 不生成，没有这笔账 |
| ContextEmergency / DG-1 | Ch1–10 平均 revision 1.7，十章都出现应急 | 助手默认单章；注入有预算；把次数露出来 | 抽卡不会根治。M0 不改上下文组装 |
| 所有权 | 人直接采纳抽卡、不再改 | 文案称草稿；看 S5；M4 可警告「几乎没改」 | 不做句级补全 |
| 导入后续写未验收 | 自动化导入测试已有，真实续写没有报告 | W3 完成定义停在 triage，直到 STATUS 记下那份报告 | M4 也不把续写写成已验证 |
| pending 被当成事实 | 展示或抽取写进圣经 | 分段标题；S8 测试；结算库只读打标 | M0 只增加可见性，不增加写入 |
| 故事线被当成 Canon | 大纲看起来像已发生的事 | 单独标题和 JSON 键 | M0 不合并两套表 |
| 两套产品声音 | 工作台调研曾写「写作可选」 | 以本文为准。调研不删，但不作为定义 | — |
| 过程门绿、稿子不可读 | Ch1–10 已发生 | S9 与过程门分开 | 不靠再加一个门 |

文学质量由人拥有。Songyan 提供探索、账本和审计。它不宣称稿子可上架、可连载、可发表。一次 LLM judge 不能代替结构化 `check`，也不能给文学签字。

---

## 12. 接受与开工

本文进仓库只表示需求可以审。**书面接受之前：**

- 不改 `src/`、`tests/`、`pyproject.toml`。
- 不写 `tasks/200` 及以后的任务桩。
- 不把 `[proposed]` 命令写进 README 的「已经支持」。
- 不跑无人值守的长篇生成来「验证 V1.0」。

**书面接受的对象是四份一起：** 本文、[tech-m0.md](tech-m0.md)、仓库根 `AGENTS.md`、[STATUS.md](STATUS.md)。只接受其中一份不够开工。

接受之后的第一刀只有 M0，按技术方案里的切片，一次一个任务文件。M1 代码要等 M0 验收通过，并且另有一份被接受的 M1 技术方案。

请 owner 特别看这几处收束（框架未改，边界写死了）：

1. M0 是只读真命令，不是「全部作者命令的未实现桩」。
2. 旧 Phase 1 拆成 M0 / M1 / M2。结算器改提案是 M2，不是 M1。
3. 指标编号改为 S1–S9，里程碑占用 M0–M4。
4. 故事线与 Canon 分开展示、分表存储。
5. 都市灵异《末班铜牌》是验收夹具和试点，不是唯一题材，也不再开召回 KPI。
6. `rejected`、`hardness`、variant 表的物理设计留给对应里程碑的技术方案。

---

## 13. 文档关系

| 文档 | 关系 |
|------|------|
| 本文 | 现行产品需求（待书面接受） |
| [tech-m0.md](tech-m0.md) | 只规划 M0。以后的里程碑不在那里展开 |
| [archive/prd-v1-writing-assist-2026-10-26.md](archive/prd-v1-writing-assist-2026-10-26.md) | 上一稿全文。总体框架已接受；实现以本文为准 |
| [ADR-0001](adr/0001-plan-first-facts.md) | 事实由计划和人写入；抽取不自动成为权威 |
| [ROADMAP-plan-first.md](ROADMAP-plan-first.md) | 阶段 A–C 已关闭 |
| [STATUS](STATUS.md) | 工程事实。本文的 proposed 命令没有落地之前，以 STATUS 为准 |
| [HANDOFF-mew.md](HANDOFF-mew.md) | 当天的下一步 |
| `tasks/` | 接受之后才从 200 起写。没有任务文件就不开工 |
