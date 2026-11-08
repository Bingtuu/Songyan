# M4 技术方案（草稿）：`chapter continue` / `review`

- **状态：** 2026-11-08 Asia/Shanghai。**草稿，未经 owner 接受。** 只覆盖 [prd-v1.md](prd-v1.md) 的 **M4**（`chapter continue` 默认 1 章；W2 短环：计划卡 → 一章 → 共审 → 人确认 → 下一章；共审增强 `review`）。接受前本文对编码无约束力。包版本仍是 `0.5.0`。
- **输入：** [docs/236-m4-preresearch.md](236-m4-preresearch.md)（task 236，含 owner 三轮评审：四条写死句 S1–S4、缺口 P0-1..6 / P1-1..7）。本文逐字回答其中全部决策点。
- **本文不做的决定：** 不规划 M4 之后的里程碑（发布、真实模型验收、M5+）；不改写 M0–M3 已接受语义。不要把本文扩成整代路线图。
- **前置：** M3 步 1–6 与 §6–7 代码验收已在 `main` `594144b` **PASS**（task 234）。包版本仍是 `0.5.0`。

Owner 要求技术方案按里程碑、小步推进。M4 让作者走完 W2 短环：从已确认的 Canon 出发，续写一章、共审、人确认、再续下一章——全程**无自动入典、无自动 accepted、无审不连跑**；`review` 把已有检查信号聚合成一份纯只读的共审报告。

---

## 1. 目标

作者对一个已有项目能走完：

- **W2 短环：** `chapter continue`（默认 1 章）→ 新章草稿（或 `--variants N` 转抽卡）→ 人改稿 → `chapter accept` 确认本章 → 再 `continue` 下一章；`review` 在任意时刻给出按章聚合的共审报告（只读）
- **无自动权威：** `continue` / `accept` / `review` 全程 `plan_*` 的 `approved` 行集合不变；无自动 `canon confirm`；`chapter accept` 是**章级**人确认写径，与 `canon confirm`（事实级）对称
- **上下文诚实：** 上一章衔接用「正文结尾节选（有预算硬顶）+ 120 字摘要」，受 Context Diet 预算约束；ContextEmergency 触发次数经 `songyan status` 对人露出（PRD :442）
- **费用可见：** continue 打印本章实际费用（`llm_call_usage` 按章可查）；`--json` 含 cost 字段

不把 10 章以上无审连跑写成作者路径，不宣称文学可连载，不注册空桩，不升包版本，不声称 V1.0 完成。

---

## 2. 仓库里已经有的

M4 在 M0–M3 的 Canon / today / check / variant / content_stale / 承诺之上加续写与共审；**不重写**这些模块的权威语义，除非 §3–§4 写明的窄改建。

| 能力 | 位置 | M4 怎么用 |
|------|------|-----------|
| 单章执行器 | `run_chapter_pipeline` / `resume_human_confirm`（`workflows/phase1_graph.py:408, 531`） | 复用前者执行一章；后者是 **run 管线内**的 LangGraph interrupt + thread 恢复机制——**作者路径确认不复用它**（B2） |
| 章推进判定 | `_compute_resume_start` / `_find_resume_run` / `_get_previous_summary`（`workflows/phase2_graph.py:586, 561, 66`） | 「下一章 = 范围内第一个非 accepted 章」口径直接复用；上一章摘要现读 120 字 `plot_summary`（B6 扩正文节选） |
| run 壳 | `project_runs` 表 + `ProjectRunRepository`（断点 / `pause_reason` / `total_cost`） | continue 挂 run 壳：中断可恢复、幂等重跑（B9） |
| accepted 写径 | `accept_with_settlement_boundary`（`workflows/_nodes.py:2958-2970`） | **参考其事务序列，不直接复用**——accept 与 settlement 拆开（B2/B5） |
| 抽卡 | `generate_chapter_variants`（`services/variant_generate.py:115`，`DraftFn` 可注入） | `--variants N` 转调它（B7）；pick/abandon 仍由人显式调 M3 命令 |
| 圣经 / 上下文 | `load_chapter_plan_bible` / `wrap_writing_prompt`（`plan_checks/bible.py:107, 53`）、Context Diet 组装 | continue 的上下文组装沿用；节选段计入口径见 B6 |
| 审读输入 | `run_plan_fact_gate` / 三审入口 / `load_latest_audits` / `ReviewReportRepository` / `LiteraryObservationRepository` / `ContinuityAuditor.audit` | review 的只读输入源（B8） |
| 复读信号 | `evals/excellence_signals.py:646-715`（逐字句 / 段 / 跨章复读） | 算法**移植封装**为 plan_checks 风格检查器（新代码，非即插） |
| ContextEmergency 数据 | `context_snapshots` 表（`context_emergency` / `_level` / `budget_used_before_emergency`，`schema.sql:220-222`） | `status` 读它；repo 现网只有 create/get——**新增按 project/chapter 查询方法**（窄改建） |
| LLM / 计费 / 预算 | `call_llm` / `resolve_llm_config` / 预算守卫 / `llm_call_usage` | 直接复用；continue/review（复读启发式不调 LLM）费用与预算守卫零新建 |

