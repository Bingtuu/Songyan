# Handoff：Mew 每日切片

owner：Bingtuu。目标与非目标以 [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 为准，架构方向以 [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) 为准。一次切片只做「下一刀」里的一件事。

## 先看哪里

| 要做什么 | 看 |
|----------|----|
| 今天做哪一件 | 本文件「下一刀」 |
| 怎样算 90 天证明了 | [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 阶段 A → B → C |
| 为什么倒过来写 canon | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 事实卡 schema（本刀已合入的容器） | `src/songyan/models/plan_facts.py`；`src/songyan/db/plan_fact_repo.py`；`src/songyan/db/migrations.py` 的 `_migrate_plan_fact_cards` |
| 现有结算路径（先别改权威） | `src/songyan/agents/settlement_extractor/`。它仍写原结算库，不写 plan canon |
| Phase A 已完成 | B7 #5、B5 #6、B18 #8。不要再开这三刀 |

证据数字只用来自 2026-10 的 owner 笔记：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、成本记录。不要在切片里补一批新的评测数字。

## 下一刀

**Phase A 已完成。** B7 #5（失败 `error` 非空）、B5 #6（HTTP 超时打断挂起）、B18 #8（按用户 ¥2/M 输入、¥8/M 输出口径报告成本）已在 main。规模写作仍然冻结。

**本刀是事实卡 schema，并已随本文件落地。** 表和读写已经在仓库里，不要再做一遍。ADR-0001 的最小记录可以创建、读回、再写回 SQLite，并且带稳定 ID：

- `entity(id, type, aliases)` → `plan_entities`
- `attribute(entity_id, key, value, valid_from_ch, valid_to_ch, source=plan|human)` → `plan_attributes`
- `event(id, ch, time_anchor, participants, causes, reveals_evidence[])` → `plan_events`
- `time_anchor(date, kind=story|history)` → `plan_time_anchors`
- `clue(id, planted_ch, revealed_ch, must_mention_in[])` → `plan_clues`

`approval_status` 为 `approved` 或 `pending`。canon 读只返回 `approved`，attribute 还要求 source 是 `plan` 或 `human`。pending 行留在表里，不能被当成已成立事实。不把 SettlementExtractor 的抽取结果写进这些表，也不改它的权威路径。

本刀不做：霞飞路 ch1–3 正文、《规则年代》续写、窄检查器、改写 plan/write/review 图节点、题材专用规则、开放式全书找矛盾。

**schema 合入之后，下一刀只做一件：** 人工确认的霞飞路《旧案》ch1–3 事实卡 / 事件卡，加上窄检查（必须提及、主张核验、类型化属性比较）。schema 只是容器；召回门要靠人批过的卡和这三项窄检查才能测。仍然不要开始《规则年代》的规模写作。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
