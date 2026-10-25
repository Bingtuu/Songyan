# 都市灵异《末班铜牌》ch1–3 活路径（2026-10-25）

活路径召回 **1/5**。目标是 ≥4/5。**阶段 C 退出条件未满足**，因为召回失败。正文来自 Mew 的 box（有 `LLM_API_KEY`，`deepseek-chat`），运行项目 `153fe8f222534585a2bdc2410496dfa0`，批准卡 `dushi-lingyi`。云端虚拟机没有参与这次写章。

错误类是这个故事自己的 D1–D5，不是霞飞路的 T1–T6。规则：拦截或不发生都算召回；短语缺席不等于未发生。

`scoreboard.json` 与 `scoreboard-live.json` 是同一份 Mew 定稿，原样抄入。`occurred.json` 是各类的发生 / 拦截 / 召回布尔。`occurred_basis.md` 是定稿之前的读章依据，原样保留。阶段 C 另外两道门（人工、成本）在 [gates.md](gates.md)，原始数字在 [`phase-c-cost-human.json`](phase-c-cost-human.json)。

| 类 | 发生 | 门 | 召回 |
|----|------|----|------|
| D1 刻痕方向/数量漂移 | 是。第 3 章刻痕从一道变成两道，东向西变成西向东 | 活路径无 typed extracts，`attribute_mismatches=0` | 未召回 |
| D2 灵印记名归属漂移 | 是。窗内交还后登记簿记名改为沈酌，第 2–3 章延续 | 主张无锚，claim 全是 unmentioned | 未召回 |
| D3 灵印位置离牌（上腕等） | 否。三章未见记名迁到手腕，位置保持牌面 | 第 2 章必须提及缺「铜牌正面」，不构成本类拦截 | 召回（未发生） |
| D4 交还朝向漂移（面朝东） | 是。第 2 章监控面朝西仍通过；第 3 章备注循环西/北/东/南 | 无锚，未拦 | 未召回 |
| D5 改写禁忌被打破（窗内仍改写） | 是。第 1 章交还约 23:52 在窗内，随后记名仍改写为沈酌 | taboo claim 为 unmentioned | 未召回 |

`anchors_supplied` 与 `extracts_supplied` 都是 false。D3 这次能记召回，是因为那一类没有发生。D1、D2、D4、D5 发生了，活路径没有拦住。

## 活路径上摘录和锚没有人填

`run_chapter_pipeline` 不写 `_plan_attribute_extracts`，也不写 `_plan_claim_anchors`。`rule_auditor_node` 把这两项原样交给 `run_plan_fact_gate`。门不从正文现抽，也不把摘录写进 plan canon。

这次跑完后的门信号（`passed` 三章都是 false）：

| 章 | missing_mentions | attribute_mismatches | claim_verdicts |
|----|------------------|----------------------|----------------|
| 1 | `23:40`（`dly-clue-window`；正文用「二十三点四十」） | 0 | 4× unmentioned |
| 2 | `铜牌正面`（`dly-clue-mark-site`） | 0 | 4× unmentioned |
| 3 | 无 | 0 | 3× unmentioned |

必须提及只抓 mention term 的字面。它没有拦住 D1、D2、D4、D5。第 2 章缺「铜牌正面」也不算拦住了 D3：D3 的召回来自未发生，不是来自拦截。类型化漂移和主张矛盾在这条活路径上不可见。

## 三道门

判定在 [gates.md](gates.md)。

| 门 | 判定 |
|----|------|
| 召回 ≥4/5 | **fail** — 1/5（只有 D3） |
| 人工 ≤10 分钟/章 | **pass_with_delegation_note** |
| 成本与 v1 同量级 | **borderline / owner call** — owner ¥6.830 vs v1 ≈¥1.37（约 5 倍）；没有一章达到 ¥7.66 |

阶段 C 退出条件未满足。召回失败是退出未过的原因。成本不记 pass。人工是带委托说明的 pass。

## 这一刀没有做的事

没有写《规则年代》。没有加题材规则，没有新的 `plan_checks`。没有把抽取吸进 plan canon。没有改 SettlementExtractor。没有改质量门路由。没有接 `_plan_attribute_extracts` / `_plan_claim_anchors`。没有把薄封装写成 owner 已经接受的结论。

按路线图的失败路径，停止加题材规则。推荐 owner 下一刀做决定，二选一：（a）接受薄封装结论——人维护事实圣经，AI 按圣经写；（b）可选的单独一刀，只把摘录和锚接到审查 state，用同一套 D1–D5 重记召回。推荐项是（a）。（b）是阶段 B 推迟的 option 1，不是新的题材规则。
