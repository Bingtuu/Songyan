# V10 Task 总索引

> **阶段**: 跨体裁 Ch200 + 优秀度信号包 + 结构升级 spike
> **定位**: V10 不是开源交付体验阶段，而是工程版 1.0 前的质量与长度再验证阶段：证明多体裁长窗口仍稳定，并把“好不好看/是否有 AI 腔/是否同质化”从主观讨论推进到可复核信号。
> **当前口径**: V9 已全量闭环；V10 规划入口已建立，Task 189 已完成 sci-fi Ch200 baseline/checkpoint 冻结，Task 190 已完成 Ch100 终点事实源盘点，Task 191 已完成 Ch200 harness 准备；Task 192/193/194 正式任务书已建立。Task 192 xuanhuan Ch200 已完成，含 192.p/q/r/s/t/u/v/w/x/y/z/aa/ab/ac/ad/ae/af/ag/ah/ai/aj/ak/al/am/an/ao/ap/aq/ar/as/at/au/av/aw 均已完成；xuanhuan Ch200 accepted/current head=`v-5659d486`，run completed_count=200、failed=[]；five-gate @200 PASS、segment audit PASS、T9=0；当前按编号推进 Task 193：wuxia Ch28 deterministic clean/source 初始化已完成，193.p/q/r/s/t/u/v/w 全部完成（根因治理线 193.s→v→t 收口：词条匹配修复诊断 8 章捕获 7/8、overdue actionable 口径；评测口径线 193.r/u/w 收口：暂停区分、schema drift、段审计 verdict/stale 防护）；wuxia 已推进到 Ch125 accepted，Ch125 段边界审计 five-gate/segment/T9 全 PASS；下一步 Ch126→Ch150 后执行 Ch150 段审计。V10 不再补 V9 生产化地基，也不做 V11 的外部用户可用化收尾。
> **任务编号**: V10 预计从 Task 189 开始；本文不占任务号。只有可独立执行、独立验收、独立出 DONE 文档的工作项才编号；撞墙修复继续按父任务字母后缀登记（如 `192.p`）。
> **状态**: ◐ V10.2 Task 193 wuxia Ch200 climb 进行中（Task 189/190/191/192 ✅；Task 193 已到 Ch125 accepted、Ch125 段审计 five-gate/segment/T9 全 PASS，193.p/q/r/s/t/u/v/w ✅；下一步 Ch126→Ch150；尚未完成 wuxia/urban Ch200 长跑）

本文是 V10 阶段任务规划入口。V9 历史事实入口见 `tasks/V9-README.md`，V9 单项任务归档见 `archive/v9/INDEX.md`。

---

## 一句话目标

> **V10 要回答两个问题：多体裁从 Ch100 拉到 Ch200 后是否仍然稳定；生成结果是否不只“一致”，还开始具备可度量的优秀度。**

---

## 背景判断

V9 已经完成三件关键前置：

- 生产化地基补齐：日志、导出、wheel、CI、doctor、成本追踪、预算熔断、五门/段审计工具、Profile CLI、schema 校验均已闭环。
- 三个非 sci-fi 体裁 Ch100 已验证：xuanhuan、wuxia、urban 均达到 100/100 accepted，五门 PASS。
- urban Ch100 作为第三体裁实战验收通过，证明 V9 地基可承受长窗口真实 LLM 运行。

V10 因此不应继续做“地基补洞”。它的主线应转向：

1. **长度再验证**：从 Ch100 扩到 Ch200，验证多体裁长窗口稳定性。
2. **质量再定义**：在 CED/T9/health/overdue 之外，补一组 report/observe 级优秀度信号。
3. **结构升级判断**：对 KG diff、validity interval、Storyline Tree 做 spike，判断是否值得进入后续主线。

V10 有一条额外纪律：**Ch200 终判样本必须先保持生成链路稳定**。优秀度信号包在校准完成前只能基于既有 accepted 正文离线分析或 report/observe 输出，不得提前改变 Writer / CreativeDirector 的生成策略，避免把 Ch200 稳定性验证和质量信号实验混在一起。

---

## 阶段验收判定

V10 通过 = A 组（Ch200 口径与工具）+ B 组（跨体裁 Ch200）+ C 组（优秀度信号包）+ D 组（结构升级 spike）同时满足，E 组守护项全程不破。

### A 组 · Ch200 口径与工具

