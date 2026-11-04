# Handoff：当前下一步

owner：Bingtuu。包 tip **v0.5**（`0.5.0`）。「V1.0」是产品代际名，不是包版本。本文件不打 tag。

权威顺序见 [AGENTS.md](../AGENTS.md)：[PRD](prd-v1.md) → [M0 技术方案](tech-m0.md) → [M1 技术方案](tech-m1.md)（**已接受**）→ ADR-0001 → STATUS（事实）→ 本文件（当天）→ `tasks/`（有任务文档之后）。

## 下一刀

**等 owner/parent 授权后再开 M1 步 5（`today` next / W0 e2e）。** 当前无 DOING 编码任务。不要自建 `tasks/20x` 步 5 文件，不要改 `src/` / `tests/`。

绑定摘要（全文以 tech-m1 为准）：无持久第四态 `accepted`；人写强制 `source=human`；步 1 五表 CHECK 必迁；`check` 正文 = `ChapterVersion.content`，属性侧值 = 注入 `AttributeExtract`；验收最小 kind = entity+attribute；rejected 后同 id 覆盖、无正文史；步 5 更新 `today` 的 `next`。

M0 步 1–4 已全部在 `main`：[#28](https://github.com/Bingtuu/Songyan/pull/28) → `1d8c0c0`；[#29](https://github.com/Bingtuu/Songyan/pull/29) → `8f03453`；[#30](https://github.com/Bingtuu/Songyan/pull/30) → `d5c2cc1`；[#31](https://github.com/Bingtuu/Songyan/pull/31) → `48fa354`。任务分别在 [tasks/done/200.md](../tasks/done/200.md)、[tasks/done/201.md](../tasks/done/201.md)、[tasks/done/202.md](../tasks/done/202.md)、[tasks/done/203.md](../tasks/done/203.md)。

M0 代码验收（步 1–4 + tech-m0 §6–7）在 `main` `80f4107`：**PASS**。归档说明：[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md)。S6 不在代码验收内。

M1 步 1–4 已在 `main`：[#35](https://github.com/Bingtuu/Songyan/pull/35) → `1995181`；[#36](https://github.com/Bingtuu/Songyan/pull/36) → `5a260a9`；[#38](https://github.com/Bingtuu/Songyan/pull/38) → `7c7ec43`；[#39](https://github.com/Bingtuu/Songyan/pull/39) → `d3f127c`。任务分别在 [tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md)、[tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md)、[tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md)、[tasks/done/208-check.md](../tasks/done/208-check.md)。

不要做的事：

- 不再开 `settlement_review` 修复刀。`11c4c761` / #19 的 Ch1–3 fail 留着；`eaa6bef` / #20 的重跑已 PASS。
- 不重开 plan-first 阶段 C，不加题材专用检查器，不改 SettlementExtractor 的权威。
- 不把 Ch1–10 写成文学验收。文学质量归人。
- 正式 git tag 仍由维护者决定。
- 不要在无 owner/parent 授权时开步 5；不要合成跨步大 PR；不要在无 Mew COMMENT 时自合。
- 不声称 V1.0 完成，不升包版本。

## 事实指针（短）

| 项 | 记录 |
|----|------|
| 产品规划 | [prd-v1.md](prd-v1.md)（文档已接受，#27 已进 main） |
| M0 步 1–4 | 已进 `main`（见上）；[tasks/done/200–203](../tasks/done/) |
| M0 验收 | **PASS** @ `80f4107`。[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md) |
| M1 技术方案 | [tech-m1.md](tech-m1.md) — **已接受**（Mew 拍板，2026-11-03 Asia/Shanghai） |
| M1 步 1 | 已合入 `1995181`（#35）；[tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md) |
| M1 步 2 | 已合入 `5a260a9`（#36）；[tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md) |
| M1 步 3 | 已合入 `7c7ec43`（#38）；[tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md) |
| M1 步 4 | 已合入 `d3f127c`（#39）；[tasks/done/208-check.md](../tasks/done/208-check.md) |
| 当前任务 | **无 DOING**。下一刀 = 步 5 today next / W0 e2e，**仅 owner/parent 授权后** |
| 架构方向 | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 工程现状 | [STATUS.md](STATUS.md) |
| 阶段 A–C | [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（CLOSED 短指针；全文在 archive，日常不要加载） |

**Ch1–3 发布冒烟：** `eaa6bef` PASS（`run-552b2c04`，scifi《轨道蜃景》）。Box（不入库）：`/workspace/songyan-release-smoke-out-rerun20/notes.md`、`smoke_result.json`。

**Ch1–10（2026-10-26）：流水线过，文学不过。** main `47954cb`。scifi《轨道蜃景》，`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；QG / settlement / summary / export 通过；exit 0。**DG-1 失败**（平均 revision 1.7；ContextEmergency 10/10，无 AutoHalt）。文学不及格：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧/EVA 复读、`ninety-two 秒`。只作 smoke / 回归证据。Box（不入库）：`/workspace/songyan-ch1-10-out/` 下 `notes.md`、`result.json`、`reports/report-run-33841231.md`、`exports/轨道蜃景-flat.md`、`quality-read.md`。

## 怎么报告

一刀结束用短记录：分支与 PR、改了哪些文件、测试结果、明确没做的事、下一刀只推荐一件。
