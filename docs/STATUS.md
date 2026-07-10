# Songyan 项目状态

> 短版状态板。长版历史状态已归档：`archive/v5/context-docs/STATUS-full-20260621.md`。

## 当前结论

| 项 | 状态 |
|----|------|
| 当前阶段 | **V7 阶段 W/X/Y 已通过，T9/T10/T12 已冻结；文学提质专项（170c–170n）**：Task 170b 中段窗口（Ch28–Ch40）真实实读证明"治理指标全达标 ≠ prose 好看"——T9=0、continuity health 9.1–9.7、QG 全 pass，而 voice 均值 1.8（塌陷）、节奏偏慢、Ch31 有真实文本缺陷，机器文学诊断系统性高估、T9 近似重复漏报。提质专项遵循"量具优先"：**170c–170m 已完成**。170g Phase2 未达标，维持 blocker；170h 路径 B 第一步已完成并复评：voice 1.50 / exposition 2.50 / 窗口均值 2.65，未达 Ch200 放行标准。**170i（路径 B 第二步）已完成并复评**：voice 2.00 / exposition 2.25 / 窗口均值 2.55，未达放行标准。**170j/170k/170l（路径 B 第三/四/五步）已完成并复评**：170j minimal_voice_anchor（voice 2.25 / 窗口均值 2.60）、170k opposing_goal_anchor（voice 2.00 / 窗口均值 3.00）、170l few_shot_voice_anchor + ai_tone_blocklist（voice 2.00 / exposition 2.00 / 窗口均值 2.40，exposition_carrier 真实值 72 处），均未达标。**170l 执行中同时修复 RuleAuditor 引号匹配 bug**（仅匹配 ASCII `"..."` 漏报中文弯引号 `"..."`，导致 170h–170k `exposition_carrier=0` 失真）。**Task 170m 量具二次校准已完成**：动态化关键词 + ground truth 闭环后，170l 原 exposition_carrier=72 降至 6（高置信），但 voice/exposition 仍未达标。**Task 170n 方向评估已完成**：推荐方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）作为长跑定点工具；方向 A（路径 B 升级）作为备选。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 因 f-string 大括号转义错误、前置/后置说话人识别缺失、空行分场景过度切割导致的恒为 0 假阴性；修复后量具对规范标签对白可用，但不改变 170i 未达标的结论。当前维持 blocker，不放行 Task 171 Ch200，最终方向待用户决策。 |
| 前置阶段 | **V6 全阶段完成**：阶段 0+A+B+C 已完成；**阶段 D（长窗口验证）收官——Task 157（Ch1-Ch50 + harness）、158（Ch1-Ch100 + T5 首测）、158r（kill→resume 命令级证据 `run-82bd2e07`）、159（Ch1-Ch150 复现 + V6 阶段验收）全部完成**。**V6 阶段验收结论：实质达标、条件通过**——新管线 `run-bba292da` Ch1-Ch150 **150/150 accept、`failed=[]`、health 全程 ≥8.2**、orphan 斜率 0.0897（≪138n 基线 6.28）、无 T3/T4 红线、T5 已冻结；两处 harness fail（T6b 瞬时已 resolved orphan、T5 旧口径缺陷）判为判据口径待校准项、非治理退化，列后续工程 Task。报告 `docs/reports/task-159-v6-final-acceptance-report.md`，DONE `tasks/159-...-DONE.md`。Task 141-159，事实入口 `tasks/V6-README.md`。前置 V5.2 已完成验收（下行）。 |
| V5.2 验收结论 | **V5.2 已完成：默认 gate_mode 切换为 `enforce`，`songyan run` 未指定 `--gate-mode` 时默认使用 enforce 模式。enforce 模式 Ch1-Ch150 完整验证通过：`run-813a9ed7` Ch1-Ch50 50/50 accept；`run-df933dbf` Ch51-Ch150 100/100 accept；Ch80 经 Task 139h 修复后重跑（`run-7b45c17d`）成功 accept。最终 150/150 章节 accepted，`failed=[]`，无 AutoHalt，continuity health=8.5。Task 139d 最终验收包已交付。** |
| 最终验收 | **Task 120 V5.0 + Task 132 V5.1 + Task 139d V5.2 Final Acceptance Package 已交付** |
| 风险口径 | P0/P1 风险为 0 |
| 最近全量测试 | 170i 改动后：`ruff check src/ tests/` 通过；分模块 pytest 全通过——`tests/test_rule_auditor.py tests/test_prompt_loader.py tests/test_revision_handler_literary.py tests/test_creative_director.py tests/test_non_character_voice_cards.py` 139 passed、`tests/db tests/models tests/genres` 357 passed、`tests/rag tests/settlement_extractor tests/creative_modes tests/cli` 133 passed、`tests/evals tests/integration` 76 passed/4 skipped、`tests/test_*.py` 1905 passed/1 xfailed。完整 `pytest tests/ -q` 在 Windows 长耗时下易卡住，按 AGENTS.md Windows 测试防卡协议改分模块 + 顶层批次执行。 |
| 最近修复/验证 | Task 123 ContextEmergency / health_low 候选硬门禁（默认观测模式，16 个新单测）；Task 124 离线影响面分析；Task 125 阈值调优（P1 异常检测、health_score 跌幅、审计点 streak），新增 12 个单测；Task 126 enforce 小窗口实跑验证，Ch1–Ch19 零 gate 触发；**Task 127 重构 `health_low_score_halt` 为"历史新低 + P1 同步激增"复合条件，新增 8 个单测，pytest 1842 passed**；**Task 128 完成**：QG false 降级接受不终止 run、Ch1–Ch10 质量爬坡阈值、RevisionHandler readability 专精路径；pytest 1843 passed；**Task 129 条件完成**：enforce 模式 Ch1–Ch50 验证，`run-89d7a2d4` Ch1–Ch15 后因 quality_gate_fail_streak 暂停，暴露 Writer 结构退化、SettlementExtractor 角色/数值提取失败、orphaned settings 快速累积等底层缺陷；报告见 `docs/reports/task-129-enforce-validation-report.md`。**Task 130 已完成**：gate_mode 默认保持 `observe`，`songyan run` 暴露 `--gate-mode` CLI 参数，`songyan report` 新增 gate 触发汇总。**Task 131 已完成**：历史规划稿已归档至 `archive/tasks/`，索引文档已指向 `-DONE.md`。**Task 132 已完成**：V5.1 最终验收包已交付，V5.1 通过（条件完成项已明确转入 V5.2）。**Task 133/134/135 已完成**：Writer 多场景结构、SettlementExtractor 角色/数值提取、设定回收与 continuity health 治理；**Task 138f 已完成**：numerical_update evidence gate 已落地，无明确正文/source_quote 数字证据的 telemetry 候选会过滤并记录 diagnostic，真实 ledger 仍硬校验；**Task 138d-R2 retry4 已完成**：`run-bcee6ab6` Ch11/Ch12 settlement、summary、QG 全过，Ch12 continuity `health=3.0`、`orphaned=14`、`mismatches=0`；**Task 138g 已执行但未收口**：目标测试 `70 passed`、ruff 通过，`run-715f7d09` completed 但 Ch12 `health=3.0`、`orphaned=16`、critical orphan=4，证明问题不在 alias 而在 recall 执行闭环；**Task 138h-138j 已完成**：critical orphan 强制回收闭环建立，138i 措辞硬化无效，138j `recycle_hint` 显著有效，文档见 `tasks/138h-critical-orphan-mandatory-recall-loop-DONE.md`；**Task 138l 已完成**：settlement 数值遥测误报修复，4 个新增单测，`tasks/138l-settlement-telemetry-false-positive-fix-DONE.md`；**Task 138k 已完成**：Ch1-Ch30 长窗口 rehearsal（Run `run-6f2a10d3`）全部完成 30/30，无 AutoHalt，但 Ch21+ health 下滑、Ch30 P1=35，报告见 `docs/reports/task-138k-long-window-rehearsal-report.md`**；**Task 138m 已完成**：根因分析确认 35 个 P1 orphan 主要系 Ch20+ 新 critical 设定引入后丢弃、`MAX_ORPHANED=8` 约束预算截断、`mandatory_references` 无上限导致 Writer 过载；推荐 A+C，报告见 `docs/reports/task-138m-critical-orphan-root-cause-report.md`，后续任务 `tasks/138n-qg-mandatory-reference-revision-loop-DONE.md`** |
| 当前 lint | `ruff check src/ tests/` 通过（仓库存量脚本另有历史 lint 债，非本次引入）；`ruff check prompts/` 不适用（YAML 非 Python） |
| Python | 3.11.9 |
| 后续阶段 | 阶段 W/X/Y 已通过、T9/T10/T12 已冻结；**文学提质专项进入决策点**：170h/170i/170j/170k/170l 路径 B 连续五步均已复评未达标（voice 1.50/2.00/2.25/2.00/2.00、exposition 2.50/2.25/2.25/2.50/2.00、窗口均值 2.65/2.55/2.60/3.00/2.40），维持 blocker，不放行 Task 171 Ch200。**170l 同时修复 RuleAuditor 引号匹配 bug**（中文弯引号 `"..."` 漏报），暴露 170h–170k `exposition_carrier=0` 失真。Task 170n 评估结论：路径 B 轻量策略已到顶，推荐方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）作为长跑定点工具；方向 A（路径 B 升级）作为备选。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 的假阴性（f-string 转义、前后置说话人、短场景合并、空情绪词交集），量具修复不影响 170i 未达标结论。等待用户最终决策：① 接受方向 C，立即启动 Task 171 Ch200 长跑；② 选择方向 B，先建样本库并小样本验证；③ 选择方向 A，跑最小硬节拍验证，不达标即回退 C。全程不放宽 T9/T10/T5/T6/T12 冻结口径。 |
| 事实入口 | 当前阶段：`tasks/V7-README.md`；V6 阶段：`tasks/V6-README.md`；V5 阶段：`tasks/V5-README.md` |
| single-run rehearsal | Task 121b：`run-21ff158b`，Ch1-Ch4 成功，Ch5 阻断；Task 121d：`run-f749826e`，Ch1-Ch7 成功，Ch8 阻断；Task 121e 重跑：`run-0317a247`，Ch1-Ch17 成功，Ch18 阻断；Task 121f 聚焦验证：`run-058fb9de`，Ch1-Ch18 成功；Task 121g 完整重跑：`run-0fd1456e`，Ch1-Ch114 成功，Ch115 阻断；Task 121h 已完成工程修复；Task 121i `run-ce1767ff` Ch115 聚焦验证成功；Task 121j `run-b063b6f0` Ch1-Ch13 成功后因连续 ContextEmergency AutoHalt 暂停；Task 121l `run-08689f68` Ch1-Ch12 成功后因 Ch10-Ch12 连续 ContextEmergency 且含 QG false 按新策略暂停；Task 121o `run-4ff41095` Ch1-Ch18 全部成功 18/18，ContextEmergency 0 次，AutoHalt 0 次，已越过 Ch13 和 Ch18；Task 121p `run-2d7d96c2` 修复 Bug A/B 后重跑，Ch1-Ch3 成功，Ch4 因 0.82 阈值阻断；Task 121q `run-86b1170c` Ch1-Ch20 聚焦验证 20/20 全部成功；**Task 121q full single-run `run-a2bed648` Ch1-Ch150 全部成功 150/150，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙** |
| Task 121c | 已修复 rewrite fallback 后 `_skip_settlement=True` 错误阻断 settlement 的契约 |
| Task 121d | 已执行修复后重跑；已验证 Ch5 阻断解除，新增 Ch8 settlement_review 阻断 |
| Task 121e | 已修复并实跑验证 Ch8 settlement 伏笔校验阻断；Ch18 暴露新阻断 |
| Task 121f | 已修复 Ch18 CreativeDirector JSON parse failure 后的错误传播/章节状态判定契约，并通过 `run-058fb9de` Ch1-Ch18 聚焦验证 |
| Task 121g | 已完成新的干净 Ch1-Ch150 single-run：`run-0fd1456e` 最终 `partial`，Ch1-Ch114 成功，Ch115 因 quality gate human review 阻断 |
| Task 121h | 已完成 Ch115 quality gate / best-version rewrite 工程修复：rewrite 状态生命周期清理、版本化 new issues、低质量 rewrite / hard truncate 回滚到 safe best；全量 pytest/ruff 通过 |
| Task 121i | 已完成 Ch115 聚焦重跑：`run-ce1767ff`，Ch115 success / settlement / summary 均通过；Ch111-Ch115 质量窗口复核显示工程阻断解除但正文质量偏弱 |
| Task 121j | 已执行新 Ch1-Ch150 full single-run：`run-b063b6f0`，Ch1-Ch13 成功，Ch13 后因 Ch11-Ch13 连续 ContextEmergency 触发 AutoHalt，结果 partial |
| Task 121k | 已规划为 V5.1 Prompt / 正文质量清理，处理机械场景标题、元标记泄漏、短段落碎片化和说明文堆叠 |
| Task 121l | 已完成 AutoHalt 策略修复、单测和 Ch1-Ch18 聚焦实跑：`run-08689f68` 完成 Ch1-Ch12，失败 0；Ch10-Ch12 连续 ContextEmergency 且 Ch10 QG false，按新 `context_emergency_degraded_streak` 策略暂停，结果 partial |
| Task 121m | **已完成**：QG false 硬拦截 settlement + 元标记泄漏清理；`pytest` 1731 passed |
| Task 121n | **已完成**：Context Diet 2.0 预算增量 80→250 + human_marks 生命周期窗口 10→6；`pytest` 1731 passed |
| Task 121o | **已完成**：Ch1-Ch18 聚焦验证重跑 `run-4ff41095` **18/18 全部成功**，ContextEmergency 0 次，AutoHalt 0 次，已越过 Ch13 和 Ch18 |
| Task 121p | **已完成 Bug A/B 修复与重跑**：`run-40ceb306` 因 pipeline 未跳过已有 accepted 章节 + RAG 索引超时异常未捕获中断；Bug A/B 已修复；`run-2d7d96c2` 重跑 Ch1-Ch3 成功，**Ch4 因 0.82 阈值阻断** |
| Task 121q | **已完成**：`_SAFE_BEST_MIN_OVERALL_SCORE` 动态化（Ch1-Ch20→0.75, Ch21-Ch50→0.78, Ch51+→0.82）+ `degraded_accept` 降级回滚路径；pytest 1731 passed；ruff 通过；**Ch1-Ch20 聚焦验证 `run-86b1170c` 20/20 全部成功** |
| Task 121r | **已完成**：Writer 1.1.0（空行分隔场景、禁止 markdown/HTML/元标记、段落节奏约束）+ CreativeDirector 1.0.5（可执行约束、行动承载、避免设定清单退化）+ RuleAuditor 新增 markdown 场景标题与短段落比例检测；pytest 1764 passed；ruff 通过 |
| Task 122a | **已完成**：动态阈值 `_safe_best_min_score` 边界值测试 + `degraded_accept` 降级回滚路径测试；pytest 通过 |
| Task 122b | **已完成**：新增 12 个集成测试覆盖 degraded_accept 路由、safe best 保护、human_review_required gate、AutoHalt streak 逻辑；pytest 1784 passed；ruff 通过 |
| Task 122c | **已完成**：Ch1-Ch20 E2E 集成测试（28 秒重度 Mock）；Ch40-Ch50 / Ch100-Ch110 窗口待补充 |
| Task 122c | **已完成**：Ch1-Ch20 / Ch40-Ch50 / Ch100-Ch110 三个 E2E 窗口验证全部完成；`test_ch41_50_validation.py` 已补强 emergency/auto-halt 断言；`test_ch100_110_from_run_log.py` 已新增并复用 `run-a2bed648` 历史数据 |
| 重跑前清理 | **2026-07-01（V6 启动准备）**：VACUUM 清空主库 `songyan.db` 全部业务数据（144821 行 → 0，schema 保留），374MB → 0.41MB；删除 `logs/` + `projects/*/logs/` 共 342 个运行日志；清理 `.tmp/` 中 V5.2 中间过程 DB 与 0 字节临时文件（保留 138n/138k V6 校准依赖与 139b_rerun2 验收证据 DB）；归档 pass1-18 + handover 到 `archive/v5/reports/`，删除与 archive/v3 重复的 v3.1_ch* 报告。此前 2026-06-23 亦有一次全量清理记录。 |
| 下一步规划 | **文学提质专项进入决策点**：170h/170i/170j/170k/170l 路径 B 连续五步均已复评未达标（voice 1.50/2.00/2.25/2.00/2.00、exposition 2.50/2.25/2.25/2.50/2.00、窗口均值 2.65/2.55/2.60/3.00/2.40），维持 blocker，不放行 Task 171 Ch200。**170l 同时修复 RuleAuditor 引号匹配 bug**（中文弯引号 `"..."` 漏报），暴露 170h–170k `exposition_carrier=0` 失真。下一步需用户决策：① 路径 B 升级（更激进结构性改写/声源工程）；② AI 腔后处理 / 反模板化 rewrite 规则；③ 诚实降级文学目标、先放行 Ch200 并在长跑中人工抽读修复。全程不放宽 T9/T10/T5/T6/T12 冻结口径。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性，不改变 170i 未达标结论。 |

