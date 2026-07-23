# Task 155: 失败隔离策略

> **Phase**: V6 阶段 C（工程加固）
> **优先级**: P1（无人值守长跑不因单章硬失败白跑整批；产出可定点重跑的失败清单）
> **依赖**: 阶段 0/A/B 已落地（不改治理）；与 Task 153（resume）/154（限流预算）在编排层协同
> **预计工作量**: 中（拆 155a 隔离-继续循环语义 + 155b 失败清单汇总与上下文回退）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 C

---

## Goal

把多章 run 的默认失败语义从"首章硬失败即 `abort` 终止整批"改为"**隔离单章失败、继续后续章、run 结束汇总失败清单**"，让一条 30h 长跑不因中段某一章的偶发失败而整批白跑；同时保证隔离**不弱化质量 AutoHalt**（质量持续退化仍应硬停），并给出可供定点重跑的失败章清单。

## Context

设计核实（2026-07-02，创建前对主干代码核对）：

- **`on_failure` 现状**：`run_project_pipeline(..., on_failure: str = "abort")`（`src/songyan/workflows/phase2_graph.py:301`），仅接受 `"abort" | "retry"`（docstring `:313`），**默认 `"abort"`**。CLI `songyan run`（`cli/main.py:435`）**根本没暴露 `on_failure`**，调用 pipeline 时不传（`main.py:471-479`），所以线上始终走 `abort`。
- **失败分支现状（关键：`retry` 也 break）**：主循环失败分支 `phase2_graph.py:469-500`：`failed.append(chapter_number)`（`:470`）→ `_persist_run_progress(...)`（`:477`）→ `_check_auto_halt_window(...)`（`:484`）→ `if on_failure == "abort": break`（`:495-496`）→ **紧接着还有一条无条件 `break`（`:500`）**。即 `retry` 已在 `_run_single_chapter` 内做过（`max_attempts = 2 if on_failure == "retry"`，`phase2_graph.py` 约 L607，重跑用新 `thread_id`），但返回失败后外层**无论哪种策略都 break**。**当前不存在任何"继续"路径**。
- **失败清单已有数据、但 CLI 只报数量**：`ProjectRunResult`（`models/project_run.py:27-37`）有 `chapters_failed` / `final_status`（`completed | partial | failed`，`:36`）；`final_status = "completed" if not failed else ("partial" if completed else "failed")`（`phase2_graph.py:534`）。持久化侧 `project_runs.failed_chapters`（`schema.sql:360`）。但 CLI `run` 只 `click.echo(f"失败: {len(result.chapters_failed)} 章")`（`main.py:483-484`）——**只报数量、不报章号**。`songyan report` 侧有逐章失败列表（`evals/streaming_report.py:248`）。
- **AutoHalt 独立于 `on_failure`（务必不弱化）**：`AutoHaltException`（`exceptions.py:53`）由 `_check_auto_halt_window`（`phase2_graph.py:207-286`）在 3 连续质量门失败/health_low streak/降级 ContextEmergency streak 时抛出，是**贯穿整个 pipeline 的硬停异常**；enforce 单章门禁也在 `:511` 硬停。**`_check_auto_halt_window` 在失败路径（`:484`）和每次成功后（`:520`）都被调用**，且在 `on_failure` 分支之前。→ 改为"隔离继续"后，**必须保留 `:484` 与 `:520` 两处调用**，AutoHalt 仍能硬停；隔离只影响"单章非质量性失败要不要终止整批"。
- **失败章对后续章上下文的影响（结构安全，但摘要断链）**：单章 `previous_summary` 来自 `_get_previous_summary(project_id, chapter_number)`（`phase2_graph.py:39-57`，读 `summaries` 表第 `chapter_number-1` 行）。失败章**不产出 accepted head、不产出 summary 行**，`accumulated_summary_parts` 仅在成功时追加（`:451-455`）。故失败章后继续到下一章：**不会崩**（查不到就返回空串），但下一章拿到的 `previous_summary` 为空——continuity 与失败章断链。
- **无任何"隔离继续"行为**：如上，`abort` 与 `retry` 都 break（`:495-500`），无 `skip`/`continue`/`isolate` 取值。本 Task 是净新增语义。

**为什么是"隔离继续"而非维持 abort**：阶段 D 长跑（Ch100/Ch150）中，单章偶发失败（LLM 抖动、settlement 边界）不应让前 N 章努力白费。但"继续"必须配套两个安全阀：(a) 质量 AutoHalt 不被削弱（系统性退化仍硬停）；(b) 失败章的上下文断链要有明确回退，避免"带病继续"污染后续所有章。

