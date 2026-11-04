# M1 技术方案：人确认入典与规则检查

- **状态：** 2026-11-03 Asia/Shanghai。只覆盖 [prd-v1.md](prd-v1.md) 的 **M1**。**已接受（Mew 拍板）。** 步 1–5 已进 `main`；§6–7 代码验收 **PASS**（`main` `69d7ece`，2026-11-04）。接受注记见文末。
- **本文不做的决定：** 不规划 M2–M4 的实现。那些里程碑以后各写一份技术方案（`docs/tech-m2.md` 起），再开工。不要把本文扩成路线图。
- **前置：** M0 步 1–4 与 tech-m0 §6–7 代码验收已在 `main` `80f4107` **PASS**（见 [STATUS.md](STATUS.md)）。包版本仍是 `0.5.0`。

Owner 要求技术方案按里程碑、小步推进。M1 只让作者把人写出的计划行显式确认入典，并包一层不写库的规则 `check`。

---

## 1. 目标

作者对一个已有项目能走完 W0 的写半边，以及 W6：

- 写出一条计划行（默认 `pending`；人写路径强制 `source=human`，见 §4.2）
- triage：`confirm` / `dismiss` 为改变持久状态的主表面；可选 UX 的 `accept` **不得写库**（见 §3.4 / §4.2）
- `confirm` 之后该行出现在 Canon（`approved`），且进入 `load_chapter_plan_bible`
- `check` 对一章正文给出带证据的规则报告，**不写库、不入典**

不调用模型写事实，不把 `SettlementExtractor` 接进提案队列，不抽卡，不 `chapter continue`，不自动标脏。

---

## 2. 仓库里已经有的

M1 在只读工作台之上加写路径与检查包装，不重写这些模块的权威语义。

| 能力 | 位置 | M1 怎么用 |
|------|------|-----------|
| 只读工作台 | `cli/commands/workbench.py` 的 `canon show` / `today` | 保留。confirm 前后用它们做看见 → 再看见。步 5 更新 `today` 的固定 `next` 文案（见 §5） |
| Canon / pending 读写 | `PlanFactRepository` 的 `list_canon_*` / `list_pending_*` / `write_*` | confirm → `approved`；dismiss → `rejected`（§3.4）。人写属性强制 `source=human`，以便 `list_canon_attributes` 在 confirm 后可见 |
| 本章圣经 | `load_chapter_plan_bible` | **只读锁定过滤语义**（只读 approved）。M1 用测试守住 S8，不改「pending / rejected 不得出现」 |
| 窄检查 | `run_plan_fact_gate` | 包成作者向 `check`。报告不写库。门**不**从正文发明属性摘录 |
| 章正文 | `ChapterHead.accepted_version_id` → `ChapterVersionRepository.get` → `ChapterVersion.content`（表 `chapter_versions`） | `check` 的 `chapter_text` 取自该章已存版本行的 `content`（与 `cli/commands/index.py` 同源约定） |
| 都市灵异夹具 | `dushi-lingyi` / 《末班铜牌》 | CLI / 门测试样本。不跑 LLM |
| 章节图 | `src/songyan/workflows/` | 不改 |
| 结算 | `apply_settlement`、`SettlementExtractor` | **不改写入目标表**（M2 才接提案） |
| 迁移 | `db/migrations.py` 的 `_MIGRATIONS` | **步 1 必做**：五张 `plan_*` 表的 `approval_status` CHECK 扩到含 `rejected`（见 §3.4 / §5 步 1） |
| 测试布局 | `tests/cli/` 不被默认 pytest 收集 | 新 CLI 测试放这里；圣经 / 计划卡回归仍放原位 |

现码 `approval_status` 只有 `approved` 与 `pending`（`PlanApprovalStatus`、仓库 `_APPROVAL`、五表 CHECK）。M1 **必须**扩到 `rejected`；**不加**第四态 `accepted`；不加 `hardness`、不加 variant 表。

---

## 3. 做、改、不做

### 3.1 做

