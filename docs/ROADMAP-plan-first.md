# Plan-first 一致性路线（约 90 天）

> **读者**: owner（Bingtuu）与每日切片执行者（Mew）
> **起点**: 2026-10-22
> **更新**: 2026-10-26。Phase A 已合入 main（B7 #5、B5 #6、B18 #8）。Phase B 已完成（#13，`c84a2dac`）：霞飞路 ch1–3 活路径三道门已有记录，召回 **5/5**，人工 **pass_with_delegation_note**，成本同量级（¥2.115 vs v1 ≈¥1.37）。Phase C 活路径已跑完（都市灵异《末班铜牌》ch1–3，项目 `153fe8f222534585a2bdc2410496dfa0`）：召回 **1/5，fail**（门槛 ≥4/5，只有 D3），人工 **pass_with_delegation_note**，成本 owner ¥6.830 vs v1 ≈¥1.37（约 5 倍，**borderline / owner call**；没有单章 ≥¥7.66）。**阶段 C 已关闭，退出条件未满足。** owner 在 2026-10-26（Asia/Shanghai）选定 **(a) 接受薄封装结论**：人维护事实圣经，AI 按圣经写。同日下令加速，顺序是切片 1→2→3。切片 1 已在 main（#17，`196f5379`）：摘录和锚接到审查 state，没有重记召回。切片 2 已在 main（#18，`11c4c761`）：薄封装运行时，已批准计划卡作为本章事实圣经；写作和修订读这些卡，审查失败出现在 human gate，正文抽取不进 canon。切片 3 的真实 LLM Ch1–3 发布冒烟已有记录（2026-10-26 Asia/Shanghai，main `11c4c761`）：**fail**。科幻项目 `fdfc04b0771c493b83ec67750325ade7`，主运行 `run-e98414fc`，第 2 章重跑 `run-3defb98a`。只有第 1 章 accepted。第 2、3 章 `settlement_review` 失败（摘要缺主角决策/认知变化）。主运行非零：`AutoHaltException`（ContextEmergency 连续 Ch1–3）。Owner 口径 ¥0.874（ch1 ¥0.208 / ch2 ¥0.406 含重跑 / ch3 ¥0.260），停的阈值 ¥7.66 没碰到。部分通过：doctor、create-project、report、bundle 卫生（无 `.env`/密钥/书稿）、导出 1 个 md。产物在维护者 box（`/workspace/songyan-release-smoke-out/smoke_result.json`、`notes.md`，以及 smoke_result 里的 reports/bundles/exports），不在仓库。正式发布标签挡住。技术预览 / release-candidate 口径不变。下一刀只修 `settlement_review` / `summary_writer` 的这一处缺口。不是再开阶段 C。不再加题材专用检查器。
> **状态**: 方向已定，阶段 C 以薄封装收束（退出未过）。SettlementExtractor 的权威路径尚未改写。写作和审查只读已批准 plan 卡，不把抽取写进 canon。切片 3 真实 LLM Ch1–3 发布冒烟 **fail**（main `11c4c761`），正式发布标签挡住。技术预览 / release-candidate 口径不变。下一刀只修摘要缺的主角决策/认知变化。
> **每日入口**: [HANDOFF-mew.md](HANDOFF-mew.md)
> **架构决定**: [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md)

## 目标

约 90 天内证明一件事：**plan-first 能把跨章真错误召回做到可用**。可用的尺子是霞飞路这一类错误上 **召回 ≥4/5**。

这 90 天的进度是召回门，规模写作先冻住。《规则年代》停在已有章节。CED / T9 / 五门和 200 章 baseline 继续按 [STATUS](STATUS.md) 的公开口径保留。

## 证据（只引用已有记录，不新造数字）