| # | 判据 |
|---|------|
| A1 | sci-fi Ch200 baseline 以正式工具重放，形成 Ch125 / Ch150 / Ch175 / Ch200 checkpoint 基线。 |
| A2 | five-gate 与 segment audit 支持 Ch200 checkpoint，不改变预算/CED/overdue/health/completeness 判定函数。 |
| A3 | Ch100 → Ch200 的 continuation 策略明确：每个体裁先确认 clean Ch100 事实源；若不可复用，必须重建 clean Ch100 起点。 |
| A4 | Ch200 harness 固定 DB 路径、run_id、成本预算、wrapper marker、报告落盘路径，避免外部 `DATABASE_URL` 污染终判样本。 |
| A5 | V10 证据目录与归档口径明确：活动任务仍在 `tasks/`，完成后归档到 `archive/v10/`；实跑证据路径、报告路径、DB 路径在任务书中固定。 |

### B 组 · 跨体裁 Ch200

V10 的硬目标建议是 xuanhuan / wuxia / urban 三个非 sci-fi 体裁均完成 Ch200。若成本或外部条件要求降级，必须在 V10 开工前明确最小通过集，不能在实跑失败后临时缩口。

每个体裁 Ch200 终判沿用冻结五门：

| # | 判据 |
|---|------|
| B1 | Ch1-Ch200 全 accepted；gap≤1 必须 documented-isolate 复核。 |
| B2 | `budget_used` 峰值 < 1.0；无 `context_emergency_budget_ratio_halt`。 |
| B3 | consistency CED ≤ sci-fi 同章尺度 × 1.15。 |
| B4 | overdue ≤ sci-fi 同章尺度。 |
| B5 | health ≥ 8.0（latest 非 None）。 |
| B6 | T9=0；不接受解释性豁免，机制修复后必须 clean rerun。 |

### C 组 · 优秀度信号包

优秀度信号包初始只做 report/observe，不作为自动 accept/reject 的硬门。V10 通过要求：

| # | 判据 |
|---|------|
| C1 | 优秀度信号与一致性 CED 明确分层，不把文学 craft、同质化或 AI 腔计入 CED。 |
| C2 | 至少覆盖：跨章同质化/多样性、叙事张力/节奏、中文 AI 腔、style extraction → style card、角色声纹锚点、perplexity/可读性可行性评估。 |
| C3 | 每个信号都有样本校准与误报记录；报告能解释命中证据，而不是只给分数。 |
| C4 | `songyan metrics` 或 `songyan report` 可展示优秀度视图，并能按章节/窗口定位问题。 |
| C5 | 优秀度信号包在 V10 内默认不改变生成链路；若任何任务要把信号注入 prompt 或 gate，必须单独立项并先完成 scifi/短窗口回归。 |

### D 组 · 结构升级 spike

V10 不把结构升级强行并入主流程。spike 的目标是形成取舍结论：

| 方向 | 目标 |
|------|------|
| KG 图 diff | 验证章级事实图 diff 是否能比现有 CED 更早发现结构性矛盾。 |
| FactTrack validity interval | 验证设定/状态有效期是否能降低“过期事实仍被引用”的误报/漏报。 |
| Storyline Tree | 验证主线/支线树是否能改善长程伏笔调度与弧级收束判断。 |

### E 组 · 守护项

- SQLite 仍是唯一长期事实源；LangGraph state 只存 ID。
- CED 继续使用 consistency-only、merged/source、正文证据口径。
- T9 仍是硬红线；PASS 样本必须 clean rerun 后 T9=0。
- 优秀度信号不覆盖、不替代、不污染五门判定。
- 任何运行时画像、上下文组装、prompt 注入、harness 或质量工具改动后，必须执行 scifi 短窗口回归；影响 Ch200 口径的改动还必须重放 sci-fi Ch200 baseline。
- 不新增核心 Agent / Workflow 节点，除非 V10 任务书明确批准并给出回归证据。
- 不做 UI、账号、后台服务、模板市场；这些不属于 V10。

---

## Task 拆解草案

> 编号是初稿。正式开工前应先评审本 README，再为第一个可执行任务补独立任务书。