1. `songyan canon edit`：人写出（或改）一条计划行，**默认 `pending`**；属性等带 `source` 的 kind **强制 `source=human`**（及使 confirm 后能进 Canon 的默认值）。输出写明未入典。
2. `songyan canon triage`（或等价旗标）：**状态变更主表面 = `confirm` + `dismiss`**。若保留 CLI 子命令名 `accept`，仅作非持久 UX（提醒去 `confirm`），**禁止**写 `approval_status` 或任何「已 accept 未入典」持久态。
3. `songyan canon confirm`：目标行写入 Canon（`approval_status=approved`）。**没有**单独的持久 `accepted` 中间态；confirm 本身就是入典。输出必须写明已入典。
4. `songyan check --project-id <id> --chapter N`：只读包装 `run_plan_fact_gate`，Markdown 报告（可选 `--json`）。见 §4.3。
5. 支持作者向 `--json`（与 `doctor --json` 习惯一致）。
6. CLI / 仓库测试覆盖第 6 节；S8：未 confirm 行不得进圣经。**验收最小 kind：entity + attribute**（§6）；其余 kind 若复用同一 edit/confirm/dismiss 路径且成本低可一并接通，但不挡 entity+attribute 先绿。

### 3.2 改

- 扩展 `workbench` 注册或并列注册 `register_canon_write_commands` / `register_check_commands`（名字实现时定；`main.py` 只加注册，不改既有命令行为，步 5 对 `today` 的 `next` 文案更新除外）。
- **`list_pending_*`（及 `canon show` 的 Pending 段）排除 `rejected`；`list_canon_*` 仍只含 `approved`。**
- **必做一条（或一组等价）迁移**：五张计划表 `plan_entities` / `plan_attributes` / `plan_events` / `plan_time_anchors` / `plan_clues` 的 `approval_status` CHECK 从 `('approved','pending')` 扩到含 `'rejected'`；同步 `PlanApprovalStatus`、`plan_fact_repo._APPROVAL` 与过滤逻辑。SQLite 改 CHECK 通常需重建表——迁移须写明重建步骤与兼容（见 §5 步 1）。**不可选。**

### 3.3 不做

- `SettlementExtractor` → 提案队列（**M2**）。
- `variant *`（**M3**）、`chapter continue` / `review`（**M4**）。
- 自动标脏 / `hardness` 列（**M2**）。
- 注册会让 `--help` 像已有抽卡的空桩：`variant`、`branch`、未规划的 `project init` / 独立 `status`。
- 改写作节点、提示词、质量门阈值、结算权威。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）。
- 真实模型、长窗 `run`、题材专用检查器。
- 在本文件里写 M2+ 的实现步骤。第 9 节只列「留给以后」。
- **持久第四态 `accepted`（「已 accept 未入典」）**；任何把 triage `accept` 写成库的设计。
- **为 `rejected` 行保留被覆盖前的正文历史**（M1 不做驳回正文史）。

### 3.4 持久状态与 dismiss（具体）

**持久 `approval_status` 只允许三态：`pending` | `approved` | `rejected`。没有第四态 `accepted`。**

| 动作 | 持久效果 |
|------|----------|
| `edit`（人写） | 写入/覆盖行；`approval_status=pending`；带 `source` 的 kind → `source=human` |
| `confirm` | `approval_status=approved`（入典）。一步完成；不经持久 `accepted` |
| `dismiss` | **保留行**，`approval_status=rejected`；不物理删除 |
| CLI `accept`（若保留） | **非持久**：不写 DB；仅提醒作者去 `confirm`。不得引入「已 accept 未入典」可读状态 |

短理由：

1. PRD 指标 **S1**（dismiss 比例说得清）与 **S2**（dismiss 有记录）需要驳回留下痕迹；删行会丢掉计数。
2. 与提案语义里的 `→ dismissed` 对齐，避免 M2 接队列时再翻一次存储语义。
3. 验收「dismiss 之后该 id 不在 `list_canon_*`」仍成立：`list_canon_*` 只读 `approved`。
4. `canon show` 默认 Pending 段不展示 `rejected`（已驳回不再待确认）。若以后要审计列表，另开只读旗标，不在 M1 首刀做。
5. 取消持久 `accepted`，避免作者与测试在「点头了但未入典」上分叉；入典的唯一写路径是 `confirm`。

