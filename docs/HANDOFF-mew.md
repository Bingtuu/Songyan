# Handoff：当前下一步

owner：Bingtuu。包 tip **v0.5**（`0.5.0`）。「V1.0」是产品代际名，不是包版本。本文件不打 tag。

权威顺序见 [AGENTS.md](../AGENTS.md)：[PRD](prd-v1.md) → [M0 技术方案](tech-m0.md) → [M1 技术方案](tech-m1.md)（**已接受**；§6–7 **PASS**）→ [M2 技术方案](tech-m2.md)（**已接受**；§6–7 **PASS** @ `f1c3093`）→ [M3 技术方案](tech-m3.md)（**已接受**；t104s937；B1–B7 原样；§6–7 **PASS** @ `594144b`）→ [M4 技术方案](tech-m4.md)（**已接受**；2026-11-08；B1–B12 原样；§6–7 **PASS** @ `e5a33bd`）→ [tech-m4-followup](tech-m4-followup.md)（§9 后续三项，已接受；248–250 闭环）→ [tech-m4-followup-s5](tech-m4-followup-s5.md)（S5 产品向，已接受；252/253 闭环）→ [tech-roadmap-post-m4](tech-roadmap-post-m4.md) + [tech-post-m4](tech-post-m4.md)（post-M4 路线，已接受；A/C/B 闭环 255–257）→ ADR-0001 → STATUS（事实）→ 本文件（当天）→ `tasks/`（有任务文档之后）。

## 下一刀

**270 已 DONE 归档（2026-11-15，goal loop 交付，代码 @ `510f79b`）**：修复抽取提案 `attribute_id` 碰撞静默覆盖——

- 碰撞向量（修复前全部 last-writer-wins，人在 `canon pending` 看不到被覆盖的提案）：同 settlement 同 (entity, key, chapter) 多次观测；`character_updates.field` × `numerical_updates.attribute_name` 跨族同 key（真实词表两边都有 `level`）；非 ASCII key/entity 经 `_slug` 塌缩成 `x`。
- 修复（`_proposals.py`）：写入携带本次调用 `seen` 表；同 ID 同值 → 幂等跳过（重跑不重复）；ASCII base ID 被不同 value 占用 → 升级「base + entity/key/value 短哈希」ID 并记 `extract_proposal_disambiguated` 日志；entity/key 含非 ASCII → 恒走哈希 ID。哈希含 value，重跑幂等。
- 兼容性：无碰撞 ASCII 正常路径 ID 逐字不变（有锁测试）；approved/rejected 跳过语义不变（task 226）；settlement 表仍是 `untrusted_until_confirmed` 观测源，原始观测可回溯。
- 测试：`tests/settlement_extractor/test_extract_proposal_collisions.py` 5 测（两值并存 / 同值幂等 / 跨族并存 / 中文 key 不塌缩 / ASCII ID 形态锁）。回归：tests/cli 371 全绿；ruff 零告警；全量默认收集见 STATUS。

**266–269 批次已 DONE 归档（2026-11-15，goal loop 交付）**——都市灵异清模板与 pending/伏笔过目（依据 `.tmp/266-269-都市灵异清模板与pending过目.md`）：

- **266 角色/设定编辑 CLI**（`8181771`）：`character|setting list|edit|remove`；软删（characters.archived / setting lifecycle=archived）+ 审计 `profile_edit_history` 同事务；软删行从默认 list 与组装/名册/初始化出口消失；主角禁 remove（exit 2）；edit 命中软删行=复活（storyline 同口径）。urban 新项目全 CLI 清场验收测试过。
- **267 未出场模板反派衰减**（`864d3c3`）：0 states 且从未出场的 antagonist 只给符号档案（importance 0.2），不占硬顶不保送 0.8；已出场/有 states 保护不变，protagonist 不变。
- **268 --no-seed + urban_horror**（`74802be`）：`create-project --no-seed` 只建主角档案；都市灵异薄模板无 seed.json。doctor 实认 8 templates。
- **269 pending 分组 + 伏笔 horizon + 承诺归档**（`591a285`）：`canon pending --chapter/--source/--kind`（entity 经引用归组）+ `confirm/dismiss batch` 同族过滤（非 TTY 无 --yes exit 2）；urban `foreshadowing_horizon_floor=8`；`canon dismiss promise` 归档（幂等，出开放集/overdue/紧迫）+ `canon confirm promise-due`（人确认到期日，未确认 expected 只是建议：不翻 overdue、不加 +2 紧迫）。
- 回归：默认收集 3689 passed / 2 skipped / 1 xpassed（基线 3663 + 本批新增/口径更新）；tests/cli 371 全绿（基线 339）；ruff 零告警。**升级提醒：旧库先 `songyan doctor --init-db`**（characters.archived / foreshadowings.confirmed_due_chapter 窄加列，既有契约；2 条钉旧口径的测试已随口径更新改写）。

