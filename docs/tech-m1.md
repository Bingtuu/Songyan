# M1 技术方案：人确认入典与规则检查

- **状态：** 2026-11-03。只覆盖 [prd-v1.md](prd-v1.md) 的 **M1**。**draft，等待 owner 书面接受。** 接受之前禁止改 `src/` / `tests/` 行为，禁止新建 `tasks/20x` 编码任务。
- **本文不做的决定：** 不规划 M2–M4 的实现。那些里程碑以后各写一份技术方案（`docs/tech-m2.md` 起），再开工。不要把本文扩成路线图。
- **前置：** M0 步 1–4 与 tech-m0 §6–7 代码验收已在 `main` `80f4107` **PASS**（见 [STATUS.md](STATUS.md)）。包版本仍是 `0.5.0`。

Owner 要求技术方案按里程碑、小步推进。M1 只让作者把人写出的计划行显式确认入典，并包一层不写库的规则 `check`。

---

## 1. 目标

作者对一个已有项目能走完 W0 的写半边，以及 W6：

- 写出一条计划行（默认 `pending`）
- triage：accept / edit / dismiss
- confirm 之后该行出现在 Canon，且进入 `load_chapter_plan_bible`
- `check` 对一章正文给出带证据的规则报告，**不写库、不入典**

不调用模型写事实，不把 `SettlementExtractor` 接进提案队列，不抽卡，不 `chapter continue`，不自动标脏。

---

## 2. 仓库里已经有的

M1 在只读工作台之上加写路径与检查包装，不重写这些模块的权威语义。

| 能力 | 位置 | M1 怎么用 |
|------|------|-----------|
| 只读工作台 | `cli/commands/workbench.py` 的 `canon show` / `today` | 保留。confirm 前后用它们做看见 → 再看见 |
| Canon / pending 读写 | `PlanFactRepository` 的 `list_canon_*` / `list_pending_*` / `write_*` | confirm 走写入并把 `approval_status` 设为 `approved`；dismiss 见 §3.4 |
| 本章圣经 | `load_chapter_plan_bible` | **只读锁定过滤语义**（只读 approved）。M1 用测试守住 S8，不改「pending 不得出现」 |
| 窄检查 | `run_plan_fact_gate` | 包成作者向 `check`。报告不写库 |
| 都市灵异夹具 | `dushi-lingyi` / 《末班铜牌》 | CLI / 门测试样本。不跑 LLM |
| 章节图 | `src/songyan/workflows/` | 不改 |
| 结算 | `apply_settlement`、`SettlementExtractor` | **不改写入目标表**（M2 才接提案） |
| 迁移 | `db/migrations.py` 的 `_MIGRATIONS` | 仅当 §3.4 需要扩展 `approval_status` 时加**一条**最小迁移 |
| 测试布局 | `tests/cli/` 不被默认 pytest 收集 | 新 CLI 测试放这里；圣经 / 计划卡回归仍放原位 |

现码 `approval_status` 只有 `approved` 与 `pending`。M1 按 §3.4 扩展；不加 `hardness`、不加 variant 表。

---

## 3. 做、改、不做

### 3.1 做

1. `songyan canon edit`：人写出（或改）一条计划行，**默认 `pending`**。输出写明未入典。
2. `songyan canon triage`：对 pending 做 `accept` / `edit` / `dismiss`（子命令或等价旗标，实现时定名，行为不变）。
3. `songyan canon confirm`：把已 accept（或本命令一次完成 accept）的行写入 Canon（`approved`）。输出必须写明已入典。
4. `songyan check --project-id <id> --chapter N`：只读调用 `run_plan_fact_gate`，Markdown 报告（可选 `--json`）。
5. 支持作者向 `--json`（与 `doctor --json` 习惯一致）。
6. CLI / 仓库测试覆盖第 6 节；S8：未 confirm 行不得进圣经。

### 3.2 改

- 扩展 `workbench` 注册或并列注册 `register_canon_write_commands` / `register_check_commands`（名字实现时定；`main.py` 只加注册，不改既有命令行为）。
- 若采用 §3.4 的 `rejected`：`list_pending_*`（及 `canon show` 的 Pending 段）**排除** `rejected`；`list_canon_*` 仍只含 `approved`。
- 必要时一条迁移，允许 `approval_status='rejected'`。

### 3.3 不做

- `SettlementExtractor` → 提案队列（**M2**）。
- `variant *`（**M3**）、`chapter continue` / `review`（**M4**）。
- 自动标脏 / `hardness` 列（**M2**）。
- 注册会让 `--help` 像已有抽卡的空桩：`variant`、`branch`、未规划的 `project init` / 独立 `status`。
- 改写作节点、提示词、质量门阈值、结算权威。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）。
- 真实模型、长窗 `run`、题材专用检查器。
- 在本文件里写 M2+ 的实现步骤。第 9 节只列「留给以后」。