测试说明：`1 xfailed` 为已知非阻断项；`4 skipped` 为 integration 中依赖外部数据的测试；`0 xpassed`（已修复）；`0 failed`。当前分模块 + 顶层 pytest 全通过。

## 当前优先级

1. **Task 170m 量具二次校准已完成**：动态化 RuleAuditor exposition carrier 关键词并引入 ground truth 闭环，170l 原 exposition_carrier=72 经校准后降至 6（高置信），但 voice/exposition/窗口均值仍未达 Ch200 放行线，维持 blocker。
2. **Task 170n 方向评估已完成**：推荐方向 C（目标降级）+ 同步准备方向 B（AI 腔后处理）作为长跑定点工具；方向 A（路径 B 升级）作为备选。最终方向待用户决策。
3. **文学提质专项（阶段 Z 前置门）进入决策点**：Task 170h 路径 B 第一步已完成并复评（voice 1.50 / exposition 2.50 / 窗口均值 2.65），Task 170i 路径 B 第二步已完成并复评（voice 2.00 / exposition 2.25 / 窗口均值 2.55），Task 170j/170k/170l 路径 B 第三/四/五步已完成并复评（170j voice 2.25 / 窗口均值 2.60；170k voice 2.00 / 窗口均值 3.00；170l voice 2.00 / exposition 2.00 / 窗口均值 2.40，exposition_carrier 真实值 72 处），均未达标，维持 blocker，不放行 Task 171 Ch200。**170l 同时修复 RuleAuditor 引号匹配 bug**（仅匹配 ASCII `"..."` 漏报中文弯引号 `"..."`，导致 170h–170k `exposition_carrier=0` 失真）。路径 B 轻量策略连续五步收益递减/劣化，下一步需用户决策：① 路径 B 升级（更激进结构性改写/声源工程）；② AI 腔后处理 / 反模板化 rewrite 规则；③ 诚实降级文学目标、先放行 Ch200 并在长跑中人工抽读修复。专项总览 `tasks/170-literary-quality-remediation-README.md`；170l DONE `tasks/170l-few-shot-voice-anchor-DONE.md`；170l 复评报告 `docs/reports/task-170l-few-shot-voice-anchor-reeval-report.md`。**2026-07-10 追加 170i 量具补丁**：修复 `detect_human_voice_homogeneity` 恒为 0 假阴性（f-string 转义、前后置说话人、短场景合并、空情绪词交集），已补测试并通过 ruff/pytest；该补丁修复量具本身，不改变 170i 未达标结论。
2. **Task 171 Ch200 长跑（阶段 Z 入口冻结）**：170h/170i/170j/170k/170l 均未达标，入口继续冻结。下一步需用户从路径 B 升级 / AI 腔后处理 / 目标降级三个方向中决策，达标或明确降级后方可重新评估 Ch200 入口。
3. **V6 阶段验收（Task 159 已完成，前置基线）**：Ch1-Ch150 治理管线复现无人值守长跑（run `run-bba292da`，隔离 DB `.tmp/task159_ch1_ch150.db`，enforce + isolate，真实 DeepSeek API，由自主督跑脚本 `scripts/supervise_159.py` 保守策略完成）。**结果：150/150 accept、`failed=[]`、health 全程 ≥8.2**；orphan 斜率 0.0897（≪138n 基线 6.28）、无 T3/T4 红线；N/D/R 三项 harness 直接 pass；**T5 已冻结**（150 章 18 样本，DB 峰值 112.32MB，扫描耗时口径改"全样本中位数×2.0"）。**V6 阶段验收结论：实质达标、条件通过**。报告 `docs/reports/task-159-v6-final-acceptance-report.md`。
4. **后续工程 Task（V7 期间处理）**：① `check_t5` 默认参数改中位数×2.0 + 单点稳健采样并落地冻结值，同步更新 `tests/test_158_t5_freeze.py`；② `check_t6b` 对已 resolved 设定豁免历史 orphan 快照、`check_t6c` 小基数归因口径校准。均为 harness（度量）改进，不涉及生成/门禁治理逻辑。
5. **持续回归**：后续改动继续执行分模块 pytest + `ruff check src/ tests/`。\r
\r
> 测试卫生（2026-07-01）：已删除孤立测试 `tests/test_124_gate_impact.py`——它动态加载的一次性离线分析脚本 `analyze_124_gate_impact.py` 已在 V6 启动时归档到 `archive/v5/scripts/`，该测试只覆盖这个已退役的一次性离线分析脚本、不覆盖产品门禁逻辑（运行时门禁由 test_125/127/128 等覆盖）。170g 改动后分模块 + 顶层 pytest 全通过。