### V10.1 Ch200 口径与工具

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 189 | Ch200 baseline 与 checkpoint 冻结 | ✅ | sci-fi Ch200 baseline 重放；形成 Ch125/150/175/200 对标表；明确 CED/overdue/health/T9 口径 | DONE：`tasks/189-ch200-baseline-and-checkpoints-DONE.md`；冻结 baseline：`tasks/189-scifi-ch200-baseline.json`；工具重放与 V7 报告一致 |
| 190 | Ch100 终点事实源盘点 | ✅ | 盘点 xuanhuan/wuxia/urban clean Ch100 DB、project_id、run_id、accepted head、T9 状态 | DONE：`tasks/190-ch100-terminal-source-inventory-DONE.md`；urban CONTINUE_READY，wuxia BLOCKED_DIRTY_SAMPLE（T9=1，需 Ch28 clean），xuanhuan REBUILD_REQUIRED |
| 191 | Ch200 harness 准备 | ✅ | 新增 `scripts/run_v10_ch200_climb.py`；固定 V10 DB/报告路径；接入 Task 190 三态准入、source clean Ch100 / inventory / genre / T9 校验、Task 189 baseline、dry-run/status/audit/init-from-source | DONE：`tasks/191-ch200-harness-preparation-DONE.md`；聚焦测试 10 passed；未启动 Ch101 |

### V10.2 跨体裁 Ch200 爬坡

