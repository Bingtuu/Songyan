# M0 技术方案：只读事实与故事线工作台

- **状态：** 2026-11-01。只覆盖 [prd-v1.md](prd-v1.md) 的 **M0**。待 owner 与 PRD、`AGENTS.md`、`docs/STATUS.md` 一起书面接受。
- **本文不做的决定：** 不规划 M1–M4 的实现。那些里程碑以后各写一份技术方案（`docs/tech-m1.md` 起），再开工。不要把本文扩成路线图。
- **开工门：** 四份文档都有书面接受之前，不要改 `src/` 或 `tests/`，不要写 `tasks/200`。

Owner 要求技术方案按第一个里程碑、小步推进。M0 只让作者看见已经存在的账，不新增一种账。

---

## 1. 目标

作者对一个已有项目执行两条只读命令，能分清：

- 已确认计划事实（Canon）
- 同表中的 pending 行（不是 Canon）
- 故事线骨架（大纲 / 弧 / 线索，不是 Canon）

不调用模型，不写库，不改下一章事实圣经的过滤规则。

---

## 2. 仓库里已经有的

M0 只包一层 CLI，不重写这些模块。

| 能力 | 位置 | M0 怎么用 |
|------|------|-----------|
| Click 入口 | `src/songyan/cli/main.py` 末尾的 `register_*_commands(cli)` | 照 `quality.py` / `import_pipeline.py` 加一个注册函数 |
| 项目是否存在 | `ProjectRepository.get` | 没有行就退出码 1 |
| Canon / pending | `PlanFactRepository.list_canon_*` 与 `list_pending_*` | 实体、属性、事件、时间锚、线索各一对 |
| 本章圣经 | `load_chapter_plan_bible` | **只读锁定**。不改实现。pending 不得出现 |
| 窄检查 | `run_plan_fact_gate` | M0 **不**包成 `check`。那是 M1 |
| 故事线 | `NarrativeRepository.get_outline`、`list_arc_plans`、`list_threads`、`count_threads_by_status` | 只读，单独成段 |
| 都市灵异夹具 | `bundled_dushi_lingyi_fixture`、`load_plan_fact_fixture`、`DUSHI_LINGYI_PROJECT_ID`（`dushi-lingyi`，《末班铜牌》） | CLI 测试的 Canon 样本。不跑 LLM |
| 章节图 | `src/songyan/workflows/`（LangGraph） | 不改 |
| 结算 | `apply_settlement`、`SettlementExtractor` | 不改 |
| 迁移 | `src/songyan/db/migrations.py` 的 `_MIGRATIONS` | 不加迁移 |
| 测试布局 | `tests/cli/` 不被默认 pytest 收集；CI 单独跑 `pytest tests/cli` | 新测试放这里 |

`approval_status` 现只有 `approved` 与 `pending`。M0 不扩展枚举。

---

## 3. 做、改、不做

### 3.1 做

1. `songyan canon show --project-id <id>`：打印 Canon、Pending、Storyline 三段。
2. `songyan today --project-id <id>`：打印计数和固定的下一步说明。
3. 两条都支持 `--json`。
4. `canon show` 支持 `--kind entity|attribute|event|time_anchor|clue|storyline`。省略则三段都打（pending 跟所选事实种类走；`--kind storyline` 时不打事实表）。
5. CLI 测试覆盖第 6 节。

### 3.2 改

只改 `src/songyan/cli/main.py` 的注册处：调用新的 `register_workbench_commands(cli)`。不改现有命令的参数和行为。

### 3.3 不做

- `canon edit` / `triage` / `confirm`、`check`、`review`、`variant`、`chapter`、`project` 别名、`status`、`branch`。这些名字 M0 **不注册**，以免 `--help` 像已经能抽卡。
- 任何 `INSERT` / `UPDATE` / `DELETE`。包括「顺手把空故事线写成空行」。
- 新表、新列、新迁移、`hardness`、`rejected`、variant 表。
- 改 `load_chapter_plan_bible`、`plan_fact_gate`、写作节点、提示词、结算器、质量门阈值。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）。
- 改 README，把 `canon show` 写成已经支持。代码 PR 合并前，PRD 里这两条仍是 `[proposed]`。代码 PR 若改帮助文本，只描述只读行为。
- 真实模型、都市灵异召回实验、长窗 `run`。
- 在本文件里写 M1 的接口草案之外的实现步骤。第 9 节只列「留给以后」，防止做到一半越界。

---

## 4. 接口

### 4.1 命令

```text
songyan canon show --project-id TEXT [--kind CHOICE] [--json]
songyan today --project-id TEXT [--json]
```