## Cross-Task Coordination（阶段 C 统一口径）

- **默认值变更口径**：`on_failure` 取值扩为 `"abort" | "retry" | "isolate"`。**默认切换为 `"isolate"`**（阶段 C 出口要求"单章硬失败不终止整批"）。CLI `songyan run` 新增 `--on-failure` 选项（`main.py:419-434` 加 option、`:435` 加参、`:471` 透传），默认 `isolate`；保留 `abort`/`retry` 供需要严格模式的场景显式选择。
- **与 AutoHalt 的边界（红线）**：隔离只处理**单章级失败**（`chapter_result["success"] is False`）。**质量 AutoHalt（`_check_auto_halt_window` 于 `:484`/`:520`）与 enforce 单章门禁（`:511`）一律保留、优先级更高**——即便 `on_failure="isolate"`，一旦 AutoHalt/门禁触发，仍硬停整批。DONE 需单测证明"隔离不吞 AutoHalt"。
- **与 153（resume）的分工**：155 让本次 run 内单章失败被隔离并继续；153 让崩溃/kill 后能续跑。叠加语义：隔离模式下 `failed_chapters` 落库，**下次 `--resume` 时这些失败章不在 accepted 集合、会被重跑**（153 的 resume 点以 accepted head 为准，失败章天然是"未完成"）。
- **与 154（限流）的分工**：偶发 429 优先由 154 在调用层退避吸收；退避耗尽才冒泡成章节失败，再由 155 隔离。预算熔断（154）是 run 级硬停、**不走隔离**（预算耗尽应停机而非继续烧）。

### 失败章上下文回退口径（权威定义）

隔离模式下，失败章 N 之后继续到 N+1 时，`previous_summary` 的取法：

1. 首选：回退到**最近一个成功章**的 summary（不是恒定用 N-1）。即维护"最近成功摘要"游标，失败章不推进该游标，N+1 用最近成功章的 `plot_summary`。
2. 若前面无任何成功章（如首章即失败），`previous_summary = ""`（与现状空串行为一致，不崩）。
3. 不为失败章伪造 summary/head，保持"失败即无产出"的事实源纯净（与 SQLite 唯一事实源精神一致）。

## In Scope（必须完成）

### 155a — 隔离-继续循环语义
- [ ] `on_failure` 增加 `"isolate"` 取值并**设为默认**；`run_project_pipeline` 签名 docstring 同步（`phase2_graph.py:301`/`:313`）。
- [ ] 改写失败分支（`phase2_graph.py:469-500`）：保留 `failed.append` / `_persist_run_progress` / `_check_auto_halt_window(:484)`；把结尾无条件 `break`（`:500`）改为按策略分派——`abort`→`break`；`retry`→维持现状（单章内已重试，仍失败则按选择 `abort` 或 `isolate` 语义，DONE 明确）；`isolate`→`continue`（记录失败、继续下一章）。
- [ ] **不弱化 AutoHalt**：`isolate` 分支仍先经 `_check_auto_halt_window`；AutoHalt/enforce 门禁（`:511`）触发时无视 `isolate` 硬停。
- [ ] CLI `songyan run` 暴露 `--on-failure`（默认 `isolate`），透传到 pipeline。

### 155b — 失败清单汇总 + 上下文回退
- [ ] 失败章上下文按 **Cross-Task Coordination「失败章上下文回退口径」** 处理：维护"最近成功摘要"游标，失败章不推进游标；N+1 用最近成功章 summary（无则空串）。
- [ ] run 结束产出**可定点重跑的失败清单**：CLI `run` 输出从"失败 N 章"升级为列出**失败章号**（复用 `result.chapters_failed`）；`final_status` 语义（`partial`）不变（`phase2_graph.py:534`）。
- [ ] 失败清单同时落库（`project_runs.failed_chapters` 已有）并在 `songyan report` 可读（`streaming_report.py:248` 已有逐章失败，确认 isolate 模式下正确填充）。
- [ ] 遵守边界：只改 run 编排 + CLI 输出；不改单章 graph、治理（149-152）、门禁与 AutoHalt 判据；不新增 Agent/LLM。

## Out of Scope（明确不做）

- 不改质量 AutoHalt / enforce 门禁的触发条件或阈值（本 Task 只保证隔离不吞它们）。
- 不做失败章的自动重试升级（单章重试仍是 `retry` 策略的职责；本 Task 不改 `_run_single_chapter` 的 `max_attempts`）。
- 不做 run 级断点续跑（Task 153）与 LLM 限流/预算（Task 154）。
- 不为失败章伪造 head/summary 占位（保持事实源纯净）。
- 不引入"失败章降级接受"路径——失败就是失败，进 `failed` 清单，不与 `degraded_accept`（质量降级但仍 accept）混淆。