现码 **没有** `chapter continue` / `chapter accept` / `review` / 顶层 `status` 命令；**没有** snapshot 按章查询方法；**没有** 复读/专名产品检查器；`resume_human_confirm` **不是** CLI 确认闸。这些是本里程碑要接的缺口。

---

## 3. 做、改、不做

### 3.1 做

1. **`songyan chapter continue`**：默认 `--count 1`；逐章过确认闸；`--variants N` 转调 M3 抽卡；`--require-plan`；中断挂 run 壳可恢复（B3–B7, B9）。
2. **`songyan chapter accept --chapter INT`**：章级人确认写径（B2/B5）；picked / 人改稿 → accepted。
3. **`songyan review [--chapter INT]`**：纯只读共审报告（B8）。
4. **`songyan status`**：本会话计数面（PRD §9.2 分工），含 ContextEmergency 触发次数 / 最近触发章 / `budget_used_before`（B10）。
5. **章进度视图纯函数**：从 `accepted_version_id` / `current_version_id` / variant 状态 / `content_stale` 推导 PRD §4.2 可判定子集（B1）；`today` 用它回答「下一章该做什么」。
6. **复读 / 专名启发式检查器**：纯代码，plan_checks 风格，供 `review` 调用（移植 evals 算法）。
7. **snapshot 按 project/chapter 查询方法**（窄改建，服务 `status`）。
8. CLI / 服务测试覆盖第 6 节。

### 3.2 改

- 新增 CLI 组：`chapter accept|continue`、`review`、`status`（**禁止**先注册空桩）。
- `today` 的 `next` 文案：M4 口径（提示 continue 短环下一步）；措辞纪律同 task 231（不与 `content_stale` / `stale_vs_canon` 混列）。
- `ContextSnapshotRepository`：新增按 project/chapter 查询（仅此窄扩建）。
- `phase2_graph` 的上一章摘要注入点：旁路新增「正文结尾节选」段（不改动 `run` 管线的既有 120 字路径行为，continue 走自己的组装函数）。

### 3.3 不做

- 无人值守多章连载；`--count N` 跳过确认闸；把 `run --auto-confirm` 写成作者主路径。
- 自动 pick / 自动选优 / 自动 `chapter accept` / 自动 `canon confirm`。
- `chapter status` 命令（若未来做，只读章进度，**不承载** ContextEmergency——B10 分工）。
- 在 `chapter accept` 事务内跑 SettlementExtractor（B5 拆开）；改 settlement 观测层权威。
- `review` 写任何表（含 `review_reports`）；在 review 路径调用 `merge_reviews`（B8）。
- 给 `plan_*` 加列；改五表三态；建 Git `branch`。
- 改写 M0–M3 已接受语义（Canon 三态、promise 销账人确认、extract→pending、variant 语义、S8）。
- 改 `pyproject.toml` 版本（保持 `0.5.0`）；声称 V1.0 完成。
- 在本文里写 M4 之后的实现步骤。第 9 节只列「留给以后」。