### 3.4 dismiss 决定（具体）

**选定：保留行，将 `approval_status` 设为 `rejected`；不物理删除。**

短理由：

1. PRD 指标 **S1**（dismiss 比例说得清）与 **S2**（dismiss 有记录）需要驳回留下痕迹；删行会丢掉计数。
2. 与提案语义里的 `→ dismissed` 对齐，避免 M2 接队列时再翻一次存储语义。
3. 验收「dismiss 之后该 id 不在 `list_canon_*`」仍成立：`list_canon_*` 只读 `approved`。
4. `canon show` 默认 Pending 段不展示 `rejected`（已驳回不再待确认）。若以后要审计列表，另开只读旗标，不在 M1 首刀做。

同一稳定 id 在 `rejected` 之后若作者再次 `edit` 写出：视为新的 pending 提案（覆盖同 id 的内容并把状态改回 `pending`），再走 confirm。不提供「复活为 approved」的暗门。

---

## 4. 接口

### 4.1 命令

```text
songyan canon edit   --project-id TEXT ...   # 写入/改写计划行，默认 pending
songyan canon triage --project-id TEXT ...   # accept | edit | dismiss
songyan canon confirm --project-id TEXT ...  # 入典为 approved
songyan check --project-id TEXT --chapter INT [--json]
```

具体参数名（按 kind、按 id、批量）在实现切片里定死，并与测试断言对齐。行为约束以本节与 PRD §6.3–6.4 为准。

退出码（沿用 PRD §9.3）：

| 码 | 何时 |
|----|------|
| 0 | 写命令成功完成声明的动作；`check` 门通过（文案不得写成「可以发表」） |
| 1 | 数据库文件不存在、项目不存在、参数非法、id 冲突、缺库时不建文件 |
| 2 | `check`：无章可查，或有硬伤未过门。不自动改文、不自动改卡 |
| 3 | M1 **不使用**（无预算路径） |

缺库时的路径检查复用 M0：先查文件存在，再 `get_db()`，避免空库被建出。

### 4.2 写入语义

1. **edit**：只产生或更新非 Canon 行。默认 `approval_status=pending`。禁止「保存即 approved」，除非同一次调用的命令就是 `confirm` 且输出写明已入典。
2. **triage accept**：标记人已点头，但仍未入典，直到 `confirm`（或 `confirm` 一次做完 accept+入典）。
3. **triage dismiss**：`approval_status=rejected`。不进 Canon，不进圣经。
4. **triage / edit 改草稿**：改完必须再 `confirm` 才入典。
5. **confirm**：目标行变为 `approved`；其后 `list_canon_*` 可见；在章窗口规则允许时出现在 `load_chapter_plan_bible`。
6. 命令路径**不调用模型**。不调用 `apply_settlement` 去改 plan 表。

### 4.3 `check`（W6）

1. 只读加载该章正文与已批准圣经相关输入，调用现有 `run_plan_fact_gate`（必须提及、主张、类型化属性）。
2. 人读报告为 Markdown；`--json` 给出结构化问题列表（实体、键、圣经值、正文侧值、严重度）。字段名实现时与门返回对齐，测试锁住关键键。
3. 报告可写「若要入典，另走 canon triage」——**不是**默认动作；W6 全程不调用 confirm。
4. 检查前后：`plan_*` 行数与各行 `approval_status` 不变。

### 4.4 模块边界

| 文件 | 责任 |
|------|------|
| 扩展或新建 `src/songyan/cli/commands/` 下 workbench / canon / check 模块 | 参数、退出码、文本与 JSON；调用仓库与 `run_plan_fact_gate` |
| 修改 `src/songyan/cli/main.py` | 增加注册 |
| 视需要修改 `plan_fact_repo.py` | `rejected` 过滤；confirm / dismiss 写入助手。不含 LLM |
| 视需要一条 `_MIGRATIONS` 项 | 仅放开 `rejected` |
| 新建 / 扩展 `tests/cli/test_*` | CliRunner。不测文学，不调模型 |
| 扩展圣经 / 计划卡测试 | S8：pending / rejected 不进圣经 |

异步写与 M0 相同：模块内 `async def` + 命令里 `asyncio.run`。Click 回调里不新开 LangGraph。

### 4.5 本里程碑不做的命令表面

- 不注册独立 `status`：confirm 成功输出写明本条已入典即可；会话累计以后再说。
- 不注册 `project init`、`chapter list|status`：需要时改 PRD / 另开技术修订，不在 M1 编码时顺手挂上。

