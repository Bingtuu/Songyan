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

**Phase A 已完成。** B7 #5、B5 #6、B18 #8 已在 main。事实卡 schema、霞飞路批准卡、三项窄检查也已在 main。规模写作仍然冻结。

**本刀是只读 plan 门，并已接到写章审查路径。** `rule_auditor_node` 在正文版本已经存在之后调用 `run_plan_fact_gate`。门只读当前项目 `approval_status=approved` 的线索、事件和属性，然后调用必须提及、主张核验、类型化属性比较。主张核验默认用确定性锚点（`AnchoredClaimJudge`），不调用模型。类型化比较只用调用方交给门的结构化摘录（审查 state 上的 `_plan_attribute_extracts`）；主张锚在 `_plan_claim_anchors`。门不从正文再抽，也不把摘录写进 plan canon。结果记在 `_plan_fact_gate`，不改质量门路由。SettlementExtractor 仍写原结算库，不写 plan canon。

稳定 `project_id` 仍是 `xiafei-jiuan`。卡和 fixture 对照记录不变，见 [xiafei-plan-checks.md](xiafei-plan-checks.md)。同一组输入仍会标出路线图上的五类。这一刀没有重跑霞飞路，没有写新章，也没有新的召回数字。

**下一刀只做一件：** 重跑霞飞路《旧案》ch1–3，用这道只读门记下路线图五类的召回（目标 ≥4/5）。不写《规则年代》，不加题材规则，不把抽取吸进 canon。理由：卡、检查器和写章审查路径上的门都已经在；只有重跑才有新的实验数字。人工时长和成本仍是阶段 B 的另外两道门，不放进这一刀。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