## V5.1 交付摘要

- **Prompt 质量清理**：Task 121r 完成 Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 格式检测。
- **测试矩阵**：Task 122a/122b/122c/122d 完成单元、集成、E2E、150 章压力四层测试。
- **候选硬门禁**：Task 123–130 完成实现、离线影响面分析、阈值调优、enforce 小窗口验证、score halt 重构、严格模式容错、gate_mode 默认决策；默认 `observe`，可显式启用 `enforce`。
- **文档一致性**：Task 131 完成历史规划稿归档，索引统一指向 `-DONE.md`。
- **V5.1 验收结论**：通过；条件完成项（Task 129 暴露的底层缺陷）已明确转入 V5.2。

## V5.0 交付摘要

- Context Diet 2.0 四组件已完成：TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling。
- Ch111-Ch150 分段验证完成：40/40 成功，QG/settlement/summary 均 40/40。
- Task 115-117 已关闭 DG-2 条件通过风险窗口。
- Task 118 已完成 ContinuityAuditor health_low P1/P2/P3 分级和 human marks 追踪。
- Task 119 已统一 `songyan report` 入口并加固 Windows wrapper。
- Task 120 给出 V5.0 最终通过结论。

## 遗留项

| 项 | 级别 | 处理 |
|----|------|------|
| 一次性 Ch1-Ch150 单命令证据 | P1 | **Task 121q full single-run `run-a2bed648` 已完成**：Ch1-Ch150 150/150 全部成功，ContextEmergency 0 次，AutoHalt 0 次，degraded_accept 0 次，failed 0 次，无间隙 |
| Ch115 rewrite / best-version 劣化 | P1 | **Task 121h 已完成工程修复，Task 121i `run-ce1767ff` 已验证 Ch115 不再进入 human_review_required**；safe-best 回滚主路径未在本次触发，仍由单测覆盖 |
| 连续 ContextEmergency AutoHalt | P1 | **Task 121l 已完成策略修复；Task 121m 已完成 QG false 硬拦截；Task 121n 已完成预算调整；Task 121o 验证 Ch1-Ch18 0 次 emergency、0 次 AutoHalt。该风险已解除** |
| 0.82 阈值早期章节阻断 | P1 | **Task 121q 已完成**：0.82 已动态化，并引入 `degraded_accept` 降级回滚路径 |
| Prompt 质量瓶颈 | V5.1 | **Task 121r 已完成**：Writer 1.1.0 + CreativeDirector 1.0.5 + RuleAuditor 新增格式检测 |
| Pass 14-18 Code Review 缺口 | P1 | **已完成**：TS-01/TS-02/TS-03/TS-08 测试缺口已补齐；PR-05 元标记检测已补充；ST-03 目录迁移已修复；AG-04 显式拦截已补充；TS-10 测试卫生已清理 |
| health_low 硬门禁 | 预研 | **Task 123/124/125/126/127 已完成**：软复核 + 候选硬门禁实现 + 离线分析 + 阈值调优 + enforce 小窗口验证 + score halt 复合条件重构；`health_low_p1_halt`/`health_low_streak_halt` 在干净 run 中零误伤，`health_low_score_halt` 改为"历史新低 + P1 同步激增"复合条件；默认仍 `gate_mode="observe"`。`Task 129` 暴露的底层提取/设定回收缺陷由 Task 133/134/135 跟踪 |
| ContextEmergency 硬门禁 | 预研 | 保持合理降级，后置评估；当前 run 中未出现 context emergency |
| enforce 模式默认启用 | V5.2 | **已完成**：CLI 默认 gate_mode 已切为 `enforce`；`run-813a9ed7`/`run-df933dbf`/`run-7b45c17d` 联合证明 Ch1–Ch150 150/150 accept，无 AutoHalt |

