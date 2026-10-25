# 霞飞路《旧案》ch1–3 只读门重跑（2026-10-25）

这一刀要的是路线图五类的召回。本环境没有测出这个数字。

## 为什么没有召回

云端虚拟机没有 `LLM_API_KEY`，工作区只有 `.env.example`，没有 `.env`。Songyan 的写章走 DeepSeek（`LLM_BASE_URL` 默认 `https://api.deepseek.com`，模型 `deepseek-chat`）。`songyan run` 的 preflight 在 `llm.key` 失败，不会出正文。

所以这里没有新的第 1–3 章，五类都是 `unscored`，`recalled` 是 null。这不是 0/5，也不是 ≥4/5。v4 对照仍然是检查器在旧正文上的 fixture 结果，不是这次重跑。

`scoreboard.json` 由 `scripts/rerun_xiafei_plan_gate.py` 在这台机器上写出。

## 活路径上摘录和锚没有人填

`run_chapter_pipeline` 的初始 state 只把 `_plan_fact_gate` 设为 `None`。它不写 `_plan_attribute_extracts`，也不写 `_plan_claim_anchors`。`rule_auditor_node` 把这两项原样交给 `run_plan_fact_gate`。门不从正文现抽，也不把摘录写进 plan canon。

因此一次真实的 `songyan run` 上：

- 必须提及会跑，能标出登记用语缺席（「右向左」「钝器伤」「往外拉」「九一八」）。
- 主张没有锚时只认主张原文。对不上就是未提及。这个缺省值不能当成矛盾，也不能当成 T2 的拦截。
- 类型化比较没有摘录就是空的。T5 钩痕归属（ch3 把钩状弧线放到横杆上）靠类型化归属或主张矛盾，活路径标不出。

`tests/plan_checks/test_plan_fact_gate.py` 用 v4 第 3 章锁住了这件事：同一段正文，不带摘录和锚时归属不符为空、`claim-ch3-hook` 为未提及；带上 fixture 摘录和锚时，类型化归属不符，主张为矛盾。

计分在 `src/songyan/plan_checks/roadmap_recall.py`。发生与否必须由读新正文的人写进 `occurred.json`。v4 的矛盾短语没出现，不等于这一类没发生。

## 有密钥时怎么重跑

在仓库根目录：

```bash
export LLM_API_KEY=...   # 或写入 .env，不要把密钥交到命令行历史以外的日志里
python scripts/rerun_xiafei_plan_gate.py
```

脚本会：

1. 用 `tpl/xiafei/`（种子、大纲、模板，与 v4 那次相同）建一个新项目。
2. 把批准卡从 `xiafei-jiuan` 改记到这个项目的 id 上再入库。门按 `state["project_id"]` 读卡，不改记就看不到。卡的稳定 id 是主键，同一库里再加载一次会把行挪走，所以用脚本自己的 `run/songyan.db`。
3. 按章调用 `songyan run --chapters N --auto-confirm`，每章最多 4 次（后几次带 `--resume`），单次 1800 秒。
4. 把接受的正文导出到 `chapters/ch01.md` 起。导出之后仍然不填召回。

然后读正文，写下发生与否：

```json
{"T1": false, "T5": false, "T4": false, "T2": false, "T6": false}
```

`true` 表示这一类在新章里发生了。类型化摘录沿用 `tests/fixtures/xiafei_jiuan/v4_extracts.json` 的形状，按新正文另写一份 `extracts.json`。没有这份文件时，T5 这类归属漂移计分脚本也标不出。

```bash
python scripts/score_xiafei_roadmap_recall.py \
  --chapters-dir docs/experiments/xiafei-plan-gate-rerun-2026-10-25/chapters \
  --occurred docs/experiments/xiafei-plan-gate-rerun-2026-10-25/occurred.json \
  --extracts docs/experiments/xiafei-plan-gate-rerun-2026-10-25/extracts.json \
  --output docs/experiments/xiafei-plan-gate-rerun-2026-10-25/scoreboard.json
```

`--live-path` 去掉锚和摘录，用来对照审查 state 实际交给门的那一档。召回规则：某一类被门标出，或新章里没发生，都算召回。五类都有判断才写总分。

人工时长和成本不是这一刀的门。写章如果留下 `llm_call_usage`，用现有的 `songyan report` 看，不在这里复算。

## 这一刀没有做的事

没有写《规则年代》。没有加题材规则。没有把抽取吸进 plan canon。没有改 SettlementExtractor 的权威。没有改质量门路由。没有开始阶段 C。
