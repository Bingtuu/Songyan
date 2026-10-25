# Handoff：Mew 每日切片

owner：Bingtuu。目标与非目标以 [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 为准，架构方向以 [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) 为准。一次切片只做「下一刀」里的一件事。

## 先看哪里

| 要做什么 | 看 |
|----------|----|
| 今天做哪一件 | 本文件「下一刀」 |
| 怎样算 90 天证明了 | [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 阶段 A → B → C |
| 为什么倒过来写 canon | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 事实卡 schema（已合入的容器） | `src/songyan/models/plan_facts.py`；`src/songyan/db/plan_fact_repo.py`；`src/songyan/db/migrations.py` |
| 霞飞路批准卡、窄检查、只读门 | `src/songyan/plan_facts/xiafei_jiuan.json`；`src/songyan/plan_checks/`（`gate.py` 由 `rule_auditor_node` 调用）；[xiafei-plan-checks.md](xiafei-plan-checks.md) |
| 现有结算路径（先别改权威） | `src/songyan/agents/settlement_extractor/`。它仍写原结算库，不写 plan canon |
| Phase A 已完成 | B7 #5、B5 #6、B18 #8。不要再开这三刀 |

证据数字只用来自 2026-10 的 owner 笔记，外加这一刀在 box 上测得的召回：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、成本记录、霞飞路重跑 5/5（[experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)）。不要在切片里再补一套新的评测数字。

## 下一刀

**Phase A 已完成。** B7 #5、B5 #6、B18 #8 已在 main。事实卡 schema、霞飞路批准卡、三项窄检查、写章审查上的只读门也已在 main。规模写作仍然冻结。

**重跑这一刀（knife4）已测量：活路径召回 5/5，达到 ≥4/5。** 正文来自 box 上的项目 `030b687372374aa491e0c294e6d62969`，不是云端虚拟机。T1、T2 发生，必须提及拦住了；T4、T6 未发生（门仍标缺「往外拉」「九一八」）；T5 未发生，所以记召回。记录在 [experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)。

`rule_auditor_node` 仍只读已批准卡，结果仍在 `_plan_fact_gate`，不改质量门路由。SettlementExtractor 仍写原结算库。`run_chapter_pipeline` 仍不填 `_plan_attribute_extracts` / `_plan_claim_anchors`。T5 这次没有发生；归属漂移若再发生，活路径标不出。人工时长和成本仍没有记录，阶段 B 还没过完。不开始阶段 C。

**下一刀还没定，两件里只做一件：** 把类型化摘录和主张锚接到审查 state，让 T5 发生时能被拦住；或者本 PR 合入之后再开下一片。不写《规则年代》，不加题材规则，不把抽取吸进 canon。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