### 3.4 绑定决策（具体）

下列决策在**接受本文后**对编码有约束力；实现切片不得静默改写。未接受前本文仅为草稿。

#### B1. 可续写判定 = 严格 accepted（写死句 S1）

- 「下一章」= 范围内第一个 `accepted_version_id IS NOT NULL` 的章之后那章；**与现网 resume 判定同口径**，不引入 picked+显式确认的第二口径（避免双真源）。
- picked 稿想进入可续写态，唯一路径 = `chapter accept`（B2）。continue 遇到「目标章**之前**存在 picked 未 accept 的章」→ 拒绝（exit 2），提示先 accept（新问题 N2 的正面处理）。
- **目标章已有未确认工作稿时再跑 continue（review major 修补）**：目标章存在未 accept 的 draft / picked 工作稿时，continue 拒绝（exit 2），提示先 `chapter accept` 或走显式 `variant pick|abandon`；M4 **不提供**自动重生成旗标（防止静默覆盖工作稿）。

#### B2. `chapter accept`：新命令，CLI 确认语义（P0-1）

- **不用** `resume_human_confirm`：那是 LangGraph interrupt + thread 恢复，服务 run 管线内部；作者路径确认是一次性 CLI 语义。
- 命令：`songyan chapter accept --project-id TEXT --chapter INT [--from-file PATH] [--json]`。`chapter accept` 是 PRD §9.2 命令树（`chapter list|status|continue`）的**增量**——W2「人确认」步骤的必要补全，非越界。
- `--json` / 非交互：accept 本身就是显式命令（人已在命令行敲了它），**无需交互**；`continue` 的输出只提示「下一步可 `chapter accept --chapter N`」，不在 continue 内部嵌确认提示符。
- **人改稿写回路径（review major 修补）**：`--from-file PATH` 把外置编辑后的正文作为 accepted 副本来源（`parent_version_id` 仍指向被确认的原工作稿，diff 可算——人改率代理 S5 可观测）；不传 `--from-file` 则确认 `current_version_id` 现稿。M4 不设独立「写回」命令——accept 是唯一章级正文写径。
- 前置校验：目标章存在 `current_version_id`；重复 accept（已 accepted）→ exit 2 幂等提示。

#### B3. accepted 游标唯一写径；与 `run` 并存（P0-2, N7 分列）

- 章级 accepted 写径收口到**单一服务函数**（M4 新建，`chapter accept` 与（未来）其他作者路径共用）；`run` 管线内既有 accept 写径不动（属引擎路径）。短理由（对调研 P0-2 建议答案的知情偏离）：run 的 accept 是管线内 human_confirm 语义，强行与作者路径共用一个服务函数会把 M4 变更耦合进已验收的 M0–M3 管线；只要保证「M4 不新增第二条**自动** accepted 写径」，两条人/引擎写径分立是可辩护的——评审应拒的是分叉出第二个**作者路径**写径。
- `run --auto-confirm` 定位不变：引擎 / 冒烟 / 长窗实验，不是作者路径，不因为它存在就放宽 M4 的确认闸。
- **验收分列句（照抄进 §6）**：M4 的「无自动 `approved`」指 **Canon（`plan_*` approved）无任何自动写径**；`import replay` 的自动 **chapter `accepted`**（`import_replay_service.py:498-560`）是历史路径，与本验收口径分列，不在「无自动 accepted」约束的否定面——M4 不新增第二条自动 accepted 写径。

#### B4. `--count N` = 逐章过确认闸（P0-3）

- `continue --count N` 是**批命令次数**，不是跳过确认：每章生成/抽卡完毕即停，打印「`chapter accept --chapter X` 后继续」；未 accept 不推进游标。
- 「无审连跑」由结构消灭（每章必须 accept）；`--count` 上限 3 仅是防误敲的参数上限，不是质量机制（PRD :435 默认 1 章锚点）。

#### B5. `chapter accept` 与 settlement 拆开（P0-6）