> 192-194 的正式任务书已建立；Ch125+ five-gate 必须显式传入 Task 189 冻结的 Ch200 baseline：`tasks/189-scifi-ch200-baseline.json`。当前 goal 按编号推进仍从 Task 192 开始；各任务内部必须服从 Task 190 三态准入：xuanhuan 需先恢复/重建 clean Ch100，wuxia 需先 Ch28 clean，urban 可直接初始化。

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 192 | xuanhuan Ch200 爬坡 | ✅ | clean Ch100 source ready；Task 191 harness 初始化并推进到 Ch200；Ch125/150/175/200 全部完成；Ch200 accepted 200/200；five-gate @200 PASS、segment audit @200 PASS、T9=0 | DONE：`tasks/192-xuanhuan-ch200-climb-DONE.md`；执行报告：`docs/reports/192-xuanhuan-ch100-climb.md` |
| 192.p | scifi 短窗口 ContextEmergency 回归修复 | ✅ | 修复 Task 192 工具链改动后暴露的 scifi 短窗口回归失败；settlement 结构化输出预算提升到 8192；scifi end10 复跑 10/10 completed | DONE：`tasks/192.p-scifi-short-regression-context-emergency-DONE.md` |
| 192.q | xuanhuan Ch17 CreativeDirector JSON parse 修复 | ✅ | CreativeDirector 改为复用通用 JSON repair parser；Ch17 resume 成功 | DONE：`tasks/192.q-xuanhuan-ch17-creative-director-json-parse-DONE.md` |
| 192.r | xuanhuan Ch24 settlement numerical validation 处理 | ✅ | 冻结 Ch24 数值结算失败现场；resume 后 Ch24/25 成功，failed=[] | DONE：`tasks/192.r-xuanhuan-ch24-settlement-numerical-validation-DONE.md` |
| 192.s | xuanhuan Ch50 T9 duplicate clean | ✅ | Ch50 初判 T9 duplicate=1（Ch8 重复段落）；使用版本化 deterministic clean 创建 `clean-8-6-cd06a7b7`，复判 T9=0、five-gate PASS、segment audit PASS | DONE：`tasks/192.s-xuanhuan-ch50-t9-duplicate-clean-DONE.md` |
| 192.t | xuanhuan Ch75 segment audit critical orphan repair | ✅ | Ch75 初判 segment audit `critical_orphans=5`；通过 repository 刷新 5 条 active critical tracking 到 Ch75 accepted version `v-6afe9dd8`，复判 `critical_orphans=0` / `halt_would_fire=false` | DONE：`tasks/192.t-xuanhuan-ch75-segment-audit-critical-orphans-DONE.md` |
| 192.u | xuanhuan Ch81 health_low_p1 critical orphan repair | ✅ | Ch81 P1 critical orphan + segment audit `critical_orphans=10`；创建版本化 continuity patch `fix-81-5-214e4cd7`，刷新 10 条 critical tracking，修复 Task 192 默认 `HALT_RETRIES=0`，复判 T9/five-gate/segment audit PASS | DONE：`tasks/192.u-xuanhuan-ch81-health-low-p1-critical-orphan-DONE.md` |
| 192.v | xuanhuan Ch93 health_low_p1 critical orphan repair | ✅ | Ch93 P1 critical orphan：`xuanhuan_lingyuan.relationship.guardian_hunter_deception`；创建 Ch93 accepted patch `fix-93-6-a98c0576` 并刷新 2 条 critical tracking，复判 T9/five-gate/segment audit PASS | DONE：`tasks/192.v-xuanhuan-ch93-health-low-p1-critical-orphan-DONE.md` |
| 192.w | xuanhuan Ch99 settlement numerical validation 处理 | ✅ | Ch99 accepted 前 settlement numerical validation failed；通过 single-chapter resume 生成 accepted `v-34d19e11`，T9=0、five-gate PASS；post-fix segment audit blocker 路由 192.x | DONE：`tasks/192.w-xuanhuan-ch99-settlement-numerical-validation-DONE.md` |
| 192.x | xuanhuan Ch99 segment audit critical orphan repair | ✅ | Ch99 accepted 后 segment audit `critical_orphans=4`；创建 Ch99 accepted patch `fix-99-6-86643cba` 并刷新 4 条 critical tracking，复判 T9/five-gate/segment audit PASS | DONE：`tasks/192.x-xuanhuan-ch99-segment-audit-critical-orphans-DONE.md` |
| 192.y | xuanhuan Ch105 health_low_p1 critical orphan repair | ✅ | Ch105 P1 critical orphan：`xuanhuan_lingyuan.technique.lingyuan_quan_first_form`；创建 Ch105 accepted patch `fix-105-5-75d18199`，resolve P1；post-fix segment audit blocker 路由 192.z | DONE：`tasks/192.y-xuanhuan-ch105-health-low-p1-critical-orphan-DONE.md` |
| 192.z | xuanhuan Ch105 segment audit critical orphan repair | ✅ | Ch105 post-fix segment audit `critical_orphans=13` / `halt_would_fire=true`；创建 accepted patch `fix-105-6-4cc94f2e` 并刷新 13 条 critical tracking；复判 segment audit/T9 PASS | DONE：`tasks/192.z-xuanhuan-ch105-segment-audit-critical-orphans-DONE.md` |
| 192.aa | xuanhuan Ch106 invalid model run-state cleanup | ✅ | Ch106 resume 时未显式设置 `LLM_MODEL`，链路回退 `deepseek-chat` 并污染 failed_chapters；确认 Ch106-Ch108 无 accepted head 后恢复 run state 到 Ch105 / failed=[] | DONE：`tasks/192.aa-xuanhuan-ch106-invalid-model-run-state-cleanup-DONE.md` |
| 192.ab | xuanhuan Ch108 settlement numerical validation | ✅ | Ch108 SettlementExtractor 数值校验失败；正式 single-chapter resume 生成 accepted `v-d841678c`，T9=0；post-fix segment audit blocker 路由 192.ac | DONE：`tasks/192.ab-xuanhuan-ch108-settlement-numerical-validation-DONE.md` |
| 192.ac | xuanhuan Ch108 segment audit critical orphan repair | ✅ | Ch108 accepted 后 segment audit `critical_orphans=2` / `halt_would_fire=true`；创建 accepted patch `fix-108-10-c8519110` 并刷新 2 条 critical tracking；复判 segment audit/T9 PASS | DONE：`tasks/192.ac-xuanhuan-ch108-segment-audit-critical-orphans-DONE.md` |
| 192.ad | xuanhuan Ch111 health_low_streak_halt repair | ✅ | Ch109-Ch111 accepted 后自动硬门 `health_low_streak_halt: window=3 P2_total=11 >= limit=2`；创建 Ch111 accepted patches `fix-111-6-334c5af5` / `fix-111-7-4abf3d31`，resolve 11 条 overdue foreshadowing、10 条 P2 marks，并刷新 9 条 critical tracking；复判 segment audit/T9 PASS | DONE：`tasks/192.ad-xuanhuan-ch111-health-low-streak-halt-DONE.md` |
| 192.ae | xuanhuan Ch120 health_low_p1_halt repair | ✅ | 创建 Ch112/117/118/120 accepted continuity patches，刷新 6 条 critical tracking，resolve 4 条 P1 marks；run 恢复为 running、failed=[]、completed_count=120；segment audit/T9 PASS | DONE：`tasks/192.ae-xuanhuan-ch120-health-low-p1-halt-DONE.md` |
| 192.af | xuanhuan Ch129 settlement JSON parse repair | ✅ | Ch129 accepted `v-08f5f8f0`；SettlementExtractor valid；SummaryWriter generated；run restored to completed 1..129, failed=[]；segment audit 后续失败已拆 192.ag | DONE：`tasks/192.af-xuanhuan-ch129-settlement-json-parse-DONE.md` |
| 192.ag | xuanhuan Ch129 segment audit critical orphans | ✅ | 创建 Ch129 accepted continuity patch `fix-129-d8015e35`，刷新 11 条 critical tracking 并 resolve P1 marks；segment audit @129 PASS，T9=0；run completed 1..129, failed=[] | DONE：`tasks/192.ag-xuanhuan-ch129-segment-audit-critical-orphans-DONE.md` |
| 192.ah | xuanhuan Ch131 LiteraryAuditor JSON parse repair | ✅ | Ch131 accepted `v-23e50dbd`；SettlementExtractor valid；SummaryWriter generated；run restored to completed 1..131, failed=[]；segment audit @131 PASS，T9=0 | DONE：`tasks/192.ah-xuanhuan-ch131-literary-auditor-json-parse-DONE.md` |
| 192.ai | xuanhuan Ch134 health_low_streak_halt repair | ✅ | Ch134 accepted/current head `fix-134-segment-192ai`；unresolved P2 Ch132-Ch134=0；continuity health @134=8.7；segment audit @134 PASS；T9=0；run completed 1..134，failed=[] | DONE：`tasks/192.ai-xuanhuan-ch134-health-low-streak-halt-DONE.md` |
| 192.aj | xuanhuan Ch138 health_low_p1_halt repair | ✅ | Ch138 accepted/current head `fix-138-segment-192aj`；continuity audit @138 P1=0；segment audit @138 PASS；T9=0；run completed 1..138，failed=[] | DONE：`tasks/192.aj-xuanhuan-ch138-health-low-p1-halt-DONE.md` |
| 192.ak | xuanhuan Ch144 health_low_streak_halt repair | ✅ | Ch144 accepted/current head `fix-144-segment-192ak`；continuity audit @144 P2=0、health=9.4；segment audit @144 PASS；T9=0；run completed 1..144，failed=[] | DONE：`tasks/192.ak-xuanhuan-ch144-health-low-streak-halt-DONE.md` |
| 192.al | xuanhuan Ch150 health_low_p1_halt repair | ✅ | Ch150 accepted/current head `fix-150-p1-192al`；direct P1 target `xuanhuan_lingyuan.technique.lingyuan_quan_first_form` 已修复；continuity audit @150 P1=0；T9=0；post-fix segment/five-gate blocker 路由 192.am | DONE：`tasks/192.al-xuanhuan-ch150-health-low-p1-halt-DONE.md` |
| 192.am | xuanhuan Ch150 segment audit critical orphans | ✅ | Ch150 accepted/current head `fix-150-segment-192am`；3 个 critical tracking 已刷新；segment audit @150 PASS；T9=0；five-gate stale health blocker 路由 192.an | DONE：`tasks/192.am-xuanhuan-ch150-segment-audit-critical-orphans-DONE.md` |
| 192.an | xuanhuan Ch150 five-gate health stale report | ✅ | 修复同章 continuity report latest 排序；Ch150 five-gate PASS、segment audit PASS、T9=0；Task 189 sci-fi baseline Ch125/150/175/200 replay PASS | DONE：`tasks/192.an-xuanhuan-ch150-five-gate-health-stale-report-DONE.md` |
| 192.ao | xuanhuan Ch156 health_low_streak_halt | ✅ | Ch156 accepted/current head `fix-156-segment-192ao`；10 条 overdue P2 伏笔 resolved，21 条 critical tracking 刷新到 Ch156；continuity audit health=9.2、overdue=0；segment audit PASS；T9=0；run completed 1..156，failed=[] | DONE：`tasks/192.ao-xuanhuan-ch156-health-low-streak-halt-DONE.md` |
| 192.ap | xuanhuan Ch162 health_low_p1_halt | ✅ | Ch162 accepted/current head `fix-162-segment-192ap`；P1 target `xuanhuan_lingyuan_seal.self.as_door` 已回收；Ch161 T9 artifact 已清理为 `clean-161-t9-192ap`；continuity audit health=9.6、overdue=0；segment audit PASS；T9=0；run completed 1..162，failed=[] | DONE：`tasks/192.ap-xuanhuan-ch162-health-low-p1-halt-DONE.md` |
| 192.aq | xuanhuan Ch168 health_low_p1_halt | ✅ | Ch168 accepted/current head `fix-168-segment-192aq`；P1 targets `xuanhuan_lingyuan.guardians.mother_descendant`、`xuanhuan_lingyuan_seal.self.as_door` 已回收；13 条 segment critical tracking 已刷新到 Ch168；continuity audit P1=0、health=9.2；segment audit PASS；T9=0；run completed 1..168，failed=[] | DONE：`tasks/192.aq-xuanhuan-ch168-health-low-p1-halt-DONE.md` |
| 192.ar | xuanhuan Ch175 segment audit + T9 hard gates | ✅ | Ch172 accepted/current head `clean-172-t9-192ar`；Ch175 accepted/current head `fix-175-segment-192ar`；12 条 critical tracking 已刷新到 Ch175；five-gate @175 PASS；segment audit @175 PASS；T9=0；run completed 1..175，failed=[] | DONE：`tasks/192.ar-xuanhuan-ch175-segment-t9-hard-gates-DONE.md` |
| 192.as | xuanhuan Ch180 health_low_p1_halt | ✅ | Ch180 accepted/current head `fix-180-segment-192as`；7 个 direct P1 targets 已回收，21 条 segment critical tracking 已刷新；continuity P1=0，segment audit PASS，T9=0；run completed 1..180，failed=[] | DONE：`tasks/192.as-xuanhuan-ch180-health-low-p1-halt-DONE.md` |
| 192.at | xuanhuan Ch186 health_low_p1_halt | ✅ | Ch186 accepted/current head `fix-186-segment-192at`；3 个 direct P1 targets 已回收，14 条 segment critical tracking 已刷新；continuity P1=0，segment audit PASS，T9=0；run completed 1..186，failed=[] | DONE：`tasks/192.at-xuanhuan-ch186-health-low-p1-halt-DONE.md` |
| 192.au | xuanhuan Ch192 health_low_p1_halt | ✅ | Ch192 accepted/current head `fix-192-segment-192au`；5 个 direct P1 targets 已回收，20 条 segment critical tracking 已刷新；continuity P1=0，segment audit PASS，T9=0；run completed 1..192，failed=[] | DONE：`tasks/192.au-xuanhuan-ch192-health-low-p1-halt-DONE.md` |
| 192.av | xuanhuan Ch198 health_low_p1_halt | ✅ | Ch198 accepted/current head `fix-198-segment-192av`；direct P1 target `xuanhuan_lingyuan_technique.escape.shadow_step` 已回收，13 条 segment critical tracking 已刷新；continuity P1=0，segment audit PASS，T9=0；run completed 1..198，failed=[] | DONE：`tasks/192.av-xuanhuan-ch198-health-low-p1-halt-DONE.md` |
| 192.aw | xuanhuan Ch200 five-gate health fail | ✅ | 补跑 Ch200 continuity audit `cont_b75b3a02`，health=8.1；five-gate @200 PASS、segment audit @200 PASS、T9=0；Task 192 父任务收口 | DONE：`tasks/192.aw-xuanhuan-ch200-five-gate-health-fail-DONE.md` |
| 193 | wuxia Ch200 爬坡 | ◐ | Ch28 deterministic clean/source 初始化已完成；193.p/q/r/u 已完成；已推进到 accepted_count=125，Ch125 head=`v-f979edd1`；Ch125 段边界审计 five-gate PASS（halt=None、health 8.1、CED 0.1584、overdue 73）、segment audit PASS（critical_orphans=0）、T9=0；run `run-v10-wuxia-5bbfab3a` completed @125、failed=[]、total_cost=4.146785 | 任务书：`tasks/193-wuxia-ch200-climb.md`；下一步 Ch126→Ch150，随后执行 Ch150 段边界审计 |
| 193.p | wuxia Ch125 missing checkpoints table | ✅ | 修复旧 Ch100 source 复制出的 V10 target DB 缺少 LangGraph checkpoint tables 时，`prune_orphan_checkpoints()` 在 setup 前崩溃的问题；缺表幂等返回 0，表存在时保持原清理语义 | DONE：`tasks/193.p-wuxia-ch125-missing-checkpoints-table-DONE.md` |
| 193.q | wuxia Ch117 health_low_p1_halt | ✅ | 创建 Ch117 continuity patch `fix-117-p1-193q`，补回 `blood_abyss.reverse_practice` 正文承接；continuity health=8.0、critical_orphans=0，segment audit PASS，T9=0；run restored to running | DONE：`tasks/193.q-wuxia-ch117-health-low-p1-halt-DONE.md` |
| 193.r | 评测口径修复包 | ✅ | detect_halt 经 `project_runs.pause_reason`（additive 迁移）区分人工/成本暂停与质量熔断，历史 NULL 行保守旧行为；segment_audit 阈值与运行时同源（注册表基线 + 目标库 DB 覆盖层，只读复刻 172i 语义），off-by-one 复核结论为无需改比较符；harness 接入 `--cost-budget`/`SONGYAN_RUN_COST_BUDGET`（无预算拒跑真实 --to）；xuanhuan 冻结库 five-gate/segment audit @200 复跑与 192 DONE 一致 | DONE：`tasks/193.r-eval-gate-caliber-fixes-DONE.md` |
| 193.s | setting tracking 刷新漏报根因诊断 | ✅ | Phase A 诊断报告 `docs/reports/193s-setting-tracking-root-cause.md`：机制修正（正文侧 Task 137 引用扫描为 active 设定刷新主路径），明确漏报 8/8 全落分支1（词面匹配层），分支2/3 为 0；漏报高度集中于核心 critical key（top2 各 12 次人工 patch）；Phase B 决策：进入 Phase C 修有界匹配层（覆盖 ≥88%），拆分为 193.v；命名漂移遗留路由 V11 | DONE：`tasks/193.s-setting-tracking-refresh-root-cause-DONE.md` |
| 193.v | setting tracking 正文引用词条匹配修复 | ✅ | F1a 《》纳入 name 拆分、F1b core phrase 下限按来源分级（name 3 / description 5，test_138c 护栏驱动调整）、F2 虚字归一化 relaxed 路径、F3 name 派生 ≥3 字 term CJK 后缀放宽；共享 `_term_in_content` 默认行为不变；F4 对照：诊断 8 章捕获 7/8（Ch163 深度 paraphrase 归 alias 遗留；Ch120 查明旧逻辑本可捕获、硬门真因为 isolate 空洞章）、lost=0、抽检无误刷；scifi end10 回归 10/10、T9=0（Ch2 瞬时锁经单章 resume 补齐）；冻结库复跑与 192 DONE 一致；wuxia Ch126+ 起新逻辑 | DONE：`tasks/193.v-setting-reference-term-matching-DONE.md` |
| 193.t | overdue operational 消费侧 lifecycle 过滤 | ✅ | 新增 `list_overdue_actionable`（仅 lifecycle active）并切换 `_find_overdue_foreshadowings`；冻结口径 `list_overdue_unresolved` 与五门 overdue（five_gate 自有 SQL）零改动；dormant/archived 决策：均排除（生命周期调度器已停放/退役条目，全量债务由五门段审计兜底）；xuanhuan 冻结库复跑 overdue=14 与 192 DONE 一致；scifi end10 回归 10/10 T9=0 一次通过；wuxia Ch126+ 起 actionable 口径 | DONE：`tasks/193.t-overdue-operational-lifecycle-filter-DONE.md` |
| 193.u | wuxia Ch121 resume schema drift 修复 | ✅ | 旧 source 复制库缺 `pause_reason` 列致 resume 崩溃；修复为 `--to` 前 `ensure_target_schema`（幂等）；Ch121→Ch125 resume 完成（125/125、failed=[]、cost 4.147），途中成本熔断优雅暂停 `pause_reason='cost_budget'` 生产实证；Ch125 five-gate PASS、segment audit PASS、T9=0 | DONE：`tasks/193.u-wuxia-ch121-resume-schema-drift-DONE.md` |
| 193.w | 段审计判定消费修复 | ✅ | five-gate health 门输出 `health_report_chapter`（判定逻辑零变化）；harness run_audit 解析 JSON 生成 verdict 块（segment halt 上浮、stale health lag≥2 预警）；Ch125 实库显示 @Ch123，xuanhuan 冻结库 @200 复跑结论与 192 DONE 一致 | DONE：`tasks/193.w-segment-audit-verdict-and-stale-health-guard-DONE.md` |
| 194 | urban Ch200 爬坡 | ◐ | 任务书已建立；urban 是当前唯一 CONTINUE_READY source，可用 Task 191 harness 初始化并按 Ch125/150/175/200 推进 | 任务书：`tasks/194-urban-ch200-climb.md`；未启动实跑 |
| 195 | 跨体裁 Ch200 总验收 | ◻ | 汇总三体裁 Ch200 与 sci-fi baseline；形成 V10 长窗口结论 | 总报告落盘；STATUS/README/INDEX 更新 |