`--kind` 的可选值：`entity`、`attribute`、`event`、`time_anchor`、`clue`、`storyline`。

退出码：

| 码 | 何时 |
|----|------|
| 0 | 项目存在，读完。内容可以全空 |
| 1 | 数据库文件不存在、项目不存在、参数非法 |

M0 不使用退出码 2 或 3。

### 4.2 读之前

1. 用 `songyan.db.connection.get_db_path()` 取 SQLite 路径（它读 `songyan.config.settings.database_url`）。
2. 路径不是已存在的文件：向 stderr 写明找不到库，退出码 1。**不要**调用 `get_db()` 或 `init_schema()`。`get_db()` 会 `mkdir` 并让 `sqlite3` 把空文件建出来。
3. 文件存在：`ProjectRepository.get(project_id)` 为 `None` 则退出码 1。
4. 其后只调用第 2 节列出的读方法。Canon 段展示这些方法的返回值，不要在 CLI 里再写一套过滤。`list_canon_attributes` 已经排除非 `plan`/`human` 的来源。
5. `canon show` 的 Canon 段是**整个项目**的已批准行，不是某一章的 `load_chapter_plan_bible`。圣经还会按章窗口裁掉未引用的实体。两者不要打成同一份。pending 测试只断言「该 id 不在圣经」，不断言「approved 全集等于圣经」。

### 4.3 人读的文本

三段标题固定，测试用子串断言，不要靠对齐空格：

```text
# Canon（approved）
# Pending（不是 Canon）
# Storyline（规划骨架，不是已确认事实）
```

空段在标题下写 `（空）`。Pending 段的每一行带 `approval_status=pending`。Storyline 段若有大纲，打印 `core_conflict` 与弧的数量；线索用 `count_threads_by_status` 的计数，不把 `PlotThread.status` 说成 Canon 的 `approval_status`。

`today` 的人读文本至少包含：`canon_rows`、`pending_rows`、`storyline_arcs`，以及这一句原文：

```text
M0 只读。确认入典和生成都不在本命令。
```

### 4.4 JSON

`canon show --json` 的顶层键只有这三个，外加 `project_id`：

```text
project_id: str
canon:    { entities, attributes, events, time_anchors, clues }
pending:  { entities, attributes, events, time_anchors, clues }
storyline: { outline, arcs, threads }
```

值用现有 Pydantic 模型的 `model_dump(mode="json")`。不要加展示用的别名字段。`--kind` 过滤时，未请求的事实列表为 `[]`，键仍在。`outline` 没有行时为 `null`。

`today --json`：

```text
project_id: str
canon_counts:   { entity, attribute, event, time_anchor, clue }
pending_counts: { 同上 }
storyline: { has_outline: bool, arc_count: int, thread_counts: { status: int } }
next: "M0 只读。确认入典和生成都不在本命令。"
```

`canon_counts` 是各列表长度，不是字节。测试断言 pending 实体计数与插入行一致，并且 `next` 等于上面这句。

### 4.5 模块边界

| 文件 | 责任 |
|------|------|
| 新建 `src/songyan/cli/commands/workbench.py` | 参数、退出码、文本与 JSON。调用仓库读方法。不含 SQL |
| 修改 `src/songyan/cli/main.py` | 增加一行注册 |
| 新建 `tests/cli/test_workbench_commands.py` | CliRunner。不测文学，不调模型 |
| 不改 `plan_fact_repo.py` / `narrative_repo.py` | 读方法已经够用 |

注册函数名：`register_workbench_commands(cli: click.Group) -> None`。

异步读放在模块内的 `async def`，命令函数用 `asyncio.run`，与 `list_projects` 相同。Click 回调里不新开 LangGraph。

---

## 5. 小步

接受之后才写任务文件。每步一个 `tasks/200+` 文档，一步一个可独立拒绝的 PR。不要四步合成一个大 PR。

### 步 1 — 只读 Canon / pending

**产出：** `canon show` 打出事实五类的 approved 与 pending。还没有故事线段也可以先合并，但标题 `# Storyline` 若已印出，必须是 `（空）`，不能伪造大纲。

**测试：** 加载 `dushi-lingyi` 夹具，approved 实体数大于 0。再构造 `PlanEntity(..., approval_status="pending")` 并 `write_entity`（测试夹具准备，不是命令的写入；默认值是 `approved`，必须显式写成 pending）。`canon show` 的 Canon 段不含该 `entity_id`，Pending 段含它。`load_chapter_plan_bible` 的 `entity_ids` 不含它。数据库 URL 的 monkeypatch 对齐 `tests/cli/test_quality_commands.py`（`songyan.config.settings`）。

### 步 2 — 故事线段