## 文档入口

- 开发代理规则：`AGENTS.md`
- 项目概览与阶段入口：`README.md`
- 文档索引：`docs/INDEX.md`
- V7 任务事实（当前阶段）：`tasks/V7-README.md`
- V7 阶段规划：`docs/v7-plan.md`
- V7 构想（方向性）：`docs/v7-vision.md`
- V6 任务事实（前置）：`tasks/V6-README.md`
- V6 阶段规划：`docs/v6-plan.md`
- V6 论证基础（300 章 gap 分析）：`docs/300-chapter-gap-analysis.md`
- V5 任务事实：`tasks/V5-README.md`
- V5.0 最终验收：`archive/tasks/120-v5-final-acceptance-DONE.md`
- V5.1 规划：`tasks/121a-v50-goal-assessment-and-v51-plan.md`
- V5.1 Code Review 修复汇总（已归档）：`archive/v5/reports/pass14-final-fix-summary.md`
- Single-run rehearsal：`tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md`
- Rewrite fallback settlement 修复：`tasks/121c-rewrite-fallback-settlement-contract-DONE.md`
- 修复后 single-run 重跑：`tasks/121d-ch1-ch150-single-run-rerun-DONE.md`
- Ch8 settlement 伏笔校验修复：`tasks/121e-ch8-settlement-foreshadowing-validation-fix-DONE.md`
- Ch18 CreativeDirector 错误传播修复：`tasks/121f-ch18-creative-director-error-contract-DONE.md`
- Ch1-Ch150 完整重跑 / Ch115 阻断：`tasks/121g-ch1-ch150-single-run-rerun-ch115-blocker-DONE.md`
- Ch115 工程修复：`tasks/121h-ch115-quality-gate-rewrite-state-review-DONE.md`
- Ch115 聚焦验证：`tasks/121i-ch115-focused-rerun-and-quality-window-DONE.md`
- Ch1-Ch150 修复后重跑：`tasks/121j-ch1-ch150-single-run-after-ch115-fix-DONE.md`
- Prompt 质量清理：`tasks/121k-prompt-quality-cleanup-plan-DONE.md`
- ContextEmergency AutoHalt review：`tasks/121l-context-emergency-autohalt-review-DONE.md`
- 候选硬门禁：`tasks/123-context-emergency-health-low-gate-proposal-DONE.md`
- 候选硬门禁阈值调优：`tasks/125-gate-threshold-tuning-and-validation-DONE.md`
- 候选硬门禁 enforce 小窗口验证：`tasks/126-small-window-enforce-validation-DONE.md`
- 重构 `health_low_score_halt`：`tasks/127-health-low-score-halt-refactor-DONE.md`
- 严格模式容错与开局期质量爬坡：`tasks/128-strict-mode-fault-tolerance-and-quality-ramp-DONE.md`
- enforce 模式 Ch1–Ch50 验证：`tasks/129-enforce-mode-ch1-ch50-validation-DONE.md`
- gate_mode 默认模式决策：`tasks/130-gate-mode-default-decision-DONE.md`
- 任务文档归档与状态一致性清理：`tasks/131-task-docs-archive-and-status-cleanup-DONE.md`
- V5.1 最终验收包：`tasks/132-v51-final-acceptance-package-DONE.md`
- Writer 多场景结构修复：`tasks/133-writer-multi-scene-structure-fix-DONE.md`
- SettlementExtractor 角色/数值提取修复：`tasks/134-settlement-character-numerical-extraction-fix-DONE.md`
- 设定回收与 continuity health 治理：`tasks/135-setting-recycling-and-continuity-health-governance-DONE.md`
- V5.2 Ch1-Ch20 采集窗口实跑验证：`tasks/136-v52-enforce-ch1-ch20-validation-DONE.md`
- 设定回收闭环与 tracking 刷新机制：`tasks/137-setting-recycling-closed-loop.md`
- 剩余 orphan 分类与证据表：`tasks/138a-remaining-orphan-classification-DONE.md`
- 基于分类结果确定最小动作：`tasks/138b-orphan-root-cause-decision-DONE.md`
- 剩余 orphan 最小修复：`tasks/138c-orphan-minimal-fix-DONE.md`
- 修复后 Ch10-Ch12 聚焦复跑验证：`tasks/138d-ch10-ch12-post-fix-rerun-DONE.md`
- 事实源同步与 Task 137 收尾判断：`tasks/138e-task137-fact-sync-and-closure-DONE.md`
- Settlement 数值结算证据门禁工程化修复：`tasks/138f-settlement-evidence-gated-numerical-extraction-DONE.md`
- V5 归档：`archive/v5/INDEX.md`
- V5.2 enforce 模式 Ch1–Ch50 验证：`tasks/139b-v52-enforce-ch1-ch50-validation.md`
- V5.2 enforce 模式 Ch51–Ch150 验证：`tasks/139c-v52-enforce-ch51-ch150-validation.md`
- V5.2 默认 gate_mode 切换与最终验收包：`tasks/139d-v52-default-enforce-switch-and-final-acceptance.md`
- V5.2 settlement LLM 超时修复：`tasks/139g-v52-settlement-llm-timeout-fix.md`
- V5.2 Ch80 revision 字数膨胀修复：`tasks/139h-v52-ch80-revision-word-count-blowup-fix.md`
- V5.2 最终验收包报告：`docs/reports/task-139d-v52-final-acceptance-package.md`
