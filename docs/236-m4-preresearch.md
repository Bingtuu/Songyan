# 236 · M4 技术方案前置调研报告

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-08 |
| 状态 | DONE（task 236，owner 三轮评审已吸收：Q2 复用条件、Q4 钉死 status、N7 验收分列、接口三线钉死、P0-6 settlement 边界、行号修正、§9 P0/P1 缺口评估与四条写死句建议） |
| 用途 | 为 `docs/tech-m4.md` 草稿备料；本报告是方案前的调研层，不是方案本身 |
| 方法 | A 需求面（PRD 精读）/ B 代码现状面（thorough 考古）/ C 历史经验面（评审审计）/ D 外部调研面（同类工具） |

---

## 1. 结论速览

1. **M4 的两条命令（`chapter continue` / `review`）都有充足的现成零件**：单章执行器（`run_chapter_pipeline` + `resume_human_confirm`）、章推进判定（`_compute_resume_start` + `accepted` 为准）、审读三入口 + gate（全部函数级 Pydantic 输出）、ContextEmergency 数据已持久化在 `context_snapshots`。M4 的主成本不在新建能力，而在**语义衔接设计**。
2. **调研中发现三个 PRD 未写明、方案必须回答的新问题**（见 §6；owner 评审补充：最大实现风险在 Q2——`resume_human_confirm` 是 LangGraph interrupt + thread 恢复，不能直接当 CLI 确认闸复用，交互模型必须先钉死）：
   - N1：W2 短环「抽卡 → pick → 人确认 → 下一章」的「人确认」缺命令——**人确认的 accepted 写径只有 run 管线内 human_confirm 一条**；而现网另有一条**无人确认的自动 accepted 写径**（import replay，见 N7），M4 方案必须一并回答两者。
   - N2：`continue` 若复用 `run` 管线，其「上一章」判定按 `accepted_version_id IS NOT NULL`——上一章 picked 但未 accepted 时会**回头重写上一章**，与作者直觉相反。
   - N3：PRD 字面「`review` 不改库、不入典」与现成聚合零件 `merge_reviews` 的写库副作用（落 `review_reports`）冲突——方案需明确 review 是纯只读还是允许审计落库。
3. 四大前置设计问题（chapter 状态机 / continue↔variant / review 输入并集 / ContextEmergency 露出）每条都有 2 个以上可行方案与代码级证据（§5）。
4. 外部同类工具（NovelCrafter Codex、authorflows canon-check、Wrylo local-first+BYO-key）验证了本产品方向（事实库注入 + 对照检查 + 人keeper），无方向性颠覆，有交互细节可借鉴（§4）。

---

## 2. A 需求面：PRD 中的 M4

来源：`docs/prd-v1.md`（以下行号为 2026-11-08 版本）。

**边界（§5 表，:172）**：M4 = `chapter continue` 默认 1 章；W2 短环「计划卡 → 一章 → 共审 → 人确认 → 下一章」。边界外：不把 10 章以上无审连跑写成作者路径；不宣称文学可连载。

**`continue` 语义（:435, :419, :585）**：
- `chapter continue --count 1` 默认一章；`--variants 2` 可转入抽卡（与 M3 衔接的显式口）。
- `--require-plan`：缺关键硬约束时可拒绝或强警告（M0 不改写作图所以 M0 无此拒绝——M4 才做）。
- 章节作者状态解释层（:131-138）：`empty → outlined → drafting → variants_ready → picked → human_rewriting → in_review → needs_settlement → settled → stale`，允许跳 `picked → in_review`（人几乎没改）、`settled → stale`（事后改硬事实）、`stale → drafting`（人决定重写）。**这是解释层不是现网列**——方案要决定映射或显式不映射。

**`review` 语义（:485, :501, :586, :334）**：
- 输入并集：`check` 的问题 ∪ 复读/专名提示 ∪ variant 备注 ∪ 人的 mark。
- 只读边界：`:586` 表「`check` / `review` 不改库、不入典」；`:501` M4 验收「`review` 在不调用 confirm 的测试里，库中 approved 行数不变」。
- 「复读、专名启发式、共审清单在 M4 的 `review`」（:334）——复读/专名是**新检查器**，不在现有 gate 里。

