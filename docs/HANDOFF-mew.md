# Handoff：Mew 每日切片

owner：Bingtuu。目标与非目标以 [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 为准，架构方向以 [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) 为准。一次切片只做「下一刀」里的一件事。

## 先看哪里

| 要做什么 | 看 |
|----------|----|
| 今天做哪一件 | 本文件「下一刀」 |
| 怎样算 90 天证明了 | [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 阶段 A → B → C |
| 为什么倒过来写 canon | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 事实卡 schema（已合入的容器） | `src/songyan/models/plan_facts.py`；`src/songyan/db/plan_fact_repo.py`；`src/songyan/db/migrations.py` |
| 霞飞路批准卡与窄检查 | `src/songyan/plan_facts/xiafei_jiuan.json`；`src/songyan/plan_checks/`；[xiafei-plan-checks.md](xiafei-plan-checks.md) |
| 现有结算路径（先别改权威） | `src/songyan/agents/settlement_extractor/`。它仍写原结算库，不写 plan canon |
| Phase A 已完成 | B7 #5、B5 #6、B18 #8。不要再开这三刀 |

证据数字只用来自 2026-10 的 owner 笔记：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、成本记录。不要在切片里补一批新的评测数字。

## 下一刀

**Phase A 已完成。** B7 #5、B5 #6、B18 #8 已在 main。事实卡 schema 也已在 main。规模写作仍然冻结。

**本刀是霞飞路《旧案》ch1–3 批准事实卡，加上三项窄检查，并已随本文件落地。** 稳定 `project_id` 是 `xiafei-jiuan`。卡在 `src/songyan/plan_facts/xiafei_jiuan.json`，由 `songyan.db.plan_fact_loader`（或 `scripts/load_plan_facts.py`）写入现有 `plan_*` 表。行都是 `approval_status=approved`。九一八前的时局锚来自种子，`source=plan`；证物方向、数量、归属、案发三月、机制方向由 Mew 代批，`source=human`。owner 不必再审这些卡。对照记录在 [xiafei-plan-checks.md](xiafei-plan-checks.md)。

检查器在 `src/songyan/plan_checks/`，没有接进写章图，也不写结算库：

- 必须提及：本章 `must_mention_in` 的登记用语是否都出现
- 主张核验：事件卡上的主张判支持 / 矛盾 / 未提及，并附引文。默认用确定性锚点，不调用模型；LLM 路径复用 `call_llm`，测试注入 complete
- 类型化属性：方向、数量、时间锚、归属与结构化摘录做代码比较

fixture 用 canon-v4 的三章正文对照这些卡，路线图上的五类都会被标出。那是对照记录，不是重跑之后的召回数字。

**下一刀只做一件：** 把这三项检查接到章节流水线的只读门上。只读已批准的 plan 卡。不改 SettlementExtractor 的权威路径，也不把正文抽取吸进 plan canon。先不重跑霞飞路，不写新章。理由：卡和检查器已经能在 v4 正文上标出那五类；最小的下一步是让写章路径调用它们。召回 ≥4/5 要等门接上之后再单开一刀重跑，才有新的实验数字。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