同一稳定 id 在 `rejected` 之后若作者再次 `edit`：允许**覆盖同 id 内容**并把状态改回 `pending`，再走 `confirm`。M1 **不**保留被覆盖前的 rejected 正文历史。不提供「复活为 approved」的暗门（必须再 `confirm`）。

---

## 4. 接口

### 4.1 命令

```text
songyan canon edit    --project-id TEXT ...   # 写入/改写计划行，默认 pending；人写 source=human
songyan canon triage  --project-id TEXT ...   # 主表面：confirm | dismiss；accept 若有则非持久
songyan canon confirm --project-id TEXT ...   # 入典为 approved（可与 triage confirm 同义实现）
songyan check --project-id TEXT --chapter INT [--json]
```

具体参数名（按 kind、按 id、批量）在实现切片里定死，并与测试断言对齐。行为约束以本节与 PRD §6.3–6.4 为准。**M1 验收先锁 entity + attribute**；其它 kind 可共享同一套命令表面。

退出码（沿用 PRD §9.3）：

| 码 | 何时 |
|----|------|
| 0 | 写命令成功完成声明的动作；`check` 门通过（文案不得写成「可以发表」） |
| 1 | 数据库文件不存在、项目不存在、参数非法、id 冲突、缺库时不建文件 |
| 2 | `check`：无章可查（无可用已存版本正文），或有硬伤未过门。不自动改文、不自动改卡 |
| 3 | M1 **不使用**（无预算路径） |

缺库时的路径检查复用 M0：先查文件存在，再 `get_db()`，避免空库被建出。

### 4.2 写入语义

1. **edit**：只产生或更新非 Canon 行。默认 `approval_status=pending`。禁止「保存即 approved」，除非同一次调用的命令就是 `confirm` 且输出写明已入典。
2. **人写路径强制 `source=human`**：凡 `PlanAttribute`（及任何带 `PlanFactSource` 的写入）经 `canon edit` / 人写 triage 写出时，必须把 `source` 设为 `human`（不得默成 `plan` 或缺省到无法进 Canon 的值）。仓库侧 `list_canon_attributes` 对 approved 行要求 `source IN ('plan','human')`——人写确认后必须能出现在该列表。验收：人写 attribute → `confirm` → `list_canon_attributes` 含该 id。
3. **confirm**：目标行变为 `approved`；其后 `list_canon_*` 可见；在章窗口规则允许时出现在 `load_chapter_plan_bible`。**不**经过持久 `accepted`。
4. **dismiss**：`approval_status=rejected`。不进 Canon，不进圣经。
5. **edit 改草稿 / 改已 rejected 同 id**：改完必须再 `confirm` 才入典；同 id 覆盖 OK，无 rejected 正文史。
6. **accept（若 CLI 保留）**：零 DB 写；输出仅提醒尚未入典、请 `confirm`。不得让 `canon show` / 仓库读出「已 accept」态。
7. 命令路径**不调用模型**。不调用 `apply_settlement` 去改 plan 表。

### 4.3 `check`（W6）

1. **`chapter_text` 来源（项目既有约定，点名）：** 通过 `ChapterHeadRepository` 取该章 `ChapterHead.accepted_version_id`，再 `ChapterVersionRepository.get` 得到 `ChapterVersion`，以 **`ChapterVersion.content`**（表 `chapter_versions.content`）作为传给 `run_plan_fact_gate(..., chapter_text=...)` 的正文。无 head、无 `accepted_version_id`、或版本缺失/空正文 → 按「无章可查」退出码 2。不另开平行存正文的通道。
2. **属性「正文侧值」（M1）：** 门比较用的 `AttributeExtract` **不**由 `check` 从散文现抽。M1 薄包装向 `run_plan_fact_gate` 注入**夹具 / 测试注入**的 `AttributeExtract` 列表（与现门契约一致：`extracts` 入参；门本身不发明摘录）。生产路径若暂无观察器，M1 仍以夹具注入证明报告字段（实体、键、圣经值、正文侧值、严重度）；不把「从正文抽属性」做成 M1 范围。
3. 只读加载已批准圣经相关输入，调用现有 `run_plan_fact_gate`（必须提及、主张、类型化属性）。
4. 人读报告为 Markdown；`--json` 给出结构化问题列表。字段名实现时与门返回对齐，测试锁住关键键。
5. 报告可写「若要入典，另走 canon confirm」——**不是**默认动作；W6 全程不调用 confirm。
6. 检查前后：`plan_*` 行数与各行 `approval_status` 不变。