| 记录 | 和本路线有关的结果 |
|------|-------------------|
| canon-v4 对照：《霞飞路旧案》（新 seed）vs《规则年代》v3 | 人工跨章真错误 5 条（证物漂移 2、机制方向 1、证据遗漏 1、时代时间线 1）。检查器召回 **0/5**。规则年代上 fixture 8/8，但那些类型在新故事里没有复发，所以没有被这次检验。编辑分 ch1/2/3 = 6.0 / 6.5 / 6.0。 |
| 《规则年代》Ch1–3 编辑审稿 | 人名漂移、跨章数值、章首无视章尾、已付代价被遗忘。CED、T9、五门、LLM 审查都没抓到。settlement 把「父亲沈拓」写进 setting，漂移进了事实库。只改 seed、不改代码的 v2：父亲名在 Ch1–2 稳定，性别却从「他」变成「她」；Ch3 再次卡死（B5），未补跑。 |
| 调研报告（2026-10-13） | 根因是事实来源方向：先写正文，再从正文抽事实，抽取会抽象化证据、为同一物体建多条记录、把漂移吸进 canon。开放式「找出全书矛盾」对强模型也难（报告引用 NoCha 上 GPT-4o 55.8%，FlawedFictions 随长度下降，FABLES 自动评审与人类相关性弱）。给定一条具体主张加证据片段，判断是否一致，是可做的窄任务。 |
| Linux bug 记录（commit `257314c`） | 阻断/高：B5 调用挂起（creative_director 空转 11 分钟以上；v2 第 3 章复现后 kill），B7 第 3 章 human_gate 已接受、settlement 已完成，仍 `chapter_failed error=None`，run 为 partial，没有恢复提示。B18 成本口径：工具自报 ¥0.457，按用户 ¥2/M 输入、¥8/M 输出约为 ¥1.37。 |
| 成本记录（`llm_call_usage`） | 正式产出 v1 三章：用户口径 **≈¥1.37**，工具自报 ¥0.458（第 1/2/3 章用户口径 ¥0.358 / ¥0.246 / ¥0.766；第 3 章含一次静默失败后的整章重跑）。审查开销约是写作的 3 倍。两次卡死的挂起请求没有入账。canon loop 边际约 ¥0.06–0.1/章，每触发一次重试再加约 ¥0.3。 |
| 霞飞路活路径重跑（2026-10-25，box，项目 `030b687372374aa491e0c294e6d62969`） | 五类召回 **5/5**。T1、T2 发生且被必须提及拦住；T4、T6 未发生；T5 未发生（活路径没有摘录和锚，发生时标不出）。见 [实验记录](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)。 |
| 同一项目的人工与成本（`llm_call_usage`，[`phase-b-cost-human.json`](experiments/xiafei-plan-gate-rerun-2026-10-25/phase-b-cost-human.json)） | 人工 **pass_with_delegation_note**（owner 委托批卡，没有秒表；若 owner 读计分板，估计 ≤5 分钟/章）。成本 owner 口径 ch1/2/3 = ¥0.824 / ¥1.072 / ¥0.219，合计 ¥2.115，对比 v1 ≈¥1.37。见 [gates.md](experiments/xiafei-plan-gate-rerun-2026-10-25/gates.md)。 |
| 都市灵异活路径（2026-10-25，box，项目 `153fe8f222534585a2bdc2410496dfa0`，《末班铜牌》） | 故事自己的五类召回 **1/5，fail**（门槛 ≥4/5）。D3 灵印位置离牌未发生，记召回。D1 刻痕方向/数量、D2 灵印记名归属、D4 交还朝向、D5 窗内改写禁忌发生，活路径没有摘录和锚，没有拦住。见 [实验记录](experiments/dushi-plan-gate-rerun-2026-10-25/README.md)。 |
| 同一项目的人工与成本（`llm_call_usage`，[`phase-c-cost-human.json`](experiments/dushi-plan-gate-rerun-2026-10-25/phase-c-cost-human.json)） | 人工 **pass_with_delegation_note**（owner 委托批卡，没有秒表）。成本 owner 口径 ch1/2/3 = ¥3.216 / ¥2.599 / ¥1.015，合计 ¥6.830，对比 v1 ≈¥1.37，约 5 倍，**borderline / owner call**。没有一章达到 ¥7.66。见 [gates.md](experiments/dushi-plan-gate-rerun-2026-10-25/gates.md)。 |
| 发布冒烟（2026-10-26，Asia/Shanghai，维护者 box，main `11c4c761`，科幻，项目 `fdfc04b0771c493b83ec67750325ade7`） | **fail**。主运行 `run-e98414fc` 非零退出（`AutoHaltException`，ContextEmergency 连续 Ch1–3）。只有 Ch1 accepted。Ch2、Ch3 失败在 `settlement_review`，摘要缺主角决策/认知变化。Ch2 另有重跑 `run-3defb98a`。Owner 口径合计 ¥0.874（ch1 ¥0.208 / ch2 ¥0.406 含重跑 / ch3 ¥0.260）。停的阈值 ¥7.66 没碰到。部分通过：doctor、create-project、report、bundle 卫生（无 `.env`/密钥/书稿）、导出 1 个 md。产物在维护者 box 的 `/workspace/songyan-release-smoke-out/`（`smoke_result.json`、`notes.md`，以及 smoke_result 里的 reports/bundles/exports），不在本仓库。 |