### V10.3 优秀度信号包

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 196 | 优秀度样本集与校准协议 | ◻ | 定义信号边界、样本抽样、人工/自动标注协议；区分 report-only 与候选 gate | 样本清单 + 校准口径 + 误报记录；不是纯文档任务 |
| 197 | 跨章同质化/多样性/叙事张力指数 | ◻ | 检测重复冲突结构、重复场景功能、重复桥段节奏、张力曲线塌陷 | report-only 输出；有章节证据与误报记录 |
| 198 | 中文 AI 腔规则包 | ◻ | 从词表升级到规则包：套话、保护性表达、说明文腔、抽象空转 | `songyan metrics/report` 可定位命中段落 |
| 199 | style extraction → style card | ◻ | 从 accepted 正文抽取项目风格卡；V10 内先生成与报告，不默认注入 Writer/CreativeDirector | style card 生成可复现；不改变历史样本判定 |
| 200 | 角色声纹锚点 | ◻ | 为主要角色建立声纹特征与偏离检测；先 observe，不自动改写 | 声纹报告可按角色/章节定位 |
| 201 | judge 偏差对策 | ◻ | 多样本、多 judge、盲评/对照协议；避免单一 judge Goodhart | 校准报告说明偏差与适用范围 |
| 202 | perplexity / 可读性可行性 spike | ◻ | 评估 perplexity、可读性统计、句段节奏等信号在中文长篇上的稳定性 | 给出采用/放弃/后置结论；不作为硬 gate |
| 203 | 优秀度报告整合 | ◻ | 将 197-202 输出整合到 metrics/report；分层展示不混入五门 | V10 总报告可引用统一优秀度视图 |