### 4.4 模块边界

| 文件 | 责任 |
|------|------|
| 扩展或新建 `src/songyan/cli/commands/` 下 workbench / canon / check 模块 | 参数、退出码、文本与 JSON；调用仓库与 `run_plan_fact_gate`；`check` 按 §4.3 装载 `ChapterVersion.content` 与注入的 extracts |
| 修改 `src/songyan/cli/main.py` | 增加注册 |
| 修改 `models/plan_facts.py` 的 `PlanApprovalStatus` | 纳入 `rejected` |
| 修改 `plan_fact_repo.py` | `_APPROVAL`；`rejected` 过滤；confirm / dismiss 写入；人写 `source=human` 助手。不含 LLM |
| **必做** `_MIGRATIONS` 项 | 五表 CHECK 含 `rejected`；SQLite 重建表并保留数据兼容 |
| 新建 / 扩展 `tests/cli/test_*` | CliRunner。不测文学，不调模型 |
| 扩展圣经 / 计划卡测试 | S8：pending / rejected 不进圣经；人写 attribute confirm 后在 `list_canon_attributes` |
| `workbench.py` 的 `_NEXT`（步 5） | 更新固定 `next`，不再暗示 confirm 不可用；同步调整锁死旧文案的 M0 测试 |

异步写与 M0 相同：模块内 `async def` + 命令里 `asyncio.run`。Click 回调里不新开 LangGraph。

### 4.5 本里程碑不做的命令表面

- 不注册独立 `status`：confirm 成功输出写明本条已入典即可；会话累计以后再说。
- 不注册 `project init`、`chapter list|status`：需要时改 PRD / 另开技术修订，不在 M1 编码时顺手挂上。

---

## 5. 小步

**本文已接受。** 按下列小步写 `tasks/20x` 编码任务。每步一个任务文档，一步一个可独立拒绝的 PR。不要合成一个大 PR。合并前 Mew COMMENT（不代 owner 点 APPROVE，除非另有授权）。

### 步 1 — `rejected` 迁移与仓库过滤（**下一刀**）

**产出（不可拆掉迁移）：**

1. **迁移（必做）：** 扩展全部五张计划表  
   `plan_entities` / `plan_attributes` / `plan_events` / `plan_time_anchors` / `plan_clues`  
   的 `approval_status` CHECK，使合法值为 `approved` | `pending` | `rejected`。SQLite 无法原地改 CHECK：迁移须按仓库既有风格 **重建表**（新建 → 拷数据 → 删旧 → 重命名 → 重建索引），并写明对已有 `approved`/`pending` 行的兼容（值集合超集，无需改行数据）。
2. 同步 `PlanApprovalStatus`、`plan_fact_repo._APPROVAL`（及一切解析/校验）。
3. `list_pending_*` / `canon show` 的 Pending **排除** `rejected`；`list_canon_*` 不变（仍只 `approved`；属性仍要求 `source IN ('plan','human')`）。

**测试：** 插入 `rejected` 行后，Canon / Pending / `load_chapter_plan_bible` 均不可见该 id（S8）。迁移在空库与含既有 plan 行的库上可重复跑通。

### 步 2 — `canon edit`（默认 pending，人写 `source=human`）

**产出：** 人可写入计划行（至少 **entity + attribute**）；attribute 强制 `source=human`；`canon show` Pending 可见；圣经不可见。

**测试：** 先红后绿。断言未 confirm 前不在 `list_canon_*` 与圣经（S8）。

### 步 3 — `confirm` + `dismiss`（主表面）