调研报告给出的最小实验口径，本路线直接沿用：人工确认事实卡后重跑 ch1–3；拦截或不发生的 v4 类错误 **≥4/5**；人工 **≤10 分钟/章**。

## 阶段

### A. 冻住规模写作，先修阻断运行的 bug

**状态（2026-10-25）：已完成。** B7 #5、B5 #6、B18 #8 已合入 main。不往《规则年代》后面加章。表里「验收」是当时的门，不是还没做的工作。

| 项 | 状态 | 验收 |
|----|------|----------------------|
| B5 挂起 | 已合入 #6。 | 超时落到实际 HTTP 调用上。挂起被总超时打断，日志里有超时错误，而不是静静空转。 |
| B7 静默失败 | 已合入 #5。 | 失败日志里的 `error` 非空，写明原因（`settlement_review` 与 missing facts）和恢复提示。human_gate 已接受、settlement 已完成的章，不能再以 `error=None` 收场。 |
| B18 成本 | 已合入 #8。chat 报告按用户口径（输入 ¥2/M、输出 ¥8/M）。 | 实验笔记和 report 标明用的是哪一套口径。在价目对齐之前，对照实验以 `llm_call_usage` 的 token 按用户口径复算，不拿工具自报 `cost_cny` 当账单。 |

A 的退出条件是这三项各自有可复现的测试或记录，不是「顺手重构生成管线」。这三条已经各自落地。

### B. 最小对照：人批事实卡 → 写 3 章 → 窄验证

**第一刀（随本文件合入）：事实卡 schema。** ADR-0001 的五类记录可以创建、读回、再写进 SQLite，带稳定 ID。`approval_status` 把 `pending` 和 plan|human 已批准的 canon 行分开。这一刀不写霞飞路正文，不接窄检查，不改 SettlementExtractor 的权威路径，也不把抽取结果自动吸进这些表。

**第二刀（随本文件之后的切片）：批准卡 + 三项窄检查。** `project_id=xiafei-jiuan` 的 ch1–3 卡已批准入库。必须提及、主张核验、类型化属性比较在 `src/songyan/plan_checks/`，用 v4 正文做了 fixture 对照（见 [xiafei-plan-checks.md](xiafei-plan-checks.md)）。

**第三刀（审查路径上的只读门）：** 写章审查在正文版本存在之后调用这三项检查，只读当前项目已批准的 plan 卡。不改 SettlementExtractor 权威，不把抽取吸进 canon，也没有重跑正文。成功门不变，留到重跑那一刀。

**重跑这一刀（2026-10-25，knife4）召回 5/5。** box 上的活路径写出 ch1–3（项目 `030b687372374aa491e0c294e6d62969`）。T1 证物属性漂移、T2 证据遗漏发生，必须提及拦住了。T4 机制方向、T6 时代时间线未发生；门仍标出缺「往外拉」「九一八」。T5 证物归属漂移未发生，记为召回。记录在 [experiments/xiafei-plan-gate-rerun-2026-10-25](experiments/xiafei-plan-gate-rerun-2026-10-25/README.md)。召回门达到 ≥4/5。

**人工和成本这一刀（2026-10-25，knife5）补上另外两道门的记录。** 数字来自 box 上该项目的 `llm_call_usage`，见 [gates.md](experiments/xiafei-plan-gate-rerun-2026-10-25/gates.md) 与 [`phase-b-cost-human.json`](experiments/xiafei-plan-gate-rerun-2026-10-25/phase-b-cost-human.json)。没有改生产代码。

- 人工 **pass_with_delegation_note**。owner 把批卡委托给 Mew（「你来审核吧，不用给我看」）。没有秒表。若 owner 读计分板和 `occurred_basis`，估计 ≤5 分钟/章，落在门的 10 分钟/章以内。记下的是委托事实和这个估计。
- 成本 **pass**。owner 口径合计 ¥2.115（由 ¥2.115 四舍五入到分是 ¥2.12；ch1 ¥0.824、ch2 ¥1.072、ch3 ¥0.219），v1 三章合计 ≈¥1.37，约 1.5 倍，同一数量级。停的阈值是单章超过 v1 第 3 章 ¥0.766 一个数量级；最高的 ch2 ¥1.072 没有到。工具 `cost_cny` 与 owner 口径一致，因为估算用了同一套 ¥2/M、¥8/M。`cost_cny` 仍是估算标签。对账以 provider 账单为准。

