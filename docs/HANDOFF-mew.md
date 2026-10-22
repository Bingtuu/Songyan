# Handoff：Mew 每日切片

owner：Bingtuu。目标与非目标以 [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 为准，架构方向以 [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) 为准。一次切片只做「下一刀」里的一件事。

## 先看哪里

| 要做什么 | 看 |
|----------|----|
| 今天做哪一件 | 本文件「下一刀」 |
| 怎样算 90 天证明了 | [ROADMAP-plan-first.md](ROADMAP-plan-first.md) 阶段 A → B → C |
| 为什么倒过来写 canon | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| B7 静默失败 | `src/songyan/workflows/_nodes.py` 结算节点末尾：`status` 在 `settlement_needs_review` 时为 `settlement_review`，返回值不含 `error`。`src/songyan/workflows/phase2_graph.py` 的 `_run_single_chapter`：`status != "done"` 走失败支路，`error` 取 `final_state["error"]`，于是打出 `chapter_failed error=None`。 |
| B5 挂起 | `src/songyan/llm/client.py` 的 `call_llm` / `get_llm`（timeout 传给 ChatLiteLLM）。现象记在 commit `257314c` 的 bug 记录 B5。 |
| B18 成本 | `src/songyan/utils/cost_estimator.py` 的 `PRICING`。用户口径是输入 ¥2/M、输出 ¥8/M。 |
| 现有流水线（先别改写） | README「架构概览」；`src/songyan/agents/settlement_extractor/` |

证据数字只用来自 2026-10 的 owner 笔记：调研报告（2026-10-13）、canon-v4 对照、规则年代 Ch1–3 审稿、bug 记录（`257314c`）、成本记录。不要在切片里补一批新的评测数字。

## 下一刀（Day-2）

**修 B7，不建事实卡 schema。**

B7 让「章已接受」和「run 失败」同时为真，而且 `error=None`，没有恢复提示。Phase B 的召回、人工时间和成本都靠这次运行的成功/失败信号；信号是空的，三章对照测不准。事实卡是 Phase B 的底物，排在运行失败能被说清楚之后。

B5 同样阻断跑完三章，但超时要落到 HTTP 流上，离线测试比 B7 重。B18 是口径标签，不挡住把一章跑完。所以下一刀只做 B7：

- 当章结束于 `settlement_review`（或其它非 `done` 且 `error` 为空）时，失败结果带上非空 `error`。
- 文本写明原因。已知的一条是摘要 missing facts（bug 记录里的「缺少主角决策/认知变化」）以及 `_settlement_needs_human_review`。
- 带一条恢复提示（bug 记录里的绕过是对该章单独 `--chapters N` 重跑；提示与此一致即可）。
- 加一个不调用真实 LLM 的测试，锁住「`error` 不得为 `None`」。
- 不改写作、审查、结算入库，不改价目表，不引入事件卡模型。

做完 B7 再排 B5，然后 B18，然后才是 Phase B 的事实卡 schema。

## 怎么报告

每刀结束用短记录回复 owner，包含：

1. 分支名和 PR 链接。
2. 改了哪些文件，对应路线图上的哪一项（B5 / B7 / B18 / 事实卡 / 其它）。
3. 跑了什么测试，结果是什么。
4. 这刀明确没做的事。
5. 下一刀只推荐一件，并写一句理由。

规模写作保持冻结：不要为了「看看效果」继续写《规则年代》。