---

## 5. 小步

**owner 书面接受本文之后**才写 `tasks/20x` 编码任务。每步一个任务文档，一步一个可独立拒绝的 PR。不要合成一个大 PR。

### 步 1 — `rejected` 与仓库过滤

**产出：** `approval_status` 允许 `rejected`；`list_pending_*` / show 的 Pending 排除之；`list_canon_*` 不变。最小迁移（若现约束挡值）。

**测试：** 插入 `rejected` 行后，Canon / Pending / `load_chapter_plan_bible` 均不可见该 id（S8）。

### 步 2 — `canon edit`（默认 pending）

**产出：** 人可写入一条计划行；`canon show` Pending 可见；圣经不可见。

**测试：** 先红后绿。断言未 confirm 前不在 `list_canon_*` 与圣经（S8）。

### 步 3 — `triage` + `confirm`

**产出：** accept / edit / dismiss / confirm。dismiss → `rejected`；confirm → `approved` 且 Canon / 圣经可见（在既有章窗口规则下）。

**测试：** PRD §6.3 验收 1–5。路径上无模型、不改结算目标表。

### 步 4 — `check`（W6）

**产出：** `check --chapter N` 报告；退出码 0/1/2 按 §4.1。

**测试：** PRD §6.4 验收 1–4。夹具构造已批准属性与正文不一致；检查前后 plan 行不变。

### 步 5 — W0 闭环文档同步

**产出：** 一条端到端 CLI 测试：`show` → `edit` → `triage`/`confirm` → `show` 再看见；更新 `STATUS` / `HANDOFF` 为「M1 步 N 已落地」，**不要**写「V1.0 完成」。

每步合并前跑第 7 节命令。`git diff` 不得出现包版本 bump；不得改 `workflows/` 与 `settlement_extractor` 行为（步 1 的迁移除外时须在 PR 说明写明「仅 rejected」）。

---

## 6. 验收

与 PRD §6.3–6.4 及 **S8** 对齐，写成命令级清单：

1. 未 confirm 的新行不在 `load_chapter_plan_bible`（S8）。测试先红后绿。
2. confirm 之后，同一稳定 id 出现在对应 `list_canon_*`。
3. dismiss 之后，该 id 的 `approval_status=rejected`，且不在 `list_canon_*`；默认 Pending 段不可见。
4. 写命令与 `check` 路径不调用模型。
5. `apply_settlement` 写入目标表与 M1 开工前相同。
6. `check`：不一致夹具报告点名实体、键、圣经值、正文侧值；检查前后 plan 行数与状态不变；W6 无 confirm。
7. 无章可查或硬伤：`check` 退出码 2。门通过：退出码 0，文案无「可以发表」。
8. `ruff check src/ tests/` 通过；默认 `pytest tests/ -q` 通过；本里程碑 CLI 测试通过；下列既有测试不改断言也通过：
   - `tests/db/test_plan_fact_cards.py`
   - `tests/db/test_dushi_lingyi_plan_facts.py`
   - `tests/plan_checks/test_plan_bible_runtime.py`
   - `tests/cli/test_workbench_commands.py`（M0 只读回归）
9. 除「`rejected` 所需的一条迁移」外，无无关 `migrations.py` 大改；无 `workflows/`、`agents/settlement_extractor/` 行为漂移；无 `pyproject.toml` 版本变化。

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
| dismiss 删行导致 S1 失真 | §3.4 选定 `rejected`，不删行 |
| `check` 被当成入典 | 报告只提示另走 triage；测试断言无 confirm、行不变 |
| 实现时顺手接结算抽取 | 评审拒绝。接提案是 M2 |
| 想加 hardness / stale | 停。属 M2，另写 tech-m2 |
| `get_db()` 缺库建文件 | 复用 M0 路径检查与测试 |
| 范围膨胀（variant / continue） | 停。改 PRD 边界并另审，不在实现 PR 里扩 |

都市灵异只作夹具题材标签。命令里不出现「若题材是都市灵异则……」分支。

---

## 9. 以后的技术方案

本文接受且 M1 代码验收通过之前，不写 M2 的代码，也不在本文件追加 M2 任务清单。

下一份技术文才决定的事（本文故意不定死）：

- 硬变更用命令旗标还是 `hardness` 列；标脏范围算法
- `SettlementExtractor` 输出如何进入提案队列；结算库哪些表保持原样只读打标
- 承诺队列销账的确认命令形状
- Variant 表与 `parent_canon_fingerprint`（M3）
- `chapter continue` / `review`（M4）

那些属于 M2、M3、M4 各自的 `docs/tech-m*.md`。每份仍要 owner 书面接受之后才能改对应的代码。