**阶段 B 退出：三道门都有记录，退出条件满足。** 召回 pass，成本 pass，人工是带委托说明的 pass。没有未记录的成功门挡着阶段 C。owner 已指定阶段 C 体裁，见下方 C。

2026-10-25 那次活路径不填 `_plan_attribute_extracts` / `_plan_claim_anchors`。门做得到必须提及，做不到类型化不符。T5 这次没发生。这是那次记录的限制，不是没记下的成功门。切片 1（2026-10-26，#17，`196f5379`）起，审查节点在调用方没钉住列表时会从当章正文读出摘录和锚再交给门。上面的 5/5 仍是接线之前的数字。

窄验证仍只做下面三件事。阶段 C 不加第四件。

1. **必须提及**：本章计划点名的证物、伤情、时间锚，生成后逐条核对是否出现。
2. **主张核验**：事件卡上的每条主张，对照正文段落，判支持 / 矛盾 / 未提及，并附引文。
3. **类型化属性**：方向、数量、时间锚、归属等能代码比较的字段做代码比较。

正文里新冒出来的事实进待审队列。人批准之后才可以进 canon。

成功门（三条都要有记录，缺一条不算过）。2026-10-25 三道都有记录，阶段 B 退出条件满足：

- 召回 **≥4/5**：已记录，**5/5，pass**。分母是 v4 那 5 条人工真错误所属的类：证物属性漂移、机制方向、证据遗漏、时代时间线。拦截或不发生都算召回；每条的归类在实验记录里，不只给一个总分。
- 人工 **≤10 分钟/章**（批卡、看核验、决定待审项）：已记录，**pass_with_delegation_note**。没有秒表。owner 委托 Mew 批卡；若 owner 读计分板和 `occurred_basis`，估计 ≤5 分钟/章。
- 成本说得清：已记录，**pass**。活路径 owner 口径合计 ¥2.115，v1 三章合计 ≈¥1.37（v1 单章 ¥0.246–¥0.766），同量级。单章没有超过 v1 第 3 章（含重跑，¥0.766）一个数量级。若以后有一章跨过这个数量级，先停，先报告，不加检查项。

可选、单独成一次切片：检查器改用 deepseek-reasoner 的消融，只看召回和成本增量。推理模型只用在窄判断上，不用来通读找错。

### C. 第二体裁 3 章，不加题材专用规则

**状态（2026-10-26）：阶段 C 已关闭。退出条件未满足。操作结论是薄封装。** owner Bingtuu 在 2026-10-26（Asia/Shanghai）选定 **(a) 接受薄封装结论**：人维护事实圣经，AI 按圣经写。体裁仍是他在 2026-10-25 指定的 **都市灵异**（调研报告曾建议仙侠或言情；以 owner 指定为准）。`project_id=dushi-lingyi`，标题《末班铜牌》：当代宁波地铁夜班，一枚铜牌的刻痕方向与数量、灵印记名与位置、末班时间窗、交还朝向是可核对的规则。卡在 `src/songyan/plan_facts/dushi_lingyi.json`，经现有 `plan_fact_loader` 入库，全部 `approval_status=approved`。Mew 按 owner 委托代批。代码和检查规则与 B 相同。没有新的题材检查器。

题材配置里没有「都市灵异」这个 id。卡上 `genre_id` 用已经能加载的 `urban_fantasy`（配置名「都市异能」）。故事身份写在标题和 `core_hook`。没有新增题材配置。

**活路径这一刀（2026-10-25）已有记录。** box 上写出 ch1–3（运行项目 `153fe8f222534585a2bdc2410496dfa0`）。召回的分母是 Mew 为《末班铜牌》标出的 D1–D5，不是霞飞路的五类。见 [实验记录](experiments/dushi-plan-gate-rerun-2026-10-25/README.md)、[gates.md](experiments/dushi-plan-gate-rerun-2026-10-25/gates.md) 与 [`phase-c-cost-human.json`](experiments/dushi-plan-gate-rerun-2026-10-25/phase-c-cost-human.json)。没有改生产代码。

成功门与 B 相同。三道门都有记录，判定如下：