**ContextEmergency（:442, :612）**：「单章仍超限则减少注入，而不是加长连跑。`status` 在 M4 露出次数」——PRD 明确要求 M4 把人可见性做出来。

**M4 验收（:448）**：连续 3 章走 W2，没有任何自动 `approved`；作者只看 `today` 能说出下一章该做什么。→ `today` 的 `next` 文案在 M4 还要再演进一步（M3 步 6 已提示抽卡，M4 要提示 continue 环）。

**W 流定位**：W2（先典后续写）= M4 主路径（:188）；W6 共审增强在 M4（:183）；W3 续写「保持未验收」（:186）。

---

## 3. B 代码现状面（事实清单，证据 = 文件:行号）

> 本節为考古摘要，完整事实清单见调研工作底稿（agent-12 报告）；此处只收与 M4 设计直接相关的事实。

### 3.1 chapter 状态面

- `chapter_heads`：`status` 默认 `'draft'`，注释值域 `draft | under_review | accepted`，**无 DB CHECK、无模型枚举校验**（`src/songyan/db/schema.sql:233-244`、`src/songyan/models/chapter.py:53-63`）。写入方：writer 初稿（`agents/writer.py:893-906`，**重置 draft 并清 `accepted_version_id`**）、accept（`_nodes.py:2958-2970`）、revision under_review（`agents/revision_handler/__init__.py:1291-1295`）、variant pick（`services/variant_pick.py:100-117`，head 不存在时新建 draft）。
- **「完成」判定 = `accepted_version_id IS NOT NULL`，不看 status**：`run` 跳过逻辑 `workflows/phase2_graph.py:758-769`、下一章确定 `_compute_resume_start`（`phase2_graph.py:586-598`）。`current_version_id` 是工作指针；`accepted_version_id` 是完成事实源。
- 章推进零件：`_find_resume_run` / `_save_run_state`（`phase2_graph.py:561-583, 100-107`）、`_get_previous_summary`（`phase2_graph.py:66-97`，只读 `summaries.plot_summary` 并**截断 120 字**）、`ProjectRunRepository` + `project_runs` 表（断点/进度/暂停原因/总成本）。

### 3.2 variant 与 continue 衔接面

- `chapter_variants.status` CHECK：`generated|picked|abandoned|archived`；同章最多一 picked（`db/migrations.py:1620-1659`）。
- pick 语义（`services/variant_pick.py:59-133`）：refresh stale → 旧 picked 转 archived → `current_version_id = content_ref`；**不动 accepted、不动 plan_*、不动 content_stale**。即 picked 稿 ≠ 可续写底稿（PRD :140 同此口径：stale 的 variant 不能当默认续写底稿）。
- 生成编排（`services/variant_generate.py:115-234`）：fingerprint + `load_chapter_plan_bible` + 逐 slot `default_slot_draft`（`call_llm(role="writer")`）+ 双表同事务；`DraftFn` 可注入。
- **缺口（事实）**：`run_chapter_pipeline` 的上一章衔接只读 120 字摘要，不读 picked/accepted 正文；「正文级上一章衔接」无现成函数。
- **关键事实**：`variant pick` 后没有「人确认 → accepted」的衔接路径。**人确认的 accepted 写径只有 run 管线内 human_confirm 一条**（`_nodes.py:2958-2970`）；另有一条**自动 accepted 写径**：import replay（`services/import_replay_service.py:498-560` 的 `_accept_with_replay_mark`，同一事务 `accept_version` + head 置 accepted，无人确认，注释自承镜像 `_nodes.py` 事务序列）——M4 需明确它与新确认语义的并存口径（见 §6 N7）。

### 3.3 review 输入面