### V10.4 结构升级 spike

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 204 | KG 图 diff spike | ◻ | 用少量已知热点章验证事实图 diff 的发现能力 | 给出继续/放弃/后置结论 |
| 205 | FactTrack validity interval spike | ◻ | 验证事实有效期建模是否降低过期事实误用 | 给出数据模型影响与迁移成本 |
| 206 | Storyline Tree spike | ◻ | 验证主线/支线树对长程伏笔和弧级收束的价值 | 给出是否进入 V11/V12 的决策 |

### V10.5 收口

| Task | 名称 | 状态 | 内容要点 | 验收要点 |
|------|------|:----:|----------|----------|
| 207 | V10 收口与归档 | ◻ | STATUS / README / INDEX / AGENTS / 本文更新；任务归档到 `archive/v10/`；V11 前置确认；**登记项一并处理**：metrics 慢路径修复（189 遗留，`songyan metrics --chapters 1-200` 历史库卡死）、评测工具次要清理（baseline `min_up_to` 字段未消费、five_gate `final>=100` 过时语义、harness inventory 的 DONE markdown 正则兜底、`_genre_from_db_path` 文件名反推、`DATABASE_URL cleanup` 提示误导、`_create_v10_project_run` 裸写 repository 评估）；alias/命名漂移与 settlement 持久化按 193.s/v 决策路由 V11 | V10 全量闭环；V11 可按 `tasks/V11-Plan.md` 进入开源可用化收尾 |