| 门 | 判定 |
|----|------|
| 召回 ≥4/5 | **fail** — 1/5（只有 D3） |
| 人工 ≤10 分钟/章 | **pass_with_delegation_note** |
| 成本与 v1 同量级 | **borderline / owner call** — ¥6.830 vs ≈¥1.37（约 5 倍）；没有单章 ≥¥7.66 |

- 召回 **fail**。只有 D3（灵印位置离牌、上腕）未发生，记召回。D1 刻痕方向/数量、D2 灵印记名归属、D4 交还朝向、D5 窗内改写禁忌都发生了，活路径没有拦住。
- 人工 **pass_with_delegation_note**。owner 把批卡委托给 Mew。没有秒表。计分板由 Mew 按 `occurred_basis` 定稿。
- 成本 **borderline / owner call**。owner 口径合计 ¥6.830（ch1 ¥3.216、ch2 ¥2.599、ch3 ¥1.015），v1 三章合计 ≈¥1.37，约 5 倍。停的阈值是单章超过 v1 第 3 章 ¥0.766 一个数量级；最高的 ch1 ¥3.216 没有到 ¥7.66。同量级不记 pass。阶段 B 的对照是约 1.5 倍。

**阶段 C 退出条件未满足，因为召回失败。** 缺召回这一条，退出不算过。成本留给 owner 判断，不记成 pass。人工是带委托说明的 pass。

那次活路径不填 `_plan_attribute_extracts` / `_plan_claim_anchors`。必须提及只抓到字面（第 1 章缺 `23:40`，第 2 章缺 `铜牌正面`），`attribute_mismatches` 三章都是 0，主张核验缺省为 unmentioned。D1、D2、D4、D5 发生时没有被拦住。D3 能记召回，是因为那一类没有发生。这些数字是接线之前的记录。

**失败路径已经收束。** owner 在 2026-10-26（Asia/Shanghai）选定 **(a)**，接受薄封装：**人维护事实圣经，AI 按圣经写**。阶段 C 以召回失败关闭，作为「需要更多人在环」的记录。不再加题材专用检查器。同日切片 1（#17，`196f5379`）把摘录和锚接到审查 state，没有重记 D1–D5，也没有改 SettlementExtractor。切片 2（#18，`11c4c761`）让写作和修订读已批准计划卡，并在 human gate 上标出 `plan_fact_gate` 失败；正文抽取仍不进 canon。切片 3 的真实 LLM Ch1–3 发布冒烟（main `11c4c761`）**fail**：只有第 1 章 accepted，第 2、3 章卡在 `settlement_review`（摘要缺主角决策/认知变化）。正式发布标签挡住。技术预览 / release-candidate 口径不变。下一刀只修这一处，不是再开阶段 C。

## 非目标

这些不做，也不要在每日切片里顺手做：

- 开放式全书 / 多章「找矛盾」。
- 把正文抽取到的事实自动吸收进 canon。
- 继续把「抽取 → 比对 → 打补丁」当主路径。
- 为每个新题材加专用检查规则来追召回。
- 用摘要链代替结构化状态。
- 写完《规则年代》或任何 300 章规模的正文。
- 在 A 的 bug 切片里改写规划 / 写作 / 审查管线。
- 在事实卡 schema 这一刀里改写规划 / 写作 / 审查图节点，或让 SettlementExtractor 停止写现有结算库。

## 90 天怎样算证明了

A 完成，并且 B 的三道门有记录。C 要么在不加题材规则的情况下过同一组门，要么写下薄封装退路。两条都算这条路线有了结论。结论可以是「plan-first 够用」，也可以是「必须更多人在环」；不能是「再加一批检查规则继续抽」。

2026-10-26 owner 选定 (a)。都市灵异活路径没有过同一组门（召回 1/5）。薄封装成为操作结论：人维护事实圣经，AI 按圣经写。这条路线已经收束，结论是「必须更多人在环」。阶段 C 已关闭。不再加题材专用检查器。切片 1 已在 main（#17，`196f5379`），把摘录和锚接到审查 state，没有重记召回。切片 2 已在 main（#18，`11c4c761`），把已批准卡接到写作和修订，并让 human gate 看见门的失败。切片 3 发布冒烟 **fail**（main `11c4c761`，只有第 1 章 accepted）。正式发布标签挡住。技术预览 / release-candidate 口径不变。下一刀只修 `settlement_review` / `summary_writer` 缺的主角决策/认知变化。