- `check`（`cli/commands/check.py:172-246`）= `run_plan_fact_gate`（`plan_checks/gate.py:65-112` → `PlanFactGateReport`：missing_mentions / claim_verdicts / attribute_mismatches / passed）+ `content_stale` 范围；正文来源约定 = accepted head → version.content。
- 三审函数级入口：`run_rule_audit`（`agents/rule_auditor.py:1649`，纯代码不调 LLM）、`run_llm_audit`（`agents/llm_auditor.py:223`，`ReviewIssue` 带 12 维 category / severity / evidence_quote / fix_type）、`run_literary_audit`（`agents/literary_auditor.py:162`）。落库：`review_reports` / `literary_observations`（`db/review_repo.py:165, 235`，后者有 `list_*_by_chapter_range`）。
- 聚合点：`merge_reviews`（`workflows/review_merger.py:655-724`，**副作用 = 写 review_reports**）；纯读取聚合 `load_latest_audits`（`workflows/_helpers.py:417`）。
- 复读/专名启发式：**产品检查器路径现网不存在**（PRD :334 说它们在 M4）；`evals/excellence_signals.py:646-715` 已有「逐字句子 / 逐字段落 / 跨章逐字复读」评测信号实现——**算法可移植，但接口不同（evals 信号 vs plan_checks 检查器），需封装改造，非同接口即插**。
- 五门 / t9 / continuity 均有 Pydantic 输出与函数级入口（`evals/five_gate_acceptance.py:535` 等）。

### 3.4 ContextEmergency 面

- 触发：`budget_used > emergency_trigger_ratio` 时触发（默认 1.0；有体裁 `GenreRuntimeProfile` 时取 `profile.context_emergency_trigger_ratio` 覆盖，`agents/context_manager/__init__.py:362-367`）→ `_context_emergency`（同文件 :912-952），level=3，清空大部分注入只留硬约束。
- 已持久化：`context_snapshots.context_emergency / _level / budget_used_before_emergency`（`schema.sql:220-222`，`_save_context_snapshot` `_nodes.py:654-674`）；章日志 JSONL 也记（`workflows/_run_logger.py:87, 246`）。
- 现有人可见性：仅 `songyan report` echo 一行（`cli/main.py:1246-1252`）+ `bundle-run` 计数。**无 CLI 从 DB 读它**（`today` / `check` / `canon show` 均不输出）。
- 最小露出点：`context_snapshots` 按 project+chapter 有索引（`schema.sql:227-228`），但 `ContextSnapshotRepository` 现网只有 `create()` 与 `get(snapshot_id)`（`db/repository.py:647-714`）——**M4 需新增按 project/chapter 的查询方法**，再在 workbench 渲染层加一段。

### 3.5 LLM / 计费 / 预算面

- `call_llm`（`llm/client.py:426-654`）：统一入口（重试/熔断/遥测落库 `llm_call_usage`）；role 路由 `resolve_llm_config`（10 个注册角色，writer 在内）；run 上下文成本以 DB 合计为权威。
- 预算守卫：调用数 + CNY 成本双熔断（`LLMBudgetExceededError`，run 循环接 pause）；`run_cost_budget` / `llm_run_call_budget` 默认 0 = 不启用。
- continue/review 走 LLM 时计费与预算零件**全部可直接复用**。

---

## 4. C 历史经验面（审计与失败教训 → M4 设计约束）

来源：`docs/superpowers/plans/2026-11-07-m0-m3-review-audit.md`、task 226/228/231 修复记录、Ch1–10 冒烟失败（DG-1、ContextEmergency 10/10）。