---

## 执行纪律

1. **先口径，后实跑**：190/191 已完成；后续任何非 sci-fi Ch200 长跑必须使用 Task 191 harness，并遵守 Task 190 三态准入。
2. **段边界早停**：Ch125 / Ch150 / Ch175 / Ch200 任一段五门不过，先冻结现场并路由定点修复。
3. **优秀度先离线/observe**：优秀度信号未校准前不得进入自动门禁，也不得默认注入生成 prompt。
4. **诊断 DB 不作终判样本**：机制修复后必须 clean rerun。
5. **不把 spike 伪装成主线**：204-206 只给技术决策，不阻塞 Ch200，除非明确证明现有结构无法继续。
6. **成本纪律**：Ch200 长跑必须启用 `SONGYAN_RUN_COST_BUDGET` 和 wrapper；分段预算耗尽优雅暂停，可提额 resume。

---

## 明确不做

| 项 | 归属 |
|----|------|
| 开源用户安装/初始化/备份/恢复/发布 checklist | V11 |
| Web/UI/桌面端/账号系统/后台服务 | 不属于当前项目主线 |
| 小说特化微调、多 agent 仿真生成、Temporal durable execution 迁移 | 调研反面清单，不做 |
| 将优秀度信号直接变成硬 gate | V10 后再评估，必须先有校准证据 |
| 将 style card / 声纹锚点默认注入生成链路 | V10 先 report/observe；注入需另立任务并回归 |
| 新增核心 Agent / Workflow 节点 | 默认不做，除非任务书单独批准 |

---

## 文档入口

- V10 规划入口：`tasks/V10-README.md`（本文）
- V9 历史事实：`tasks/V9-README.md`
- V9 归档索引：`archive/v9/INDEX.md`
- V10 未来归档位置：`archive/v10/`
- V8 长调研报告（优秀度/结构升级储备）：`docs/reports/v8-literature-and-landscape-review.md`
- V9 中篇爬坡冻结口径参照：`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1
- V11 预登记备忘：`tasks/V11-Plan.md`