**下一刀（均需 owner 侧动作，助手默认待命）**：① owner 真人 dogfood 写一章（266–269 的实模型验收输入，建议都市灵异 urban_horror 起步）；② ~~选项 A~~ **已拍板不做（2026-11-15，owner 确认）**——B（265 定向注入）已消除裸奔，A 的残余价值只剩章节级 target_events/hooks 自动规划，与「人主导 + B12 轻量短环」相悖且每章 +¥0.02–0.05；③ ~~实模型抽检 1–2 章看是否再漏模板~~ **271 已 DONE（2026-11-27）**：urban_horror / urban 两模板原生开书抽检 PASS 不漏不串（¥0.0628），265 story_brief 注入与 267 反派衰减实模型实锤。未建任务文件，不口头开工。

**task 265 已 DONE 归档（2026-11-15）**：context 断链修复（owner 拍板选项 B）——writer 卡 1.1.2 注入故事定向（story_brief/角色名册/世界观设定，断链 C2/C3/C4）；`chapter continue` 四路定向全空可见提醒（`orientation_notice`，不越 B12）；`storyline edit outline --core-hook/--protagonist-background`（C5）；抽卡字数门 `quality_flag=short`（F9）；`--title` 回显（F3）。代码 @ `43eca48`；dogfood 复测 PASS（`.tmp/dogfood-265-末班电梯-003233/`：纯 CLI storyline、零 canon 预置，ch1 2726 字 ¥0.0245 恐怖要素全命中零泄漏）；回归：默认收集 3663 passed，tests/cli 339 全绿，ruff 零告警。评估文档：[docs/experiments/265-context-disconnect-eval.md](experiments/265-context-disconnect-eval.md)；归档：[tasks/done/265](../tasks/done/265-context-disconnect.md)。

**task 244 已 DONE 归档（2026-11-11）**：真实模型冒烟发现 5/6 两个 P1 修复，代码 @ `120012c`，切片 5 真实模型复验 PASS（`.tmp/smoke-244-verify-20261111/`：pick→accept 后 continue exit 0；圣经 text_len 0→1664；抽卡两槽真实正文 1602/2075 字；canon confirm 后 stale_vs_canon=1；费用 ¥0.4823 / 24 次调用）。归档：[tasks/done/244](../tasks/done/244-修复抽卡死锁与圣经空渲染.md)。

**task 245 已 DONE 归档（2026-11-12）**：变体拒写质量门（owner 拍板 P1–P3）——判定纯函数 + 同槽重试 1 次 + `quality_flag` 打标 + 全败 exit 2；代码 @ `8c26105`；真实模型复验 ¥0.3491（`.tmp/smoke-245-verify-20261112/`）。归档：[tasks/done/245](../tasks/done/245-变体拒写判失败与重试策略.md)。

**task 246 已 DONE 归档（2026-11-12）**：db-maintenance 锁表根因 = `get_db()` 的 `PRAGMA quick_check` 未消费结果悬挂持锁（4 轮实验链实锤：插桩→sync 探针→最小复现→单变量二分）；修复后真实 run 收尾 0 告警、WAL 截断 0 字节（¥0.4203），全量 3623 passed。归档：[tasks/done/246](../tasks/done/246-修复run收尾db-maintenance锁表失败.md)。

