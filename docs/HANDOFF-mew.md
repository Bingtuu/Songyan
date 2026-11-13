# Handoff：当前下一步

owner：Bingtuu。包 tip **v0.5**（`0.5.0`）。「V1.0」是产品代际名，不是包版本。本文件不打 tag。

权威顺序见 [AGENTS.md](../AGENTS.md)：[PRD](prd-v1.md) → [M0 技术方案](tech-m0.md) → [M1 技术方案](tech-m1.md)（**已接受**；§6–7 **PASS**）→ [M2 技术方案](tech-m2.md)（**已接受**；§6–7 **PASS** @ `f1c3093`）→ [M3 技术方案](tech-m3.md)（**已接受**；t104s937；B1–B7 原样；§6–7 **PASS** @ `594144b`）→ [M4 技术方案](tech-m4.md)（**已接受**；2026-11-08；B1–B12 原样；§6–7 **PASS** @ `e5a33bd`）→ ADR-0001 → STATUS（事实）→ [task 244](../tasks/done/244-修复抽卡死锁与圣经空渲染.md)（2026-11-11 冒烟 P1 修复，DONE 归档；代码 @ `120012c`）→ 本文件（当天）→ `tasks/`（有任务文档之后）。

## 下一刀

**task 244 已 DONE 归档（2026-11-11）**：真实模型冒烟发现 5/6 两个 P1 修复，代码 @ `120012c`，切片 5 真实模型复验 PASS（`.tmp/smoke-244-verify-20261111/`：pick→accept 后 continue exit 0；圣经 text_len 0→1664；抽卡两槽真实正文 1602/2075 字；canon confirm 后 stale_vs_canon=1；费用 ¥0.4823 / 24 次调用）。归档：[tasks/done/244](../tasks/done/244-修复抽卡死锁与圣经空渲染.md)。

**task 245 已 DONE 归档（2026-11-12）**：变体拒写质量门（owner 拍板 P1–P3）——判定纯函数 + 同槽重试 1 次 + `quality_flag` 打标 + 全败 exit 2；代码 @ `8c26105`；真实模型复验 ¥0.3491（`.tmp/smoke-245-verify-20261112/`）。归档：[tasks/done/245](../tasks/done/245-变体拒写判失败与重试策略.md)。

**task 246 已 DONE 归档（2026-11-12）**：db-maintenance 锁表根因 = `get_db()` 的 `PRAGMA quick_check` 未消费结果悬挂持锁（4 轮实验链实锤：插桩→sync 探针→最小复现→单变量二分）；修复后真实 run 收尾 0 告警、WAL 截断 0 字节（¥0.4203），全量 3623 passed。归档：[tasks/done/246](../tasks/done/246-修复run收尾db-maintenance锁表失败.md)。

**下一刀（均需 owner 侧动作，助手默认待命）**：tech-m4 §9「以后」清单（`chapter status` / `review --deep` / 导入后再续写验收）——新功能授权项，未建任务文件，需 owner 新授权立项