- accept 事务内**仅此两件事**：`ChapterVersion` 追加 `version_type='accepted'` 副本（只追加；`parent_version_id` 指向被确认稿）+ `chapter_heads` 更新：`accepted_version_id` 与 **`current_version_id` 一并指向该副本**、`status='accepted'`（工作指针与完成事实一致；此后若再改，走新 draft 版本再 accept）。**不**调用 SettlementExtractor，**不**写结算库，**不**产生 pending 提案。
- settlement 提取属**审后步骤**：发生在下一次 `continue` 的准备阶段（对上一章 accepted 稿跑既有 SettlementExtractor 语义：结算观测层 + `plan_*` pending 提案；人确认仍走 `canon confirm`，M2 语义不变）。「该章是否已 settlement」的判定以实现锁定（查结算库该章有无 settlement 记录），测试钉死——防止重复提取。`review` 若在 settlement 之前跑，看到的是上一章的既有信号，不触发提取。
- 短理由：PRD §4.2 目标语义即 `… → in_review → needs_settlement → settled`（结算在审后）；run 管线把 accept 与 settlement apply 绑在一个事务是 auto 路径的历史耦合，不复制进作者确认。

#### B6. 上一章上下文 = 正文结尾节选 + 120 字摘要（写死句 S3，量化在此钉死）

- continue 的上下文包在既有 Context Diet 组装上增加一段「上一章衔接」：**accepted 正文结尾节选，硬顶 800 字** + 既有 120 字 `plot_summary` 摘要（两者并存，不互相替代）。
- **计入口径**：节选是 context 包的一个组成段，**计入 `budget_used`**（与圣经、brief 同口径）；`run` 管线的既有 120 字路径行为不变。
- **超预算降级**：不新增机制——按 Context Diet 既有管线走（先到 `emergency_trigger_ratio` 即触发 ContextEmergency 裁剪；这与 PRD :442「单章仍超限则减少注入，而不是加长连跑」一致）。
- 被确认稿若事后被 `canon confirm --hard/--mark-stale` 标 `content_stale`（M2 语义），下一章 continue **不自动重写**（PRD：系统不自动改正文），但 `today` / `review` 可见该标记。

#### B7. `--variants N` 转调 M3（写死句 S2, P0-5）

- `continue --variants N` = 同进程函数级调用 `generate_chapter_variants`（M3 语义原样：默认 N=2、不 auto-pick、指纹、费用）；**不内嵌**第二套生成逻辑。
- 转调后的 pick / abandon 仍由人显式调 M3 `variant pick|abandon`；continue 不包它们。
- stale 规则沿用 M3：`stale_vs_canon=1` 的槽不可默认 pick（`--allow-stale` 语义不变）；continue 不另造 stale 口径。

#### B8. `review` 纯只读零写库（写死句 S4, N3, P1-4）

- 输入并集（PRD :485）：`check` 的问题（`run_plan_fact_gate`，现算——只读）∪ 最新三审报告（`load_latest_audits` / `ReviewReportRepository`，读已落库）∪ `literary_observations` ∪ 复读 / 专名启发式（新纯代码检查器，现算）∪ variant 备注（stale / 费用 / 槽状态，只读）∪ **人的 mark**（现网 mark 命令族的落库记录，只读取，不含写入）。
- **默认不调 `merge_reviews`**（其写 `review_reports` 的副作用违反本决策）；需要合并呈现时在 review 进程内做内存合并。
- 写库断言进测试：review 运行前后，`plan_*` / `review_reports` / `literary_observations` / `chapter_*` 各表行数不变。

#### B9. continue 挂 run 壳；中断可恢复（P1-6）

- continue 建/复用 `project_runs` 壳（`_find_resume_run` 语义）：中断（Ctrl-C / 异常 / LLM 熔断暂停）后再次 `continue` 可恢复未完成章；同章重跑幂等（只追加版本，不覆盖）。
- 中断恢复不绕过确认闸：恢复后仍须 `chapter accept` 才推进。

#### B10. `status` 命令分工（Q4 拍板，owner 三轮评审）