**产出：** confirm → `approved` 且 Canon / 圣经可见（在既有章窗口规则下）；dismiss → `rejected`。若实现 CLI `accept`，测试断言其 **不**改变 `approval_status`。同 id 在 rejected 后再次 edit：覆盖为 pending，无正文史要求。

**测试：** PRD §6.3 验收（以 entity+attribute 为硬门）；人写 attribute confirm 后出现在 `list_canon_attributes`。路径上无模型、不改结算目标表。

### 步 4 — `check`（W6）

**产出：** `check --chapter N` 报告；`chapter_text` 来自该章 `ChapterVersion.content`（§4.3）；属性正文侧值来自注入的 `AttributeExtract`；退出码 0/1/2 按 §4.1。

**测试：** PRD §6.4 验收 1–4。夹具构造已批准属性与注入 extracts 不一致；检查前后 plan 行不变；门不从散文发明 attributes。

### 步 5 — W0 闭环与 `today` 文案

**产出：**

1. 一条端到端 CLI 测试：`show` → `edit` → `confirm`/`dismiss` → `show` 再看见。
2. **更新 `today` 固定 `next`：** 现行 M0 文案 `M0 只读。确认入典和生成都不在本命令。` 在 M1 接通后会误导（暗示 confirm 仍不可用）。改为不再暗示 confirm 不可用的产品文案（具体句子实现时定，测试锁新句）。
3. **同步调整**任何锁死旧 `next` 字符串的 M0 测试（如 `tests/cli/test_workbench_commands.py` 的 `_NEXT`）：视为**有意的产品文案更新**，不是回归失败；在该步 PR 说明里写明「故意更新 M0 锁文案」。
4. 更新 `STATUS` / `HANDOFF` 为「M1 步 N 已落地」，**不要**写「V1.0 完成」。

每步合并前跑第 7 节命令。`git diff` 不得出现包版本 bump；不得改 `workflows/` 与 `settlement_extractor` 行为（步 1 的迁移除外时须在 PR 说明写明「仅 rejected CHECK / 重建」）。

---

## 6. 验收

与 PRD §6.3–6.4 及 **S8** 对齐，写成命令级清单。

**最小 kind（硬门）：`entity` + `attribute`。** 其它 kind（event / time_anchor / clue）若共享同一 edit/confirm/dismiss 实现且成本低，可一并接通与测；§6 与首轮合并门以 entity+attribute 先绿为准，不得因尚未接齐五类而阻塞 M1 代码验收。

1. 未 confirm 的新行不在 `load_chapter_plan_bible`（S8）。测试先红后绿。
2. confirm 之后，同一稳定 id 出现在对应 `list_canon_*`；**人写 attribute 出现在 `list_canon_attributes`**（`source=human`）。
3. dismiss 之后，该 id 的 `approval_status=rejected`，且不在 `list_canon_*`；默认 Pending 段不可见。
4. **无持久 `accepted` 态**；若 CLI 有 `accept`，调用后 DB 的 `approval_status` 不变。
5. 写命令与 `check` 路径不调用模型。
6. `apply_settlement` 写入目标表与 M1 开工前相同。
7. `check`：`chapter_text` 来自 `ChapterVersion.content`；不一致夹具（注入 `AttributeExtract`）报告点名实体、键、圣经值、正文侧值；检查前后 plan 行数与状态不变；W6 无 confirm；门不从散文发明 attributes。
8. 无章可查或硬伤：`check` 退出码 2。门通过：退出码 0，文案无「可以发表」。
9. `ruff check src/ tests/` 通过；默认 `pytest tests/ -q` 通过；本里程碑 CLI 测试通过；下列既有测试不改断言也通过（步 5 对 `_NEXT` 的有意更新除外，须在该步 PR 说明）：
   - `tests/db/test_plan_fact_cards.py`
   - `tests/db/test_dushi_lingyi_plan_facts.py`
   - `tests/plan_checks/test_plan_bible_runtime.py`
   - `tests/cli/test_workbench_commands.py`（M0 只读回归；步 5 可改 `_NEXT`）
10. 五表 `rejected` 迁移已落地；除该迁移外无无关 `migrations.py` 大改；无 `workflows/`、`agents/settlement_extractor/` 行为漂移；无 `pyproject.toml` 版本变化。

