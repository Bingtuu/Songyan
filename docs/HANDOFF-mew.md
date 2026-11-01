# Handoff：当前下一步

owner：Bingtuu。包 tip **v0.5**（`0.5.0`）。「V1.0」是产品代际名，不是包版本。本文件不打 tag。

权威顺序见 [AGENTS.md](../AGENTS.md)：[PRD](prd-v1.md) → [M0 技术方案](tech-m0.md) → ADR-0001 → STATUS（事实）→ 本文件（当天）→ `tasks/`（有任务文档之后）。

## 下一刀

**等 Mew 审 M0 步 2 的 PR。** 本切片没有自行合并。任务是 [tasks/201.md](../tasks/201.md)。步 2 只把 Storyline 段改成读 `NarrativeRepository`，并加 `canon show --json`。`today` 和缺库退出码还没做。

步 1 已在 `main`：[#28](https://github.com/Bingtuu/Songyan/pull/28) squash 为 `1d8c0c0`，任务在 [tasks/done/200.md](../tasks/done/200.md)。`main` 上的故事线段仍是 `（空）`，直到步 2 合并。

不要做的事：

- 不再开 `settlement_review` 修复刀。`11c4c761` / #19 的 Ch1–3 fail 留着；`eaa6bef` / #20 的重跑已 PASS。
- 不重开 plan-first 阶段 C，不加题材专用检查器，不改 SettlementExtractor 的权威。
- 不把 Ch1–10 写成文学验收。文学质量归人。
- 正式 git tag 仍由维护者决定。
- 步 2 PR 未合并。不要开步 3，不要把故事线正文写成 `main` 已安装。

## 事实指针（短）

| 项 | 记录 |
|----|------|
| 产品规划 | [prd-v1.md](prd-v1.md)（文档已接受，#27 已进 main） |
| M0 步 1 | [#28](https://github.com/Bingtuu/Songyan/pull/28) 已进 `main`（`1d8c0c0`）。[tasks/done/200.md](../tasks/done/200.md) |
| M0 步 2 | [tasks/201.md](../tasks/201.md)（DOING，PR 未合并） |
| 当前任务 | [tasks/201.md](../tasks/201.md) |
| 架构方向 | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 工程现状 | [STATUS.md](STATUS.md) |
| 阶段 A–C | [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（CLOSED 短指针；全文在 archive，日常不要加载） |

**Ch1–3 发布冒烟：** `eaa6bef` PASS（`run-552b2c04`，scifi《轨道蜃景》）。Box（不入库）：`/workspace/songyan-release-smoke-out-rerun20/notes.md`、`smoke_result.json`。

**Ch1–10（2026-10-26）：流水线过，文学不过。** main `47954cb`。scifi《轨道蜃景》，`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；QG / settlement / summary / export 通过；exit 0。**DG-1 失败**（平均 revision 1.7；ContextEmergency 10/10，无 AutoHalt）。文学不及格：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧/EVA 复读、`ninety-two 秒`。只作 smoke / 回归证据。Box（不入库）：`/workspace/songyan-ch1-10-out/` 下 `notes.md`、`result.json`、`reports/report-run-33841231.md`、`exports/轨道蜃景-flat.md`、`quality-read.md`。

## 怎么报告

一刀结束用短记录：分支与 PR、改了哪些文件、测试结果、明确没做的事、下一刀只推荐一件。
