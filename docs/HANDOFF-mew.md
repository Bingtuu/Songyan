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

证据数字只用来自 2026-10 的 owner 笔记：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、成本记录。不要在切片里补一批新的评测数字。

## 下一刀

**Phase A 已完成。** B7 #5、B5 #6、B18 #8 已在 main。事实卡 schema、霞飞路批准卡、三项窄检查、写章审查上的只读门也已在 main。规模写作仍然冻结。

**重跑这一刀没有召回数字。** 执行环境没有 `LLM_API_KEY`，也没有 `.env`，生产模型调不到。没有新的 ch1–3。五类都是未计分，`recalled` 为空。这不是 0/5。记录在 [experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)。`scripts/rerun_xiafei_plan_gate.py` 在没有密钥时写这份记分板并退出；有密钥时用 `tpl/xiafei` 建项目，把批准卡改记到该项目 id 上，再 `songyan run`。

`rule_auditor_node` 仍只读已批准卡，结果仍在 `_plan_fact_gate`，不改质量门路由。SettlementExtractor 仍写原结算库。核实过的缺口：`run_chapter_pipeline` 不填 `_plan_attribute_extracts` / `_plan_claim_anchors`。必须提及会跑；类型化比较为空；没有锚时主张对不上原文就是未提及，这个缺省值不算矛盾，也不算 T2 的拦截。T5 归属漂移因此在活路径上标不出。计分脚本 `scripts/score_xiafei_roadmap_recall.py` 要求人读正文后填写发生与否，不用 v4 短语缺席代替「未发生」。

**下一刀只做一件：** 在有 `LLM_API_KEY` 的环境执行 `scripts/rerun_xiafei_plan_gate.py`，再用计分脚本给出五类召回（目标 ≥4/5）。不写《规则年代》，不加题材规则，不把抽取吸进 canon。理由：卡、门和计分规则已经在，缺的是一次真实写章。人工时长和成本仍不放进这一刀。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