## 接口契约

```python
# workflows/phase2_graph.py
async def run_project_pipeline(
    project_id: str,
    chapter_range: tuple[int, int],
    mode_id: str = "webnovel",
    *,
    auto_confirm: bool = False,
    max_revision_rounds: int = 2,
    on_failure: str = "isolate",   # 变更：默认 isolate（原 "abort"）；取值 abort|retry|isolate
    continuity_health_threshold: float = 7.0,
    gate_config: GateConfig | None = None,
) -> ProjectRunResult:
    """isolate: 单章失败记入 chapters_failed 并继续；AutoHalt/enforce 门禁仍硬停。"""

# cli/main.py — run 命令
@click.option("--on-failure", default="isolate",
              type=click.Choice(["abort", "retry", "isolate"]),
              help="单章失败策略：isolate 隔离并继续（默认），abort 终止整批，retry 重试一次")
```

（最终签名以实现为准；核心：新增 isolate 默认语义 + 失败章号清单输出 + 最近成功摘要回退，且 AutoHalt 不被削弱。）

## 测试要求

### Layer 2: 模块测试（Mock LLM / 构造章节失败）
- [ ] **isolate 继续**：构造 Ch2 失败、Ch1/Ch3 成功，`on_failure="isolate"` → run 跑完 Ch1-Ch3，`chapters_completed=[1,3]`、`chapters_failed=[2]`、`final_status="partial"`。
- [ ] **abort 兼容**：`on_failure="abort"` 仍在 Ch2 失败处 break（现状行为不变）。
- [ ] **AutoHalt 不被吞**：构造连续质量门失败触发 AutoHalt，即便 `on_failure="isolate"` 仍抛 `AutoHaltException` 硬停、run `status="paused"`（断言 `_check_auto_halt_window` 仍生效）。
- [ ] **上下文回退**：Ch2 失败后 Ch3 的 `previous_summary` = Ch1（最近成功章）的 summary，而非空串；首章失败时后继为空串不崩。
- [ ] **失败清单输出**：CLI `run` 输出含失败章号（非仅数量）；`project_runs.failed_chapters` 落库正确。
- [ ] **游标不被失败章推进**：多失败章连续（Ch2/Ch3 失败、Ch1/Ch4 成功）时，Ch4 的 `previous_summary` 仍为 Ch1。

### Layer 3: 小窗口注入实跑（阶段 C 出口佐证，可用隔离副本 DB）
- [ ] Ch1-ChN 小窗口注入一个中段单章硬失败，`on_failure="isolate"` 跑完全程：失败章被隔离、后续章继续、run 结束 `partial` 且失败清单可定点重跑；对比 `abort` 模式会在失败处终止。
- [ ] 证据入 `docs/reports/`（注入点、隔离结果、失败清单、后续章 previous_summary 回退验证）。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_155_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] `on_failure` 默认 `isolate`，单章硬失败不终止整批；`abort`/`retry` 仍可显式选择；CLI 暴露 `--on-failure`。
- [ ] AutoHalt / enforce 门禁在 isolate 下仍硬停（单测证明"隔离不吞熔断"）。
- [ ] 失败章后续章上下文按"最近成功摘要"回退；run 结束输出**失败章号清单**可供定点重跑。
- [ ] Layer 3 证明注入单章失败被隔离、run 续完为 partial（证据入 `docs/reports/`）。
- [ ] 不违反不可违背规则：只改 run 编排/CLI；不改治理、门禁、AutoHalt 判据；不伪造失败章产出；不新增 Agent/LLM。
- [ ] 生成 `archive/v6/tasks/155-failure-isolation-DONE.md`，含 isolate 语义、上下文回退口径、AutoHalt 不弱化证明、失败清单格式、Layer 3 证据。
- [ ] 更新 `tasks/V6-README.md`（155 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 C（Task 155 行 + 阶段 C 出口）
- 现有代码：`workflows/phase2_graph.py`（`on_failure` `:301`/失败分支 `:469-500`/`_check_auto_halt_window` `:484`&`:520`/enforce 门禁 `:511`/`final_status` `:534`/`_get_previous_summary` `:39`）、`cli/main.py:435`（`run` 命令与输出 `:481-485`）、`models/project_run.py`（`ProjectRunResult.chapters_failed`/`final_status`）、`exceptions.py:53`（`AutoHaltException`）、`evals/streaming_report.py:248`（逐章失败报告）
