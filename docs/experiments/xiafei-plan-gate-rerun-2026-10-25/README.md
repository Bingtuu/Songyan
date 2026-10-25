# 霞飞路《旧案》ch1–3 只读门重跑（2026-10-25）

活路径召回 **5/5**。目标是 ≥4/5。正文来自 Mew 的 box（本 PR 分支，有 `LLM_API_KEY`），项目 `030b687372374aa491e0c294e6d62969`。云端虚拟机没有密钥，没有参与这次写章。

`scoreboard.json` 是这次测量。`scoreboard-live.json` 是计分脚本的原输出。`occurred.json` 与 `occurred_basis.md` 是读 `chapters/` 之后的发生判断。

| 类 | 发生 | 门 | 召回 |
|----|------|----|------|
| T1 证物属性漂移 | 是。第 2 章「两道新鲜的刮痕」，没有钉住「右向左」 | 第 2 章必须提及缺「右向左」 | 召回 |
| T5 证物归属漂移 | 否。没有把钩状弧线放到横杆拓片上 | 没有标出。活路径没有摘录和锚 | 召回（未发生） |
| T4 机制方向 | 否。没有「往外拉」对上「从外往内拉」 | 第 3 章必须提及缺「往外拉」 | 召回（未发生） |
| T2 证据遗漏 | 是。第 1 章有后脑伤口，三章都没有登记用语「钝器伤」 | 第 2 章必须提及缺「钝器伤」 | 召回 |
| T6 时代时间线 | 否。没有「日军进逼锦州」；第 3 章「昭和六年三月」与案发 `1931-03` 相容 | 第 1 章必须提及缺「九一八」 | 召回（未发生） |

`anchors_supplied` 与 `extracts_supplied` 都是 false。必须提及拦住了 T1 和 T2。T5 这次能记召回，是因为那一类没有发生；归属漂移若再出现，活路径仍然标不出。

## 活路径上摘录和锚没有人填

`run_chapter_pipeline` 不写 `_plan_attribute_extracts`，也不写 `_plan_claim_anchors`。`rule_auditor_node` 把这两项原样交给 `run_plan_fact_gate`。门不从正文现抽，也不把摘录写进 plan canon。

## 怎样复跑

```bash
export LLM_API_KEY=...
python scripts/rerun_xiafei_plan_gate.py
```

脚本用 `tpl/xiafei/` 建项目，把批准卡改记到该项目 id，再按章 `songyan run --auto-confirm`。没有密钥时它会改写 `scoreboard.json` 为未计分；这次的 5/5 以 `scoreboard-live.json` 为准。

人工时长和成本没有记。没有写《规则年代》。没有加题材规则。没有把抽取吸进 plan canon。没有改 SettlementExtractor。没有改质量门路由。没有开始阶段 C。
