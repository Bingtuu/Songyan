# Task 144 DONE — 线索经济约束（MVP）

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **状态**: ✅ 完成（工程实现 + Layer 2 单测）；⚠️ Layer 3（Ch1-Ch20 真跑 (b)(c)）见"验证与遗留"
> **完成日期**: 2026-07-01
> **依赖**: Task 141（PlotThread 状态机）、Task 143（NarrativeGoalContext）
> **规划**: `docs/v6-plan.md` §3 阶段 0；任务书：`tasks/144-thread-economy-mvp.md`

---

## 交付概览

给 CreativeDirector 注入"本章应推进/收束的线索、非必要不开新线"约束，并让 `PlotThread` 状态在 settlement 后依据本章证据自动推进（`opened/advanced/resolved`），使线索开启-兑现可追踪、可计数。

| 交付物 | 文件 |
|--------|------|
| 线索约束注入 | 工艺卡 `prompts/cards/creative_director/1.0.6.yaml`（+ manifest）；`creative_director/__init__.py` `_render_prompt`/`generate_creative_brief` 增 `narrative_ctx`；`creative_director_node` 接线 |
| 状态跟随更新 | `src/songyan/workflows/_thread_economy.py` `update_plot_threads_after_settlement`（service 层）；`settlement_extractor_node` 后处理接线（非阻塞） |
| 状态可计数 | 复用 Task 141 `NarrativeRepository.count_threads_by_status`（为阶段 A Task 148 铺路） |
| 测试 | `tests/test_144_thread_economy.py`（9 用例：约束注入 3 + 状态机/计数/边界 6） |

## 线索约束注入

- **工艺卡 1.0.6** = 1.0.5 + 于"## 章节目标"后插入"## 线索经济约束（V6 叙事骨架）"段（`{{ thread_constraints }}`），新增一个必填字符串变量。1.0.5 未改动。
- **版本选择保证回退零差异**：`_render_prompt` 仅当 `narrative_ctx.has_skeleton=True` **且存在待推进/收束线索**时用 `version="1.0.6"`；否则显式 `version="1.0.5"`（与历史逐字节等价）。默认 manifest 版本仍为 1.0.5，避免隐式默认渲染缺变量。
- `thread_constraints` 文本含"应推进的线索 / 应收束的线索 / **非必要不开启新线索、不引入新的 critical 设定**"，复用 `NarrativeGoalContext.open_threads` / `threads_to_resolve`。
- 接线：`creative_director_node` 先 `load_narrative_goal_context` 再传入 `generate_creative_brief`；无骨架回退。

## PlotThread 状态跟随更新（正文进展驱动）

`update_plot_threads_after_settlement(project_id, chapter_number, version_id, settlement, narrative_repo=None) -> list[str]`：
- 取项目所有未收束线索（`planned/opened/advanced`）；无则直接返回空。
- **证据抽取**（仅用 settlement 已产出结构化输出，不新增 LLM）：`evidence` = 伏笔描述 + 新设定名/描述 + 角色新值 + planted/resolved hooks + open_threads；`resolved_evidence` = resolved_hooks + `operation=="resolve"` 的伏笔描述。
- **引用判定**：`thread_id` 或非空 `title` 出现在证据文本 → 该线索被本章推进。
- **状态推进规则**（可解释、可单测；2026-07-01 冒烟后加固）：
  - `planned → opened`（首次推进，回填 opened_chapter）
  - `opened → advanced`（继续推进；**禁止 `opened` 直接 `resolved`**，保证 opened→advanced→resolved 链）
  - `advanced → resolved`（有收束信号 **且** 已进入线索 `expected_resolve_arc` 对应弧的起始章窗口）否则保持 advanced
  - 收束窗口：`expected_resolve_arc` 对应弧未定义/未到达 → 不自动收束；`None` → 退化为仅靠 advanced + 收束信号
- 每次变更调用 Task 141 `advance_thread_status`，写 `last_status_chapter` + `last_status_version_id`（T1 可追溯）。
- **接线**：`settlement_extractor_node` 在 accept + settlement 成功后的后处理块调用（步骤 6），非阻塞——失败仅告警，不影响 settlement/summary。

## Agent 边界与规则遵守

- 状态更新集中在 service 层（`_thread_economy`）+ repository；Writer/CreativeDirector 不直接写 DB。
- 不新增 LLM 调用、不新增 Agent/Workflow 节点；不改 SettlementExtractor 证据校验规则；不做显式 resolve/作废出口（阶段 B/152）。
- 无运行时循环依赖：CreativeDirector 对 `NarrativeGoalContext` 仅在 `TYPE_CHECKING` 下引用。

## 验证与遗留