S1/S2 的产品日志要等命令装到作者机器之后才记周期；M1 **代码**验收以本节为准，不以一周使用时长为门。

---

## 7. 验证命令

```bash
ruff check src/ tests/
python -m pytest tests/db/test_plan_fact_cards.py tests/db/test_dushi_lingyi_plan_facts.py tests/plan_checks/test_plan_bible_runtime.py -q
python -m pytest tests/cli/test_workbench_commands.py -q
python -m pytest tests/cli/test_canon_write_commands.py tests/cli/test_check_command.py -q
```

（后两文件名可按实现调整；原则是 CLI 单独跑。）改动若含迁移，加跑与计划卡 / 圣经相关的 DB 测试。不必为了 M1 去跑真实 LLM。

---

## 8. 风险

| 风险 | 处理 |
|------|------|
| 保存即被当成 Canon | 默认 pending；confirm 文案强制「已入典」；测试锁 S8 |
| 持久 `accepted` 造成「点头未入典」分叉 | §3.4 禁止第四态；accept 若有则非持久 |
| 人写 attribute 因 `source` 默认进不了 Canon | 人写路径强制 `source=human`；测试锁 `list_canon_attributes` |
| dismiss 删行导致 S1 失真 | §3.4 选定 `rejected`，不删行 |
| SQLite CHECK 漏迁或只改一表 | 步 1 强制五表重建式迁移 + 模型/仓库同步 |
| `check` 从散文现抽属性 | §4.3：M1 只用注入的 `AttributeExtract`；门不发明摘录 |
| `check` 被当成入典 | 报告只提示另走 confirm；测试断言无 confirm、行不变 |
| 实现时顺手接结算抽取 | 评审拒绝。接提案是 M2 |
| 想加 hardness / stale | 停。属 M2，另写 tech-m2 |
| `get_db()` 缺库建文件 | 复用 M0 路径检查与测试 |
| 范围膨胀（variant / continue / 五类全齐才验收） | 停。entity+attribute 硬门；改 PRD 边界并另审 |
| `today` 仍写「确认入典不在本命令」 | 步 5 更新固定 `next` 与锁文案测试 |

都市灵异只作夹具题材标签。命令里不出现「若题材是都市灵异则……」分支。

---

## 9. 以后的技术方案

本文已接受；M1 代码验收已 **PASS**（`69d7ece`）。**在 owner 书面接受 `docs/tech-m2.md` 之前**，不写 M2 的代码，也不在本文件追加 M2 任务清单。

下一份技术文才决定的事（本文故意不定死）：

- 硬变更用命令旗标还是 `hardness` 列；标脏范围算法
- `SettlementExtractor` 输出如何进入提案队列；结算库哪些表保持原样只读打标
- 承诺队列销账的确认命令形状
- Variant 表与 `parent_canon_fingerprint`（M3）
- `chapter continue` / `review`（M4）
- 生产路径上从正文观察 / 抽取 `AttributeExtract`（超出 M1 夹具注入）
- rejected 正文历史或审计列表 UI

那些属于 M2、M3、M4 或后续修订各自的 `docs/tech-m*.md`。每份仍要书面接受之后才能改对应的代码。

---

## 接受注记

**Mew 拍板 / 接受** tech-m1（含上文绑定决策：无持久 `accepted`；人写 `source=human`；步 1 五表 `rejected` 迁移必做；`check` 正文取 `ChapterVersion.content`、属性侧值用注入 `AttributeExtract`；验收最小 kind = entity+attribute；rejected 后同 id 覆盖无正文史；步 5 更新 `today` 的 `next`）：**2026-11-03 Asia/Shanghai**，依据 owner **t82u** 授权「评估缺口与决策由 Mew 拍板后继续推进」。

**合入本文档 PR 之后的下一刀：** M1 **步 1** 编码（`rejected` 迁移 + 过滤），TDD；开 PR 后 **Mew COMMENT** 再合并（勿在无 COMMENT 时自合）。本接受注记不授权改 `src/` 行为于本文档 PR 内。