**产出：** 第三段和 JSON `storyline`。用测试自行 `upsert_outline` + `add_arc_plan` + `add_thread` 准备数据（仍是测试夹具，命令本身只读）。断言冲突句出现在 Storyline 段、不出现在 `# Canon` 段。无故事线的 `dushi-lingyi` 库退出码 0 且该段为 `（空）`。

若步 1 已经打印了空的 Storyline 标题，步 2 只填内容，不改 Canon 段的格式。

### 步 3 — `today`

**产出：** 计数与固定 `next` 句。测试在调用前后对计划表做 `COUNT(*)`，数值相同。不 mock 一个生成器来证明「没调用」；代码审查看 `workbench.py` 的 import 列表：不得导入 `workflows`、`settlement_extractor`、`llm`。

### 步 4 — 缺失库与缺失项目

**产出：** 两条命令在文件不存在、以及文件在但 `project_id` 未知时退出码 1。断言目标路径在「文件不存在」用例之后仍然不存在。

步 4 可以和步 3 分 PR。不要为了少一次评审把缺失库的行为留到「以后再补」。

每步合并前跑第 7 节的命令。行为有变就更新 `docs/STATUS.md` 与 `docs/HANDOFF-mew.md`：写「M0 步 N 已落地」，不要写「V1.0 完成」。README 仍不记载进度。

---

## 6. 验收

与 PRD 第 6.2 节同一组，这里写成命令：

1. `dushi-lingyi` 上 `canon show` 退出码 0，approved 段非空（夹具本身有卡）。
2. 插入的 pending 实体只出现在 Pending 段。
3. 该实体不在 `load_chapter_plan_bible`。
4. 故事线在单独标题和 JSON 键 `storyline` 中；缺失时为空且退出码 0。
5. `today` 不写库；`next` 为第 4.4 节那句。
6. 缺库或缺项目退出码 1；缺库时不创建文件。
7. `ruff check src/ tests/` 通过。默认 `pytest tests/ -q` 仍通过。`pytest tests/cli/test_workbench_commands.py -q` 通过。下列既有测试不改断言也通过：
   - `tests/db/test_plan_fact_cards.py`
   - `tests/db/test_dushi_lingyi_plan_facts.py`
   - `tests/plan_checks/test_plan_bible_runtime.py`
8. `git diff` 里没有 `pyproject.toml` 版本变化，没有 `migrations.py`、`workflows/`、`agents/settlement_extractor/` 的修改。

S6（一周打开 3 天）要等命令装到作者机器上之后才记。M0 的代码验收不含这条日志。

---

## 7. 验证命令

```bash
ruff check src/ tests/
python -m pytest tests/db/test_plan_fact_cards.py tests/db/test_dushi_lingyi_plan_facts.py tests/plan_checks/test_plan_bible_runtime.py -q
python -m pytest tests/cli/test_workbench_commands.py -q
```

`tests/cli` 不在默认 pytest 收集里，所以第三条要单独跑。改动的若只是 CLI，不必为了 M0 去跑真实 LLM。

---

## 8. 风险

| 风险 | 处理 |
|------|------|
| 作者把故事线当成已发生的事 | 固定标题 + JSON 分键。测试断言大纲句子不在 Canon 段 |
| 作者把 pending 抄进正文当设定 | 标题「不是 Canon」；每行带 `approval_status=pending` |
| `get_db()` 在缺文件时把库建出来 | 先做路径存在性检查，测试锁住「调用后文件仍不存在」 |
| `today` 被当成启动器 | 文案固定；模块不导入工作流 |
| 夹具《末班铜牌》被改成题材检查器的金标准 | 它只提供已批准卡的往返样本。不新增召回用例，不改 `plan_checks/` 的规则 |
| 实现时顺手做 confirm | 评审拒绝任何写 SQL 的命令路径。写操作留在测试夹具 |
| M0 范围不够用，想把 check 拉进来 | 停。改 PRD 的 M0 边界并另审，不在实现 PR 里扩 |

都市灵异只作为这份夹具的题材标签。命令里不出现「若题材是都市灵异则……」的分支。

---

## 9. 以后的技术方案

M0 验收通过之前，不写 M1 的代码，也不在本文件追加 M1 的任务清单。

下一份技术文才决定的事（本文故意不定死）：

- dismiss 是删除 pending 行，还是新增 `rejected`
- 硬变更用旗标还是 `hardness` 列
- 抽取结果进提案队列时，结算库哪些表保持原样
- Variant 表和 `parent_canon_fingerprint` 的算法

那些属于 M1、M2、M3 各自的 `docs/tech-m*.md`。每份仍要 owner 书面接受之后才能改对应的代码。
