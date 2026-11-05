# Handoff：当前下一步

owner：Bingtuu。包 tip **v0.5**（`0.5.0`）。「V1.0」是产品代际名，不是包版本。本文件不打 tag。

权威顺序见 [AGENTS.md](../AGENTS.md)：[PRD](prd-v1.md) → [M0 技术方案](tech-m0.md) → [M1 技术方案](tech-m1.md)（**已接受**；§6–7 **PASS**）→ [M2 技术方案](tech-m2.md)（**已接受**）→ ADR-0001 → STATUS（事实）→ 本文件（当天）→ `tasks/`（有任务文档之后）。

## 下一刀

**M2 步 3 编码进行中（W4 content_stale + confirm `--hard` / `--mark-stale`）：** [#48](https://github.com/Bingtuu/Songyan/pull/48)；分支 `m2-step3-content-stale-hard`；任务 [tasks/214-m2-step3-content-stale-hard.md](../tasks/214-m2-step3-content-stale-hard.md)。产出：窄迁移 `chapter_heads.content_stale`；硬/显式标脏按闭区间覆盖章。步 2 已在 `main`（[#46](https://github.com/Bingtuu/Songyan/pull/46) → `8afb7be`；[tasks/done/213-m2-step2-confirm-settle.md](../tasks/done/213-m2-step2-confirm-settle.md)）。步 1 已在 `main`（[#44](https://github.com/Bingtuu/Songyan/pull/44) → `8f7bc77`）。本步不做 check stale 报告 / extract source / SettlementExtractor 权威漂移；包仍 `0.5.0`。等 Mew COMMENT，勿自合。

M0 步 1–4 已全部在 `main`：[#28](https://github.com/Bingtuu/Songyan/pull/28) → `1d8c0c0`；[#29](https://github.com/Bingtuu/Songyan/pull/29) → `8f03453`；[#30](https://github.com/Bingtuu/Songyan/pull/30) → `d5c2cc1`；[#31](https://github.com/Bingtuu/Songyan/pull/31) → `48fa354`。任务分别在 [tasks/done/200.md](../tasks/done/200.md)、[tasks/done/201.md](../tasks/done/201.md)、[tasks/done/202.md](../tasks/done/202.md)、[tasks/done/203.md](../tasks/done/203.md)。

M0 代码验收（步 1–4 + tech-m0 §6–7）在 `main` `80f4107`：**PASS**。归档说明：[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md)。S6 不在代码验收内。

M1 步 1–5 已在 `main`：[#35](https://github.com/Bingtuu/Songyan/pull/35) → `1995181`；[#36](https://github.com/Bingtuu/Songyan/pull/36) → `5a260a9`；[#38](https://github.com/Bingtuu/Songyan/pull/38) → `7c7ec43`；[#39](https://github.com/Bingtuu/Songyan/pull/39) → `d3f127c`；[#41](https://github.com/Bingtuu/Songyan/pull/41) → `69d7ece`。任务分别在 [tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md)、[tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md)、[tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md)、[tasks/done/208-check.md](../tasks/done/208-check.md)、[tasks/done/209-w0-today-e2e.md](../tasks/done/209-w0-today-e2e.md)。

M1 代码验收（步 1–5 + tech-m1 §6–7）在 `main` `69d7ece`：**PASS**。归档说明：[tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md)。S1/S2 产品周期日志不在代码验收内。

不要做的事：

- 不再开 `settlement_review` 修复刀。`11c4c761` / #19 的 Ch1–3 fail 留着；`eaa6bef` / #20 的重跑已 PASS。
- 不重开 plan-first 阶段 C，不加题材专用检查器，不改 SettlementExtractor 的权威。
- 不把 Ch1–10 写成文学验收。文学质量归人。
- 正式 git tag 仍由维护者决定。
- **tech-m2 已接受。** 只做已授权的下一刀（当前 = 步 3 W4 `content_stale`）；不做未授权的步 4+、不改 SettlementExtractor、不加 extract / variant / continue。
- 不声称 V1.0 完成，不升包版本。

## 事实指针（短）

| 项 | 记录 |
|----|------|
| 产品规划 | [prd-v1.md](prd-v1.md)（文档已接受，#27 已进 main） |
| M0 步 1–4 | 已进 `main`（见上）；[tasks/done/200–203](../tasks/done/) |
| M0 验收 | **PASS** @ `80f4107`。[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md) |
| M1 技术方案 | [tech-m1.md](tech-m1.md) — **已接受**（Mew 拍板，2026-11-03 Asia/Shanghai）；§6–7 **PASS** @ `69d7ece` |
| M1 步 1–5 | 已合入（见上）；[tasks/done/205–209](../tasks/done/) |
| M1 验收 | **PASS** @ `69d7ece`。[tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md) |
| M2 技术方案 | [tech-m2.md](tech-m2.md) — **已接受**（2026-11-04；t93s804；B1–B6 原样；[#43](https://github.com/Bingtuu/Songyan/pull/43) → `a95824a`） |
| M2 步 1 | 已合入 `8f7bc77`（#44）；[tasks/done/212-m2-step1-w5-readonly.md](../tasks/done/212-m2-step1-w5-readonly.md) |
| M2 步 2 | 已合入 `8afb7be`（#46）；[tasks/done/213-m2-step2-confirm-settle.md](../tasks/done/213-m2-step2-confirm-settle.md) |
| 当前任务 | DOING：M2 步 3（W4 content_stale）；[tasks/214-m2-step3-content-stale-hard.md](../tasks/214-m2-step3-content-stale-hard.md)；PR [#48](https://github.com/Bingtuu/Songyan/pull/48) |
| 架构方向 | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 工程现状 | [STATUS.md](STATUS.md) |
| 阶段 A–C | [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（CLOSED 短指针；全文在 archive，日常不要加载） |

**Ch1–3 发布冒烟：** `eaa6bef` PASS（`run-552b2c04`，scifi《轨道蜃景》）。Box（不入库）：`/workspace/songyan-release-smoke-out-rerun20/notes.md`、`smoke_result.json`。

**Ch1–10（2026-10-26）：流水线过，文学不过。** main `47954cb`。scifi《轨道蜃景》，`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；QG / settlement / summary / export 通过；exit 0。**DG-1 失败**（平均 revision 1.7；ContextEmergency 10/10，无 AutoHalt）。文学不及格：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧/EVA 复读、`ninety-two 秒`。只作 smoke / 回归证据。Box（不入库）：`/workspace/songyan-ch1-10-out/` 下 `notes.md`、`result.json`、`reports/report-run-33841231.md`、`exports/轨道蜃景-flat.md`、`quality-read.md`。

## 怎么报告

一刀结束用短记录：分支与 PR、改了哪些文件、测试结果、明确没做的事、下一刀只推荐一件。