M0 步 1–4 已全部在 `main`：[#28](https://github.com/Bingtuu/Songyan/pull/28) → `1d8c0c0`；[#29](https://github.com/Bingtuu/Songyan/pull/29) → `8f03453`；[#30](https://github.com/Bingtuu/Songyan/pull/30) → `d5c2cc1`；[#31](https://github.com/Bingtuu/Songyan/pull/31) → `48fa354`。任务分别在 [tasks/done/200.md](../tasks/done/200.md)、[tasks/done/201.md](../tasks/done/201.md)、[tasks/done/202.md](../tasks/done/202.md)、[tasks/done/203.md](../tasks/done/203.md)。

M0 代码验收（步 1–4 + tech-m0 §6–7）在 `main` `80f4107`：**PASS**。归档说明：[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md)。S6 不在代码验收内。

M1 步 1–5 已在 `main`：[#35](https://github.com/Bingtuu/Songyan/pull/35) → `1995181`；[#36](https://github.com/Bingtuu/Songyan/pull/36) → `5a260a9`；[#38](https://github.com/Bingtuu/Songyan/pull/38) → `7c7ec43`；[#39](https://github.com/Bingtuu/Songyan/pull/39) → `d3f127c`；[#41](https://github.com/Bingtuu/Songyan/pull/41) → `69d7ece`。任务分别在 [tasks/done/205-rejected迁移与过滤.md](../tasks/done/205-rejected迁移与过滤.md)、[tasks/done/206-canon-edit.md](../tasks/done/206-canon-edit.md)、[tasks/done/207-confirm-dismiss.md](../tasks/done/207-confirm-dismiss.md)、[tasks/done/208-check.md](../tasks/done/208-check.md)、[tasks/done/209-w0-today-e2e.md](../tasks/done/209-w0-today-e2e.md)。

M1 代码验收（步 1–5 + tech-m1 §6–7）在 `main` `69d7ece`：**PASS**。归档说明：[tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md)。S1/S2 产品周期日志不在代码验收内。

不要做的事：

- 不再开 `settlement_review` 修复刀。`11c4c761` / #19 的 Ch1–3 fail 留着；`eaa6bef` / #20 的重跑已 PASS。
- 不重开 plan-first 阶段 C，不加题材专用检查器，不改 SettlementExtractor 的权威。
- 不把 Ch1–10 写成文学验收。文学质量归人。
- 正式 git tag 仍由维护者决定。
- **M0–M4 编码范围全部闭环**：不扩 M3（continue / review 已由 M4 交付）、不扩 M4（步 1–5 + §6–7 PASS @ `e5a33bd`，task 243）；结算表仍保留为 untrusted 对照，不升格 Canon。tech-m4 §9「以后」事项已由 followup 248–250 闭环（`chapter status` / `review --deep` / 导入后再续写验收），§9 清零。
- 不声称 V1.0 完成，不升包版本。

## 事实指针（短）

| 项 | 记录 |
|----|------|
| 产品规划 | [prd-v1.md](prd-v1.md)（文档已接受，#27 已进 main） |
| M0 步 1–4 | 已进 `main`（见上）；[tasks/done/200–203](../tasks/done/) |
| M0 验收 | **PASS** @ `80f4107`。[tasks/done/204-m0-acceptance.md](../tasks/done/204-m0-acceptance.md) |
| M1 技术方案 | [tech-m1.md](tech-m1.md) — **已接受**（Mew 拍板，2026-11-03 Asia/Shanghai）；§6–7 **PASS** @ `69d7ece` |
| M1 步 1–5 | 已合入（见上）；[tasks/done/205–209](../tasks/done/) |
| M1 验收 | **PASS** @ `69d7ece`。[tasks/done/210-m1-acceptance.md](../tasks/done/210-m1-acceptance.md) |
| M2 技术方案 | [tech-m2.md](tech-m2.md) — **已接受**（2026-11-04；t93s804；B1–B6 原样；[#43](https://github.com/Bingtuu/Songyan/pull/43) → `a95824a`） |
| M2 步 1 | 已合入 `8f7bc77`（#44）；[tasks/done/212-m2-step1-w5-readonly.md](../tasks/done/212-m2-step1-w5-readonly.md) |
| M2 步 2 | 已合入 `8afb7be`（#46）；[tasks/done/213-m2-step2-confirm-settle.md](../tasks/done/213-m2-step2-confirm-settle.md) |
| M2 步 3 | 已合入 `2ac1093`（#48）；[tasks/done/214-m2-step3-content-stale-hard.md](../tasks/done/214-m2-step3-content-stale-hard.md) |
| M2 步 4 | 已合入 `5a6e923`（#50）；[tasks/done/215-m2-step4-check-stale-report.md](../tasks/done/215-m2-step4-check-stale-report.md) |
| M2 步 5 | 已合入 `2fa8209`（#52）；[tasks/done/216-m2-step5-extract-pending.md](../tasks/done/216-m2-step5-extract-pending.md) |
| M2 步 6 | 已合入 `f1c3093`（#53）；[tasks/done/217-m2-step6-docs-copy.md](../tasks/done/217-m2-step6-docs-copy.md) |
| M2 验收 | **PASS** @ 证据 tip `f1c3093`。[tasks/done/218-m2-acceptance.md](../tasks/done/218-m2-acceptance.md) |
| M3 技术方案 | [tech-m3.md](tech-m3.md) — **已接受**（2026-11-06；t104s937；B1–B7 原样）；草稿任务 [tasks/done/219-tech-m3草稿.md](../tasks/done/219-tech-m3草稿.md) |
| M3 步 1 | 已合入 `b9bbf98`（#56）；[tasks/done/220-m3-step1-variants-table.md](../tasks/done/220-m3-step1-variants-table.md) |
| M3 步 2 | 已合入 `135fcfb`（#57）；[tasks/done/221-m3-step2-variant-generate.md](../tasks/done/221-m3-step2-variant-generate.md) |
| M3 步 3 | 已合入 `0b47410`（#58）；[tasks/done/222-m3-step3-variant-list-diff.md](../tasks/done/222-m3-step3-variant-list-diff.md) |
| M3 步 4 | 已合入 `c38ee31`（#59）；[tasks/done/223-m3-step4-variant-pick-abandon.md](../tasks/done/223-m3-step4-variant-pick-abandon.md) |
| M3 步 5 | 已合入 `1b0e323`（#60）；[tasks/done/224-m3-step5-stale-cost.md](../tasks/done/224-m3-step5-stale-cost.md) |
| M3 §6–7 验收 | **PASS** @ `594144b`（task 234）；步 6 = task 233 |
| M4 技术方案 | [tech-m4.md](tech-m4.md) — **已接受**（2026-11-08；owner 拍板「按 B1–B12 开 M4 编码」；B1–B12 原样）；调研底稿 [docs/236-m4-preresearch.md](236-m4-preresearch.md) |
| M4 步 1 | 已提交 `c55a714`（章进度视图 + `status`）；[tasks/done/238-m4-step1-progress-status.md](../tasks/done/238-m4-step1-progress-status.md) |
| M4 步 2 | 已提交 `f205f8a`（`chapter accept`）；[tasks/done/239-m4-step2-chapter-accept.md](../tasks/done/239-m4-step2-chapter-accept.md) |
| M4 步 3 | 已提交 `23bd3f3`（`chapter continue`）；[tasks/done/240-m4-step3-chapter-continue.md](../tasks/done/240-m4-step3-chapter-continue.md) |
| M4 步 4 | 已提交 `b857e8b`（`review` 只读共审）；[tasks/done/241-m4-step4-review.md](../tasks/done/241-m4-step4-review.md) |
| M4 步 5 + §6–7 验收 | 步 5 已提交 `e5a33bd`（W2 连走集成测试 + `today` M4 文案）；**§6–7 PASS @ `e5a33bd`**（[tasks/done/242-m4-step5-closure.md](../tasks/done/242-m4-step5-closure.md) · [tasks/done/243-m4-code-acceptance.md](../tasks/done/243-m4-code-acceptance.md)） |
| 当前任务 | 无进行中。**271 实模型抽检 DONE 已归档**（两模板原生开书不漏不串 ¥0.0628）；此前 270 extract 碰撞修复已归档。待 owner：真人 dogfood 写一章（266–269 实模型验收） |
| 架构方向 | [adr/0001-plan-first-facts.md](adr/0001-plan-first-facts.md) |
| 工程现状 | [STATUS.md](STATUS.md) |
| 阶段 A–C | [ROADMAP-plan-first.md](ROADMAP-plan-first.md)（CLOSED 短指针；全文在 archive，日常不要加载） |

**Ch1–3 发布冒烟：** `eaa6bef` PASS（`run-552b2c04`，scifi《轨道蜃景》）。Box（不入库）：`/workspace/songyan-release-smoke-out-rerun20/notes.md`、`smoke_result.json`。

**Ch1–10（2026-10-26）：流水线过，文学不过。** main `47954cb`。scifi《轨道蜃景》，`project_id=8e30dec7f2ec40c1a9ce54c783981f8c`，`run-33841231`。10/10 accepted；QG / settlement / summary / export 通过；exit 0。**DG-1 失败**（平均 revision 1.7；ContextEmergency 10/10，无 AutoHalt）。文学不及格：时间线回滚、Hermes/赫耳墨斯、时间尺度、供氧/EVA 复读、`ninety-two 秒`。只作 smoke / 回归证据。Box（不入库）：`/workspace/songyan-ch1-10-out/` 下 `notes.md`、`result.json`、`reports/report-run-33841231.md`、`exports/轨道蜃景-flat.md`、`quality-read.md`。

## 怎么报告

一刀结束用短记录：分支与 PR、改了哪些文件、测试结果、明确没做的事、下一刀只推荐一件。