- `songyan status --project-id TEXT [--json]`：本会话计数面（PRD §9.2「today 是下一步，status 是本会话计数」）；其中一段 = ContextEmergency 触发次数 / 最近触发章 / `budget_used_before`（读 `context_snapshots`，经新增查询方法）。
- **`chapter status` 本里程碑不做**；若未来做，只读章进度，**不承载** ContextEmergency。此分工一句话进文档与帮助文案。

#### B11. exit 码表（P1-1）

| 命令 | 0 | 1 | 2 | 3 |
|------|---|---|---|---|
| `chapter continue` | 章已生成待确认 | 缺库 / 缺项目 / 参数非法（含 `--count >3`） | 业务拒绝：上一章 picked 未 accept、`--require-plan` 拒绝、目标章状态非法 | 预算耗尽（已写草稿保留） |
| `chapter accept` | 已确认 | 缺库 / 缺项目 / 参数非法 | 无可确认稿 / 重复 accept | — |
| `review` | 报告输出（含发现问题） | 缺库 / 缺项目 / 参数非法 | 指定章不存在 | — |
| `status` | 输出 | 缺库 / 缺项目 | — | — |

- 与 `check` 的 exit 2（未过门）**不同命令各表各义**，不在本文合并 `check` 语义；`review` 发现问题仍 exit 0（报告即产出）。

#### B12. `--require-plan`：默认警告，旗标拒绝（P1-3）

- 判定：本章 approved 圣经为空或缺 `chapter_goal`（实现锁定的具体判定，测试钉死）。
- 默认：警告文案明示缺哪类硬约束，**继续执行**（exit 0）。
- `--require-plan`：拒绝执行，exit 2，stderr 指明缺失项。

---

## 4. 接口

### 4.1 命令（增量）

```text
songyan chapter continue --project-id TEXT [--count 1] [--variants N]
                         [--require-plan] [--json]
songyan chapter accept   --project-id TEXT --chapter INT [--json]
songyan review           --project-id TEXT [--chapter INT] [--json]
songyan status           --project-id TEXT [--json]
```

- `chapter` 组在 M3 不存在于命令树（M3 只有 `variant` 组）；`chapter accept|continue` 随步注册，无空桩。
- 退出码按 B11；`--json` 结构化输出供脚本消费（continue 含 cost 字段，P1-2）。

### 4.2 `chapter continue` 语义

1. 恢复检查：有未完成 run 壳 → 续跑该章（B9）；否则目标章 = 范围内第一个非 accepted 章（B1 口径）。
2. 目标章前若存在 picked 未 accept 的章 → exit 2 并提示先 `chapter accept`（B1）。
3. 准备阶段：上一章若刚 accepted 且未 settlement → 跑 SettlementExtractor（B5；写结算观测层 + pending 提案）。
4. `--require-plan` 检查（B12）。
5. `--variants N` → 转调 M3 generate（B7）；否则单章初稿：组装上下文（B6 衔接段 + 圣经 + brief）→ `call_llm(role="writer")` → 追加 `version_type='draft'` 版本 + head 工作指针指向它。
6. 输出：本章草稿位置、字数、费用、下一步提示（`chapter accept` 或 `variant pick`）；不推进 accepted 游标。
7. 全程：`plan_*` 的 **approved 行集合不变**（settlement 产生的 `pending` 提案属 M2 既有语义，是合法变化，断言只锁 approved 集）；无自动 accept；中断挂 run 壳。

### 4.3 `chapter accept` 语义

1. 前置：目标章有 `current_version_id`；已 accepted → exit 2 幂等提示（B2）。
2. 事务：追加 `version_type='accepted'` 副本（只追加）+ head 双指针更新（B5，事务内仅此）。
3. **不**跑 settlement（B5）；**不**动 `plan_*` / variant 行 / `content_stale`。
4. 输出：被确认 version_id、章号、字数；`--json` 含同字段。

### 4.4 `review` 语义

1. 按章聚合（默认最近一章，可 `--chapter`）：gate 现算报告 + 最新三审（读库）+ literary_observations + 复读/专名启发式 + variant 备注（B8 输入并集）。
2. 内存合并呈现：markdown（默认）/ `--json`；问题按严重度分组、带证据引用（沿用 `ReviewIssue.evidence_quote` 纪律）。
3. 全程零写库（B8 测试断言）；发现问题仍 exit 0（B11）。