M0 步 1–4 已全部在 `main`：[#28](https://github.com/Bingtuu/Songyan/pull/28) → `1d8c0c0`；[#29](https://github.com/Bingtuu/Songyan/pull/29) → `8f03453`；[#30](https://github.com/Bingtuu/Songyan/pull/30) → `d5c2cc1`；[#31](https://github.com/Bingtuu/Songyan/pull/31) → `48fa354`。任务分别在 [tasks/done/200.md](../tasks/done/200.md)、[tasks/done/201.md](../tasks/done/201.md)、[tasks/done/202.md](../tasks/done/202.md)、[tasks/done/203.md](../tasks/done/203.md)。

M0 代码验收（步 1–4 + tech-m0 §6–7）在 `main` `80f4107`：**PASS**。归档说明：[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md)。S6 不在代码验收内。

M1 步 1–5 已在 `main`：[#35](https://github.com/Bingtuu/Songyan/pull/35) → `1995181`；[#36](https://github.com/Bingtuu/Songyan/pull/36) → `5a260a9`；[#38](https://github.com/Bingtuu/Songyan/pull/38) → `7c7ec43`；[#39](https://github.com/Bingtuu/Songyan/pull/39) → `d3f127c`；[#41](https://github.com/Bingtuu/Songyan/pull/41) → `69d7ece`。任务分别在 [tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md)、[tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md)、[tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md)、[tasks/done/208-check.md](../tasks/done/208-check.md)、[tasks/done/209-w0-today-e2e.md](../tasks/done/209-w0-today-e2e.md)。

M1 代码验收（步 1–5 + tech-m1 §6–7）在 `main` `69d7ece`：**PASS**。归档说明：[tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md)。S1/S2 产品周期日志不在代码验收内。

不要做的事：

- 不再开 `settlement_review` 修复刀。`11c4c761` / #19 的 Ch1–3 fail 留着；`eaa6bef` / #20 的重跑已 PASS。
- 不重开 plan-first 阶段 C，不加题材专用检查器，不改 SettlementExtractor 的权威。
- 不把 Ch1–10 写成文学验收。文学质量归人。
- 正式 git tag 仍由维护者决定。
- **M0–M4 编码范围全部闭环**：不扩 M3（continue / review 已由 M4 交付）、不扩 M4（步 1–5 + §6–7 PASS @ `e5a33bd`，task 243）；结算表仍保留为 untrusted 对照，不升格 Canon。tech-m4 §9「以后」事项需 owner 新授权立项。
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
| M2 步 3 | 已合入 `2ac1093`（#48）；[tasks/done/214-m2-step3-content-stale-hard.md](../tasks/done/214-m2-step3-content-stale-hard.md) |
| M2 步 4 | 已合入 `5a6e923`（#50）；[tasks/done/215-m2-step4-check-stale-report.md](../tasks/done/215-m2-step4-check-stale-report.md) |
| M2 步 5 | 已合入 `2fa8209`（#52）；[tasks/done/216-m2-step5-extract-pending.md](../tasks/done/216-m2-step5-extract-pending.md) |
| M2 步 6 | 已合入 `f1c3093`（#53）；[tasks/done/217-m2-step6-docs-copy.md](../tasks/done/217-m2-step6-docs-copy.md) |
| M2 验收 | **PASS** @ 证据 tip `f1c3093`。[tasks/done/218-m2-acceptance.md](../tasks/done/218-m2-acceptance.md) |
| M3 技术方案 | [tech-m3.md](tech-m3.md) — **已接受**（2026-11-06；t104s937；B1–B7 原样）；草稿任务 [tasks/done/219-tech-m3草稿.md](../tasks/done/219-tech-m3草稿.md) |
| M3 步 1 | 已合入 `b9bbf98`（#56）；[tasks/done/220-m3-step1-variants-table.md](../tasks/done/220-m3-step1-variants-table.md) |
| M3 步 2 | 已合入 `135fcfb`（#57）；[tasks/done/221-m3-step2-variant-generate.md](../tasks/done/221-m3-step2-variant-generate.md) |
| M3 步 3 | 已合入 `0b47410`（#58）；[tasks/done/222-m3-step3-variant-list-diff.md](../tasks/done/222-m3-step3-variant-list-diff.md) |
| M3 步 4 | 已合入 `c38ee31`（#59）；[tasks/done/223-m3-step4-variant-pick-abandon.md](../tasks/done/223-m3-step4-variant-pick-abandon.md) |
| M3 步 5 | 已合入 `1b0e323`（#60）；[tasks/done/224-m3-step5-stale-cost.md](../tasks/done/224-m3-step5-stale-cost.md) |
| M3 §6–7 验收 | **PASS** @ `594144b`（task 234）；步 6 = task 233 |
| M4 技术方案 | [tech-m4.md](tech-m4.md) — **已接受**（2026-11-08；owner 拍板「按 B1–B12 开 M4 编码」；B1–B12 原样）；调研底稿 [docs/236-m4-preresearch.md](236-m4-preresearch.md) |
| M4 步 1 | 已提交 `c55a714`（章进度视图 + `status`）；[tasks/done/238-m4-step1-progress-status.md](../tasks/done/238-m4-step1-progress-status.md) |
| M4 步 2 | 已提交 `f205f8a`（`chapter accept`）；[tasks/done/239-m4-step2-chapter-accept.md](../tasks/done/239-m4-step2-chapter-accept.md) |
| M4 步 3 | 已提交 `23bd3f3`（`chapter continue`）；[tasks/done/240-m4-step3-chapter-continue.md](../tasks/done/240-m4-step3-chapter-continue.md) |
| M4 步 4 | 已提交 `b857e8b`（`review` 只读共审）；[tasks/done/241-m4-step4-review.md](../tasks/done/241-m4-step4-review.md) |
| M4 步 5 + §6–7 验收 | 步 5 已提交 `e5a33bd`（W2 连走集成测试 + `today` M4 文案）；**§6–7 PASS @ `e5a33bd`**（[tasks/done/242-m4-step5-closure.md](../tasks/done/242-m4-step5-closure.md) · [tasks/done/243-m4-code-acceptance.md](../tasks/done/243-m4-code-acceptance.md)） |
| 当前任务 | **task 247 DOING**（tech-m4 §9 后续三项调研与技术方案，owner 已授权立项；预拍板：一案三步顺序、--deep 交互确认+--yes、status 中薄面）。245（@`8c26105`）/ 246（@`b1e1c01`）均 DONE 归档（2026-11-12） |
| 架构方向 | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 工程现状 | [STATUS.md](STATUS.md) |
| 阶段 A–C | [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（CLOSED 短指针；全文在 archive，日常不要加载） |

**Ch1–3 发布冒烟：** `eaa6bef` PASS（`run-552b2c04`，scifi《轨道蜃景》）。Box（不入库）：`/workspace/songyan-release-smoke-out-rerun20/notes.md`、`smoke_result.json`。

**Ch1–10（2026-10-26）：流水线过，文学不过。** main `47954cb`。scifi《轨道蜃景》，`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；QG / settlement / summary / export 通过；exit 0。**DG-1 失败**（平均 revision 1.7；ContextEmergency 10/10，无 AutoHalt）。文学不及格：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧/EVA 复读、`ninety-two 秒`。只作 smoke / 回归证据。Box（不入库）：`/workspace/songyan-ch1-10-out/` 下 `notes.md`、`result.json`、`reports/report-run-33841231.md`、`exports/轨道蜃景-flat.md`、`quality-read.md`。

## 怎么报告

一刀结束用短记录：分支与 PR、改了哪些文件、测试结果、明确没做的事、下一刀只推荐一件。