1. **人确认边界是最高优先级约束**（audit blocker #1 的教训：settlement 直写 resolved 曾绕过确认）。→ M4 任何「章推进」「状态翻转」都不得有自动 approved / 自动 accepted 写径；测试必须覆盖「带副作用路径」（audit 发现 M2 测试只测只读路径漏掉违规写径）。
2. **写库副作用要显式声明**（audit major #2 双重记账、#5 非原子提交的教训）。→ review 若允许落审计库，必须在方案里写明哪些表、什么事务边界；若纯只读，要防止误用 `merge_reviews`。
3. **exit 码语义要可分辩**（observation：`check` 无章可查与未过门共用 exit 2）。→ continue/review 的 exit 码设计要预留区分空间。
4. **Ch1–10 失败模式**（ContextEmergency 10/10、时间线回滚、复读）说明：无审连跑 + 上下文超载 = 质量崩坏。→ 支持 PRD 边界「不把 10 章以上无审连跑写成作者路径」；ContextEmergency 露出（Q4）是 M4 的实质质量信号，不是装饰。
5. **文案纪律**（task 231）：新文本输出列名/措辞须与 `content_stale` / `stale_vs_canon` 防混原则一致。

---

## 5. D 外部调研面（同类工具的可借鉴模式）

轻量调研（2026-11，详见搜索记录），取模式不取依赖：