- `pytest tests/test_144_thread_economy.py -q` → **9 passed**。
- `ruff check src/ tests/` → **All checks passed**。
- 全量 `pytest tests/ -q` → **2065 passed, 2 skipped, 1 xfailed, 16 errors**（16 error 全为预存在的 `test_124` 缺脚本问题；相对 143 基线 +9 = 本任务 9 个新单测，无新增失败）。
  - 回归修复：初次全量跑出现 3 个 `test_phase1_graph.py::TestSettlementExtractorNode` 失败，根因是这些单测对着缺 `plot_threads` 表的历史 ambient DB 运行、step-6 抛 `sqlite3.OperationalError` 未被节点捕获。已将该后处理步骤的异常捕获扩展为 `(RuntimeError, OSError, ConnectionError, sqlite3.OperationalError)`（best-effort、不阻断 settlement）；修复后 3 个失败全部转绿。
- **⚠️ Layer 3（阶段 0 出口 (b)(c)）需带大纲长跑**：判据 (b)「≥1 条主线线索完成完整 `opened→advanced→resolved` T1 跃迁」与 (c)「T7 较 138k 基线降 ≥30%」都需要**带大纲项目跑到线索计划收束弧**（如 Ch11+）才能产出 resolve，且需 Stage A 的度量入库做 T7 对比。转入阶段 D / 后续长跑任务（157/158），届时用隔离副本 DB 直接查询跃迁链与 T7 对比。

## 冒烟测试（2026-07-01，真实 DeepSeek API）

用 `--outline-file` 相同代码路径建"灰塔/断刃"带大纲项目（隔离 DB `.tmp/v6_smoke.db`，主库未污染），`songyan run --chapters 1-3 --auto-confirm --skip-rag --gate-mode observe`：

- **结果**：3/3 章 accepted，`failed=[]`，~12.6 分钟，全流程无崩溃。
- **验证通过**：`chapter_goals.derived_from_arc` ch1/2/3 全 `=0`（Task 143 派生生效）；CreativeDirector 1.0.6 约束注入从 ch2 起触发无误；两条主线线索被真实 settlement 证据驱动推进（Task 144 闭环在真实文本上会 fire）。
- **暴露并修复的缺陷**：初版收束规则太松——主线线索"灰塔"/"断刃"在 **ch2 就被误判 resolved**（关键词"灰塔"/"断刃"频繁出现在局部章末钩子/伏笔里，仅凭子串命中即收束整条主线）。已按上文"加固版"规则修复：**advanced 优先 + `expected_resolve_arc` 收束弧窗口**。修复后单测新增 `test_no_premature_resolve_before_resolve_arc` / `test_resolve_arc_undefined_never_auto_resolves` / `test_opened_advances_not_resolves` 等覆盖（12 用例全过）。
- 临时产物：`.tmp/v6_smoke_*`（大纲/脚本/DB），复跑校验后可清理，不影响 138n/138k 校准库。

## 复审修复（2026-07-02，阶段 0/A 交付复审）

阶段 0+A 交付整体复审发现两处中危缺陷并修复（不改行为契约，仅收紧健壮性与原子性）：

- **#1 后处理异常捕获不完整（破"非阻塞"契约）** — `settlement_extractor_node` step-6 的 except 原为 `(RuntimeError, OSError, ConnectionError, sqlite3.OperationalError)`，但 `update_plot_threads_after_settlement` 会抛 `NarrativeError`/`InvalidThreadTransitionError`（`SongyanError` 子类，如非法迁移/线索不存在）与 `sqlite3.IntegrityError`（FK 冲突），这些均**不在捕获范围内**，一旦触发会中断 accept 后处理，违背"线索更新失败不影响 settlement/summary"契约。修复：`src/songyan/workflows/_nodes.py` 捕获扩展为 `(SongyanError, RuntimeError, OSError, ConnectionError, sqlite3.Error)`，并补 `SongyanError` import。
- **#3 一章引用多条线索时状态推进非原子** — 原 `update_plot_threads_after_settlement` 对每条待推进线索各自 `advance_thread_status`（各自开连接、各自 commit），若第 N 条中途抛异常，前 N-1 条已提交、留下**部分推进**的不一致状态。修复：`src/songyan/workflows/_thread_economy.py` 先在内存算出全部 `pending`（thread_id, new_status），再在**单个 `get_db()` 事务**内批量 `advance_thread_status(..., conn=conn)` 后统一 `commit()`——要么全成功、要么全回滚；每批新开连接也顺带规避 `advance_thread_status` 内 `row_factory=Row` 对复用连接的污染。
- 验证：`pytest tests/test_144_thread_economy.py`（38 项相关用例含 phase2/146 全过）、全量 `pytest tests/ -q` → **2099 passed, 2 skipped, 1 xfailed**（与修复前基线一致，无回归）；`ruff check` 改动文件全过。

## Out of Scope（未做）

- 自动重规划闭环（V7）；线索显式 resolve/作废出口（阶段 B/152）；Writer ContextPackage 注入骨架（超出 MVP 边界）。