### 4.5 `status` 语义

1. 读 `context_snapshots`（新增按 project/chapter 查询）：ContextEmergency 触发次数、最近触发章、`budget_used_before`（B10）。
2. 同面放项目级计数（章进度数 / 未确认 picked 数）——口径说明：PRD §9.2「本会话计数」在 CLI 无会话概念下按**项目维度**解释（`--project-id` 范围内计数）；保持薄。
3. 纯只读。

### 4.6 模块边界

| 文件 | 责任 |
|------|------|
| `services/chapter_continue.py`（新） | 目标章判定、准备（settlement 触发）、上下文组装（B6）、编排 |
| `services/chapter_accept.py`（新） | accepted 写径唯一服务函数（B3/B5 事务） |
| `services/review_report.py`（新） | review 只读聚合（B8） |
| `plan_checks/` 新检查器 | 复读 / 专名启发式（移植 evals 算法） |
| `db/repository.py` 窄扩建 | `ContextSnapshotRepository` 按 project/chapter 查询 |
| `cli/commands/chapter.py` / `review.py` / `status.py`（新） | 命令面 |
| `workbench.py` | `today` 用章进度视图 + M4 next 文案 |
| `models/` | 章进度视图 / review 报告模型 |
| `tests/cli/test_chapter_*.py`、`tests/cli/test_review*.py`、`tests/services/test_*` | CliRunner / 服务级；生成可 mock；验收测试按 §6 |

### 4.7 本里程碑不做的命令表面

- 不注册 `chapter status`、`branch`、`continue` 之外的 `chapter` 子命令空桩。
- 不注册「打印未实现」空桩。

---

## 5. 小步

每步一个可独立拒绝的提交；合并前跑 §7 命令。顺序固定：**步 2 在步 3 前**（continue 的确认闸依赖 accept 写径）。

### 步 1 — 章进度视图 + `status`（task 238）

**产出：** 章进度视图纯函数（B1 推导，可判定子集）；`ContextSnapshotRepository` 按章查询；`songyan status`（B10）；`today` 接入视图（next 文案 M4 口径可留到步 5）。
**测试：** 视图推导各态锁死；status 输出字段锁死；纯只读断言。

### 步 2 — `chapter accept`（task 239）

**产出：** accepted 写径唯一服务函数 + `songyan chapter accept`（B2/B3/B5）。
**测试：** TDD 先红——picked→accept 事务锁死；**accept 后结算库零新行**（B5 拆开锁死）；`plan_*` 前后快照不变；重复 accept exit 2。

### 步 3 — `chapter continue`（task 240）

**产出：** continue 编排（B1 判定 / B4 逐章确认 / B6 衔接段 / B7 转调 / B9 run 壳 / B12 require-plan）+ 命令注册。
**测试：** N2 拒绝路径（picked 未 accept → exit 2）；`--count 3` 逐章停闸；`--variants 2` 转调语义（plan_* 不变、不 auto-pick）；中断恢复幂等；费用字段非空。

### 步 4 — `review`（task 241）

**产出：** 只读聚合（B8）+ 复读/专名启发式检查器。
**测试：** 输入并集各源聚合计数锁死；**全表行数前后不变**；不调用 `merge_reviews`（mock 断言）；exit 码按 B11。

### 步 5 — 收口与验收（task 242）

**产出：** `today` next 文案 M4 口径；§6 验收清单全跑；STATUS/HANDOFF 记步次。
**测试：** 3 章 W2 连走验收脚本（mock 模型）：无任何自动 approved；review 测试 approved 行数不变（PRD :501）。

---

## 6. 验收

最小验收表面（硬门）：

