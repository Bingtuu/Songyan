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
| 都市灵异批准卡（Phase C 种子） | `src/songyan/plan_facts/dushi_lingyi.json`；`project_id=dushi-lingyi`。加载走同一套 `songyan.db.plan_fact_loader`，不另加检查器 |
| 都市灵异活路径记录（Phase C 已关闭，退出未过） | [experiments/dushi-plan-gate-rerun-2026-10-25](experiments/dushi-plan-gate-rerun-2026-10-25/README.md)，[gates.md](experiments/dushi-plan-gate-rerun-2026-10-25/gates.md) |
| 现有结算路径（先别改权威） | `src/songyan/agents/settlement_extractor/`。它仍写原结算库，不写 plan canon |
| Phase A 已完成 | B7 #5、B5 #6、B18 #8。不要再开这三刀 |

证据数字只用来自 2026-10 的 owner 笔记，外加 box 上已经测得的召回、人工与成本：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、v1 成本记录、霞飞路重跑 5/5 与阶段 B 人工/成本（[experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)，[gates.md](experiments/xiafei-plan-gate-rerun-2026-10-25/gates.md)）、都市灵异活路径 1/5 与阶段 C 人工/成本（[experiments/dushi-plan-gate-rerun-2026-10-25](experiments/dushi-plan-gate-rerun-2026-10-25/README.md)，[gates.md](experiments/dushi-plan-gate-rerun-2026-10-25/gates.md)）。不要在切片里再补一套新的评测数字。

## 下一刀

**Phase A 已完成。** B7 #5、B5 #6、B18 #8 已在 main。事实卡 schema、霞飞路批准卡、三项窄检查、写章审查上的只读门也已在 main。规模写作仍然冻结。

**阶段 B 已完成，三道成功门都有记录（main #13，`c84a2dac`）。** 活路径召回 5/5（≥4/5）。人工 ≤10 分钟/章记为 **pass_with_delegation_note**：owner 在 2026-10-25 把批卡委托给 Mew（「你来审核吧，不用给我看」）；没有秒表；若 owner 自己读计分板和 `occurred_basis`，估计 ≤5 分钟/章。成本同量级 **pass**：owner 口径合计 ¥2.115（两位小数 ¥2.12），v1 ≈¥1.37，约 1.5 倍；ch1 ¥0.824 / ch2 ¥1.072 / ch3 ¥0.219。没有一章达到 v1 第 3 章 ¥0.766 的十倍。正文来自 box 上的项目 `030b687372374aa491e0c294e6d62969`。记录在 [experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md) 与 [gates.md](experiments/xiafei-plan-gate-rerun-2026-10-25/gates.md)。

`rule_auditor_node` 仍只读已批准卡，结果仍在 `_plan_fact_gate`，不改质量门路由。SettlementExtractor 仍写原结算库。2026-10-25 那次霞飞路活路径没有摘录和锚。T5 这次没有发生。阶段 C 的都市灵异活路径跑的时候也还没有这两项，D1、D2、D4、D5 发生且未被拦住。切片 1 之后，审查节点会在调用方没钉住列表时，按当前版本正文把 `_plan_attribute_extracts` / `_plan_claim_anchors` 填上再交给同一扇门。上面两段召回数字是接线之前的记录。

**阶段 C 已关闭。退出条件未满足。操作结论是薄封装。** owner Bingtuu 在 2026-10-26（Asia/Shanghai）选定 **(a) 接受薄封装结论**：人维护事实圣经，AI 按圣经写。2026-10-25 指定的第二体裁仍是 **都市灵异**。种子和批准卡已在 main：`project_id=dushi-lingyi`，标题《末班铜牌》，卡在 `src/songyan/plan_facts/dushi_lingyi.json`，全部 `approval_status=approved`。Mew 按 owner 的委托代批。仓库题材配置没有「都市灵异」这个 id，卡上的 `genre_id` 仍是已能加载的 `urban_fantasy`。box 上的活路径写出 ch1–3，运行项目 `153fe8f222534585a2bdc2410496dfa0`。错误类是这个故事的 D1–D5，不是霞飞路 T1–T6。记录在 [experiments/dushi-plan-gate-rerun-2026-10-25](experiments/dushi-plan-gate-rerun-2026-10-25/README.md) 与 [gates.md](experiments/dushi-plan-gate-rerun-2026-10-25/gates.md)。

- 召回 **fail**：1/5，门槛 ≥4/5。只有 D3（灵印位置离牌、上腕）因未发生记召回。D1 刻痕方向/数量、D2 灵印记名归属、D4 交还朝向、D5 窗内改写禁忌都发生了。活路径没有摘录和锚，`attribute_mismatches` 三章都是 0，主张核验缺省为 unmentioned，这四类没有被拦住。
- 人工 **pass_with_delegation_note**：owner 在 2026-10-25 把批卡委托给 Mew。没有秒表。计分板由 Mew 按 `occurred_basis` 定稿。
- 成本 **borderline / owner call**：owner 口径合计 ¥6.830，v1 ≈¥1.37，约 5 倍。ch1 ¥3.216 / ch2 ¥2.599 / ch3 ¥1.015。没有一章达到 v1 第 3 章 ¥0.766 的十倍（¥7.66）。这道门不记 pass。

**阶段 C 以召回失败关闭，退出条件未满足。** 这是「需要更多人在环」的记录。操作结论仍是薄封装：人维护事实圣经，AI 按圣经写。

**切片 1 已完成（2026-10-26，owner Bingtuu 下令加速，只做接线）。** `rule_auditor_node` 在审查 state 没有同时钉住 `_plan_attribute_extracts` 和 `_plan_claim_anchors` 时，从本章正文和已批准卡读出类型化摘录和主张锚，写回这两项，再交给原来的 `run_plan_fact_gate`。下一轮修订按新稿重读，不沿用上一稿。调用方已经同时放了列表时，沿用调用方的列表。门仍不从正文发明摘录，也不写 canon。没有新的题材检查器。没有重记 D1–D5。没有改 SettlementExtractor，没有改质量门路由，没有写《规则年代》。

**切片 2 已完成（2026-10-26，薄封装运行时）。** 写章上下文只读当前项目、当前章的已批准计划卡，放进 `ContextPackage.plan_bible`。Writer 和修订提示词把这段放在最前面，当作本章事实圣经。待审卡、别的章、别的项目、窗口盖不住本章的属性，不进圣经。审查仍把正文摘录留在 `_plan_attribute_extracts` / `_plan_claim_anchors`，不把它们写成 plan canon，也不自动送进待审队列。人批准仍是进 canon 的唯一入口。`plan_fact_gate` 没过时，失败条目出现在 human gate 的 `plan_fact_gate_failures`，并记在 `plan_fact_gate.failures` 日志里。接受、退回、质量门的路由都不变。SettlementExtractor 仍只写原结算库。没有新的题材检查器。没有重记 D1–D5。没有发版，没有写《规则年代》。

**下一刀是切片 3：发布核对与冒烟。** 核对写章会读已批准圣经、审查失败对人可见、正文抽取不进 canon。不要加题材规则，不要改 SettlementExtractor 的权威，不要重记阶段 C 的召回。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