| 模式 | 来源 | 对 M4 的启示 |
|------|------|--------------|
| Codex/事实库随写随注（角色、地点、时间线作为一等对象注入生成） | [NovelCrafter 评测](https://findyourai.com/writing-copy/novelcrafter/)、[对比文](https://blog.chapter.pub/sudowrite-vs-novelcrafter/) | Songyan plan bible/canon 已是同构；M4 continue 的上下文组装可直接沿用，无需新机制 |
| 「先建 canon，再把新文本对照 canon 检查」的审稿流 | [authorflows 连续性检查评测](https://www.authorflows.com/blogs/best-ai-novel-continuity-checking) | review 的输入并集（Q3）与该模式一致；可借鉴其「逐章对照 + 报告」呈现 |
| 三层提示：canon briefing → 显式约束 → 创作请求 | [ProseEngine](https://proseengine.app/blog/how-to-stop-ai-from-contradicting-your-story-s-established-facts) | 与 Context Diet 硬约束一致；ContextEmergency 时可 degraded 到 briefing+约束两层，露出给人 |
| local-first + 自带 API key 的长篇工作室 | [Wrylo](https://fazier.com/launches/wrylo) | 产品形态同路；无新增要求 |
| 行业共识：瓶颈是编辑与一致性，作者仍是真相 keeper | [Sudowrite vs NovelCrafter](https://writeabookai.com/blog/sudowrite-vs-novelcrafter-ai-novel-writing-2026) | 支持 M4「共审增强」而非「自动续写」的定位 |

**结论**：外部无方向性颠覆；M4 设计应保持「人 keeper + 系统对照」的主线，借鉴点是 review 报告的呈现结构（问题按章聚合、严重度分级、证据引用）。

---

## 6. 四大设计问题深化 + 新发现问题

### Q1 · chapter 状态机映射

- **现状证据**：现网 `chapter_heads.status` 三值注释（draft/under_review/accepted）无强校验；真实判定走 `accepted_version_id IS NOT NULL`；PRD 解释层 11 态（:131-138）。
- **约束**：PRD 说解释层「不是现网列」——不强求建状态机；但 `today next`（M4 验收 :448 要求「只看 today 能说出下一章」）需要可计算的「下一章该做什么」。
- **方案 A（映射视图，推荐调研倾向）**：不加列，写一个「章进度视图」纯函数：从 `accepted_version_id` / `current_version_id` / variant 状态 / `content_stale` 推导 PRD 11 态的子集（empty/drafting/variants_ready/picked/settled/stale 等可判定的），`today` 与 `continue` 共用。零迁移、可测试。
- **方案 B（落列状态机）**：head 加 `author_status` 列 + CHECK，所有翻转走服务层。表达力强，但引入第二状态源（与 accepted_version_id 双真源风险，违反「SQLite 唯一事实源」精神）。
- **方案 C（不映射）**：continue/today 直接回答操作问题（下一章缺什么、能不能写），不呈现状态名。最省，但 `today` 输出可解释性差。

### Q2 · continue ↔ variant 衔接

- **现状证据**：pick 不动 accepted（`variant_pick.py:59-133`）；continue 复用 run 零件时按 accepted 判定下一章（`phase2_graph.py:586-598, 758-769`）；`--variants 2` 是 PRD 钦定的转抽卡口（:435）。
- **约束**：PRD「stale 的 variant 不能当默认续写底稿」（:140）；「不自动选优」（M3 边界）；W2 短环含「人确认」步骤（:172）。
- **方案 A（continue = 单章管线 + 内嵌确认闸）**：`chapter continue` 跑一章（初稿或 `--variants N` 转抽卡），结束后停在「待确认」态，人确认（accept）后才推进游标。确认前再 continue = 提示先确认。**这把 N1（确认写径缺失）一并解决**。
  - **⚠ owner 评审钉死的复用条件（2026-11-08）**：现网确认机制是 **LangGraph interrupt + thread 恢复**（`resume_human_confirm`），不是一次性 CLI 确认——**不能直接当 CLI 确认闸复用**。tech-m4 必须先定两件事：① 新 `chapter accept` 命令 vs 复用 thread resume，二选一并写清交互模型；② `--json` / 非交互模式下 accept 怎么办（拒绝？生成待确认令牌？）。不定这两点，极易做出「能跑但绕过 W2 人确认」的实现。
  - 另：**accepted 游标 / import 自动 accept / `--variants`+stale 三条线的接口语义必须在接口层钉死**（见 N7 与 §7），不能只停在原则描述。
  - 另：**`chapter accept` 与 settlement 的边界必须先写清**（owner 评审补充，见 §9 P0-6）——否则 N1 补上后会把结算副作用带进作者确认。
- **方案 B（continue 要求上一章已 accepted）**：缺确认时拒绝并指向确认命令/流程（需要新命令或复用 run 的 resume 交互）。简单但 CLI 单次执行的交互模型与 `resume_human_confirm` 的 thread 恢复模型耦合深。
- **方案 C（continue 不认 variant，只管 outlined→draft）**：抽卡与续写完全分裂，违背 PRD `--variants` 口径。不推荐。
- **衔接细节（两方案都要回答）**：`_get_previous_summary` 只读 120 字摘要——M4 若要正文级衔接（读上一章 accepted/picked 正文节选），是新增组装函数还是沿用摘要链，方案需定。

### Q3 · review 输入并集

- **现状证据**：输入源全部函数级可读（§3.3）；`merge_reviews` 有写库副作用；PRD :586「不改库」与 :501（approved 行数不变）——**approved/计划表不动是明确的，review_reports 审计落库属灰区**。
- **方案 A（纯只读聚合，推荐倾向）**：`review` = 按章聚合 gate 报告 + 最新 review_reports（`load_latest_audits`，已落库的旧审计可读）+ literary_observations + 新增复读/专名启发式（纯代码，走 rule 风格不调 LLM）→ 渲染 markdown/json。**默认不调用 `merge_reviews`**（其写 review_reports 的副作用违反本方案定位，需合并逻辑时在 review 内做内存合并）。**复读/专名启发式是新代码**（§3.3：evals 算法可移植但需封装）。
- **方案 B（现算现聚合）**：调用三审 + gate 现算（LLM 调用、花钱）再聚合。报告新鲜但烧钱、慢，且 LLMAuditor 现算结果与「只读」定位冲突（它本身落 review_reports）。不推荐作为默认。
- **方案 C（A + 可选 LLM 深审旗标）**：默认 A；`--deep` 显式调 LLM 审（成本前置提示）。可作为后续增强写进方案但不实现。
- **新问题 N3 必须在此拍板**：review 是否允许写审计表（如复读命中记录）。建议默认不写，保持 PRD 字面。

### Q4 · ContextEmergency 露出

- **现状证据**：数据已在 `context_snapshots`（§3.4）；无 DB 读取面给人。
- **方案 A（钉死挂 `songyan status`，owner 2026-11-08 拍板）**：PRD 点名的命令就是 `status`——新建 `songyan status`，输出含「ContextEmergency 触发次数 / 最近触发章 / budget_used_before」段（读 `context_snapshots`，需新增按 project/chapter 查询方法，见 §3.4）。`today` 不承载此职责。
- **方案 B（章级 drill-down）**：`songyan review` / `check` 输出附带各章 emergency 标记（与 Q3 聚合合并）。信息更全，与 review 耦合；可作后续增强。
- **结论**：A 为 M4 必做（PRD :442），钉死挂顶层 `songyan status`；B 随 Q3 一起设计为可选附加段。命令树划清（owner 评审补充）：PRD §9.2 同时有顶层 `status`（「与 today 分工：today 是下一步，status 是本会话计数」）与 `chapter ... status`；**顶层 `status` 承载 ContextEmergency 次数露出；若未来做 `chapter status`，只读章进度，不承载 ContextEmergency**——tech-m4 用一句话写死此分工。

### 新发现问题（调研产出，方案必须回答）

| # | 问题 | 证据 | 不答的风险 |
|---|------|------|-----------|
| N1 | `picked → accepted` 人确认写径缺失 | pick 不置 accepted；唯一 accepted 写径在 run 管线内（`_nodes.py:2958-2970`） | W2 短环断了：抽卡后无法进入「下一章」 |
| N2 | continue 复用 run 零件时的上一章判定 | `_compute_resume_start` / 跳过逻辑按 `accepted_version_id`（`phase2_graph.py:586-598, 758-769`） | 上一章 picked 未确认 → continue 回头重写上一章，作者意图被违背 |
| N3 | review 的写库边界 | PRD :586 不改库 vs `merge_reviews` 写 review_reports（`review_merger.py:714`） | 方案灰区，验收口径争议 |
| N4 | 上一章衔接信息量 | `_get_previous_summary` 120 字摘要截断（`phase2_graph.py:66-97`） | continue 的「续写感」取决于此；需定「摘要 vs 正文节选」口径 |
| N5 | 复读/专名启发式是全新检查器 | PRD :334；产品检查器路径现网无；但 `evals/excellence_signals.py:647-715` 已有「逐字句子/段落/跨章复读」评测信号实现可复用 | 工作量评估需吸收 evals 现有实现，避免从零写 |
| N6 | `today next` 的 M4 演进 | PRD :448 验收要求 | M3 步 6 文案在 M4 需再改一轮（属 M4 范围） |
| N7 | import replay 自动 accepted 写径与 M4「无自动 accepted」约束并存口径 | `services/import_replay_service.py:498-560`（无人确认，镜像 `_nodes.py` 事务） | 若不回答：M4 验收「连续 3 章 W2 无自动 approved」与 import 回放路径的边界说不清。**验收写法必须分列**：「无自动 **Canon `approved`**」与「import 可自动 **chapter `accepted`**」是两件事，接口层与验收条目各自写清 |

---

## 7. 对 tech-m4.md 草稿的结构建议

对齐 tech-m0–m3 的章节模式（目标 / 仓库里已有的 / 做、改、不做 / 接口 / 小步 / 验收 / 验证命令 / 风险），草稿应额外含：

1. **「状态口径」节**：明确回答 Q1（视图 vs 落列；owner 已认可可判定子集映射）与 N1/N2（确认写径、上一章判定）——这是 M4 与现网差异最大的语义点。
2. **「review 写边界」节**：回答 N3（默认纯只读，不调 `merge_reviews`）。
3. **「确认交互模型」节（owner 评审新增要求）**：钉死 ① `chapter accept` 新命令 vs 复用 thread resume 的选择与理由；② `--json`/非交互的 accept 语义；③ accepted 游标 / import 自动 accept / `--variants`+stale 三条线的**接口级**定义（签名、事务、拒绝路径），不停留在原则。
4. **「status 命令」节（owner 评审钉死）**：`songyan status` 承载 ContextEmergency 次数露出（Q4A）。
5. **小步建议**（供草稿参考，非定案）：
   - 步 1：章进度视图纯函数 + `today` 露出（Q1A 骨架）+ ContextEmergency status 露出（Q4A）；
   - 步 2：`chapter continue` 单章执行 + 内嵌确认闸（Q2A + N1/N2）+ `--require-plan`；
   - 步 3：`review` 只读聚合（Q3A）+ 复读/专名启发式（N5）；
   - 步 4：验收与 today 文案收口（N6）。
6. **验收草案**：连续 3 章 W2 无自动 approved（PRD :448）；review 测试里 approved 行数不变（PRD :501）；`--require-plan` 拒绝路径锁死。

---

## 8. 附：可复用零件清单（B 面考古汇总）

| 零件 | 位置 | M4 用途 |
|------|------|---------|
| `run_chapter_pipeline` / `resume_human_confirm` | `workflows/phase1_graph.py:408, 531` | continue 的单章执行器；`resume_human_confirm` 是 **run 管线内**确认/恢复机制（LangGraph interrupt + thread），作者路径确认**不**复用它——用 `chapter accept`（见 §6 Q2） |
| `_compute_resume_start` / `_find_resume_run` / `_get_previous_summary` | `workflows/phase2_graph.py:586, 561, 66` | 下一章判定 / resume / 上一章摘要（N4 相关） |
| `ProjectRunRepository` + `project_runs` | `db/project_run_repo.py` | run 级断点与暂停语义 |
| `accept_with_settlement_boundary` | `workflows/_nodes.py:2958-2970` | accepted 写径参考（N1 相关） |
| `load_chapter_plan_bible` / `wrap_writing_prompt` | `plan_checks/bible.py:107, 53` | continue 的圣经注入（`--require-plan` 检查点） |
| `generate_chapter_variants`（DraftFn 可注入） | `services/variant_generate.py:115` | `--variants N` 转抽卡 |
| `run_plan_fact_gate` / `PlanFactGateReport` | `plan_checks/gate.py:65, 39` | review 输入之一 |
| `run_rule_audit` / `run_llm_audit` / `run_literary_audit` | `agents/rule_auditor.py:1649`、`agents/llm_auditor.py:223`、`agents/literary_auditor.py:162` | review 三审输入 |
| `load_latest_audits` / `ReviewReportRepository` / `LiteraryObservationRepository` | `workflows/_helpers.py:417`、`db/review_repo.py:165, 234` | review 读取聚合 |
| `ContextSnapshotRepository` + `context_snapshots` | `db/repository.py:647`、`schema.sql:213` | ContextEmergency 露出数据源 |
| `call_llm` / `resolve_llm_config` / 预算守卫 / `llm_call_usage` | `llm/client.py:426` 等 | continue/review 的 LLM 与计费复用 |

---

## 9. 缺口评估（owner 二轮评审，2026-11-08）

P0 = 不写进 tech-m4 就会形成语义破口；P1 = 草稿应写但可合并成节。逐条结论与建议归属：

### P0（5 条，全部要改，草稿必写）

| # | 缺口 | 评估 | 建议答案（供 owner 否决） |
|---|------|------|--------------------------|
| P0-1 | 确认命令产品面（新 CLI vs LangGraph resume） | 要改——这是 Q2 决策点本身 | **新 `chapter accept` 命令**：CLI 单次语义与 thread-resume 交互模型冲突；resume 机制保留给 `run` 管线内部；`chapter accept` 与 `canon confirm` 构成对称产品面（章级确认 vs 事实级确认）。命名空间 `chapter` 与 M1 非持久 `canon accept` 不冲突 |
| P0-2 | continue 与 `run`/`--auto-confirm` 并存、谁能动游标 | 要改——N7 的正面表述 | accepted 游标写径收口到**单一服务函数**（与 `accept_with_settlement_boundary` 同事务语义），`continue` 与 `run` 都经它；`run --auto-confirm` 定位不变（引擎冒烟，不是作者路径）；**不存在第三条 accepted 写径**，import replay 为历史路径、方案中列为豁免 |
| P0-3 | `--count>1` / 无审连跑上限硬行为 | 要改——PRD 边界（:172）的硬执行 | 结构上消灭「无审连跑」：`continue --count N` **逐章过确认闸**（N 只减少命令次数，不跳过确认）；上限不靠魔法数，靠「每章必须 accept 才推进」这一结构保证 |
| P0-4 | N7 验收豁免句 | **已改**（本轮 §6 N7 已分列「无自动 Canon approved」/「import 可自动 chapter accepted」） | 草稿验收节照抄分列句 |
| P0-5 | `--variants` 与 M3 pick/stale/`--allow-stale` 交接 | 要改——不写清必出两套语义 | `--variants N` = **转调 M3**（函数级 `generate_chapter_variants`，同进程，退出码与 M3 一致）；pick/abandon 仍由人显式调 M3 命令；continue 只在「上一章已 accepted」时启动；stale 规则沿用 M3（`--allow-stale` 语义不变，continue 不另造） |
| P0-6 | `chapter accept` 与 settlement 边界（owner 评审新增） | 要改——N1 补上后若沿用 `accept_with_settlement_boundary` 会把结算副作用（LLM 成本、提案写库）带进作者确认时刻 | **建议拆开**：`chapter accept` = 只移动 accepted 游标（`version_type=accepted` 副本，事务内仅此）；settlement 提案属审后步骤（PRD 4.2 目标语义即 `... → in_review → needs_settlement → settled`，结算在审后；run 管线绑事务是 auto 路径的历史耦合）。备选：沿用同一事务边界（与 run 行为一致，但结算副作用进确认时刻）——tech-m4 二选一写死 |

### P1（8 条，7 要改 1 已决）

| # | 缺口 | 评估 |
|---|------|------|
| P1-1 | exit 码表 | 要改——审计教训（`check` 无章可查与未过门共用 exit 2 不可分辩）；草稿给 `continue`/`accept`/`review`/`status` 一张显式 exit 码表 |
| P1-2 | `--json` / 费用可见 | 要改——延续 M3 步 5 口径；continue 打印本章实际费用（`llm_call_usage` 按章可查），`--json` 含 cost 字段 |
| P1-3 | `--require-plan` 拒绝 vs 警告判定 | 要改——建议：默认**警告**（exit 0，文案明示缺哪类硬约束）；`--require-plan` 时**拒绝**（exit 2，锁死测试） |
| P1-4 | 副作用路径 TDD 切片 | 要改——审计 blocker #1 的直接教训：accept 写径、游标推进必须「先红测试锁死再实现」 |
| P1-5 | ContextEmergency 挂哪个命令 | **已决**——Q4 已拍板 `songyan status` |
| P1-6 | continue 中断后的失败恢复 | 要改——continue 若不挂 `project_runs` 壳，中断即丢上下文；建议 continue 复用 run 壳（`_find_resume_run`/`pause_reason` 语义），中断后可恢复或幂等重跑，二选一写死 |
| P1-7 | 报告归档路径（引用链） | **不改**——`docs/236-m4-preresearch.md` 已 tracked 且四处引用已更新；tech-m4 完成后也不移动本报告（历史调研记录，引用链保持） |

### 四条写死句（owner 点名，草稿必须逐字回答）

| # | 问题 | 调研建议答案 |
|---|------|--------------|
| S1 | 可续写判定：严格 accepted vs picked+显式确认 | **严格 accepted**——与现网 resume 判定同口径避免双真源；picked → `chapter accept` 即成 accepted，衔接成本低 |
| S2 | `--variants N`：转调 M3 vs 内嵌 generate | **转调 M3**（见 P0-5），不内嵌第二套生成逻辑 |
| S3 | 上一章上下文：120 字摘要 vs 正文节选 | **正文结尾节选（预算硬顶）+ 120 字摘要并存**。数值不在调研层钉死：节选是否计入 Context Diet `budget_used`、超预算时降级策略（截断 / 退回纯摘要 / 标记 emergency），由 **tech-m4 接口节写死**（owner 评审决定） |
| S4 | review 默认是否写任何表 | **默认零写库**——纯只读聚合，与 PRD :586 字面一致；`merge_reviews` 不得进入 review 路径 |