1. **W2 短环走通：** 连续 3 章「continue → 人改（可省）→ accept → continue」，mock 模型可验；全程 `plan_*` approved 行数**零变化**（无自动 Canon `approved`——B3 分列句：import replay 的自动 chapter accepted 属历史路径，不在此口径的否定面）。
2. **`chapter accept` 干净：** accept 事务内只动版本 + 游标；结算库无新行（B5）。
3. **无审不连跑：** 未 accept 的章，continue 不推进（exit 2 提示）；`--count N` 逐章停闸。
4. **`review` 只读：** 运行前后全部相关表行数不变；approved 行数不变（PRD :501）。
5. **`status` 露出：** ContextEmergency 次数 / 最近触发章可读（PRD :442）。
6. **`today` 可作答：** 只看 `today` 能说出下一章该做什么（PRD :448）。
7. **exit 码表（B11）逐项锁死**；`--require-plan` 拒绝路径锁死。
8. `ruff check src/ tests/` 过；本里程碑 CLI / 服务测试过；M0–M3 回归过（文案有意更新在提交说明写明）。

S 指标产品周期统计不挡代码验收，以本节命令级清单为准。真实模型冒烟另开维护者任务，不挡本节硬门。

---

## 7. 验证命令

```bash
ruff check src/ tests/
python -m pytest tests/db/test_plan_fact_cards.py tests/plan_checks/ -q
python -m pytest tests/cli/test_workbench_commands.py tests/cli/test_variant_pick_abandon.py -q
# 步 2 后追加：
python -m pytest tests/cli/test_chapter_accept.py -q
# 步 3 后追加：
python -m pytest tests/cli/test_chapter_continue.py -q
# 步 4 后追加：
python -m pytest tests/cli/test_review*.py tests/plan_checks/test_repetition*.py -q
```

每步合并前跑全量 `python -m pytest tests/ -q`（本机已无需 `PYTHONUTF8=1`，task 235 修复后零失败基线）。`tests/cli` 不在默认收集，改 CLI 必单独跑。

---

## 8. 风险

| 风险 | 处理 |
|------|------|
| 把 `resume_human_confirm` 当 CLI 确认闸复用 | B2：新 `chapter accept`；评审应拒「复用 thread resume 做作者确认」的实现 |
| settlement 溜进 accept 事务 | B5 + 「accept 后结算库零新行」测试锁死 |
| picked / accepted 双口径判定下一章 | B1：严格 accepted 唯一口径；N2 拒绝路径测试 |
| `--count N` 变相无审连跑 | B4：逐章停闸结构保证；N>3 拒绝 |
| `--variants` 内嵌第二套生成逻辑 | B7：函数级转调 M3 |
| review 误调 `merge_reviews` 写库 | B8：mock 断言 + 行数不变断言 |
| 正文节选撑爆上下文预算 | B6：计入 budget_used、走既有 emergency 管线、硬顶 800 字 |
| accept 写径分叉（第二服务函数） | B3：唯一服务函数；代码评审查重 |
| exit 码与 `check` 语义混淆 | B11：各命令各表；review 发现问题 exit 0 |
| 范围膨胀（自动选优 / 文学判定 / 无人值守） | 停；改 PRD 并另审 |
| 包版本或 V1.0 完成话术 | 禁止 |

题材无关性：命令里不出现「若题材是 X 则……」分支；都市灵异仍是夹具标签。

---

## 9. 以后的技术方案

本文若被接受并完成 M4 之后，才轮到：

- 真实模型冒烟与「导入后再续写」验收（维护者任务）
- `chapter status`（若做：只读章进度，不承载 ContextEmergency——B10 分工句）
- `review --deep`（显式 LLM 深审，成本前置提示）
- 故事线纳入 fingerprint / 人几乎不改就标 settled 的警告（S5 产品向）

那些属于后续修订各自的文档。本文不写其实现步骤。

---

## 接受注记

**待接受**（草稿，2026-11-08 Asia/Shanghai）。接受需 owner 书面拍板（对照 tech-m3 先例：widget 编号 + 「接受 tech-m4，按 B1–B12 开 M4 编码」）。**B1–B12 原样接受**或点名修改项；接受前不对编码产生约束力。

接受后按 §5 小步推进（task 238–242）。包仍 `0.5.0`；不声称 V1.0 完成。
