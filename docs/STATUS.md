# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V10-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | **V10.2 Task 192 xuanhuan Ch200 climb 可恢复 Ch106/125**：V9 已全量闭环（2026-07-23），事实入口 `tasks/V9-README.md`，归档入口 `archive/v9/INDEX.md`。V10 规划入口为 `tasks/V10-README.md`；Task 189 已冻结 sci-fi Ch200 baseline/checkpoint；Task 190 已完成 xuanhuan/wuxia/urban Ch100 终点事实源盘点（xuanhuan=REBUILD_REQUIRED、wuxia=BLOCKED_DIRTY_SAMPLE、urban=CONTINUE_READY）；Task 191 已完成 Ch200 harness 准备；Task 192/193/194 正式任务书已建立；Task 192.p/q/r/s/t/u/v/w/x/y/z/aa 已完成；xuanhuan clean Ch100 source ready，Ch200 target 已初始化并推进到 Ch105（105/105 accepted，failed=[]），Ch105 segment audit 已由 192.z 修复到 `critical_orphans=0` / `halt_would_fire=false`，192.aa 已清理 Ch106 invalid model run-state pollution；下一步使用 Task 191 harness + 显式 `LLM_MODEL=deepseek/deepseek-v4-flash` 继续 Ch106→Ch125；非 sci-fi Ch200 长跑和优秀度实现仍未完成 |
| V7 收尾 | **已完成**。sci-fi/space_opera + webnovel_intense 单一体裁稳定跑到 Ch200，200/200 accepted，D1 hard clean pass；Ch201-Ch220 20/20 accepted |
| V8.1 运行时画像 | **已完成**（Task 172a + 172a.p）。`GenreRuntimeProfile` 把 Context Diet 2.0 运行时契约从 sci-fi 默认值解耦；xuanhuan Ch8 halt 已消除（base_budget=15000） |
| V8.3 文学护栏 | **已完成**（Task 172d）。`literary_guardrail_observe` 去科幻硬编码，lexicon/主角名参数化到 `GenreProfile`，三体裁各配一套；DONE 文档已补齐 |
| V8 当前主线 | **Task 172c 已完成**：wuxia clean rerun Ch1-Ch100 100/100 accepted，0 halt，budget/CED/overdue/health/completeness 五门 PASS |
| V8 验收进度 | **P/C/Q/S/V 五维度已实证达标** |
| V8 文档治理 | **已完成**：`tasks/V8-README.md` 已明确 Task 编号是 trace id；阶段任务、前置并行、撞墙修复、后续增强已分层展示 |
| **V8 技术债** | **172e-172i 已完成**：`GenreRuntimeProfile` 声明后未接线的字段已全部接到消费者；`load_profile()` 已改为注册表基线 + DB 字段级覆盖层 |
| V8 遗留收口 | **172j/172k/172l 全部完成**：172k C 判据三档证据闭环（xuanhuan end10 10/10、urban end15 15/15、wuxia end20 20/20 gap=0，T9=0、overdue=0、budget<1.0；xuanhuan resolved=12 确认 172c.r 生效）；详见 `tasks/V8-README.md` V8.5 节 |
| V9.1 长跑可靠性 | **173/174/175/176 全部 ✅ 完成**：173 挂死根因确证（sqlite checkpointer 泄漏）并真修（2.5s 自然退出）；174 三边重建闭环；175 成本追踪/熔断/report 视图上生产线（阶段 D 实跑验收全通过，含两个生产缺陷修复）；176 防卡 wrapper 工具化（`-SelfTest` 11/11、实跑验收 PASS_NORMAL_EXIT、旧脚本已弃用） |

## 最新证据

| 维度 | 事实 |
|------|------|
| P 可插拔 | scifi profile 全默认 → 逐值回退旧行为；scifi --end 10 10/10、overdue=0、budget Ch1=8250=legacy 公式 |
| C 完成度 | scifi/wuxia/urban `--end 10` 各 **10/10 accepted**；xuanhuan `--end 15` 14–15/15（Ch2 瞬时 LLM JSON 错误，非系统性）；**172k 三档补完**：xuanhuan end10 10/10、urban end15 15/15、wuxia end20 20/20 gap=0 |
| Q 质量同标 | CED：wuxia 8.48 < urban 8.75 < scifi 9.60 < xuanhuan 10.48（同量级）；全体裁 budget<1.0、T9=0、0 halt |
| S 状态可控 | 172a.p horizon floor=12：floor12 实跑 DB 严证 **overdue@<15 = 2 < 5**（vs floor=0 的 28），44 伏笔 0 floor 违规 + 数学下界证明 |
| V 中篇爬坡 | 172b xuanhuan Ch1-Ch100 **100/100 accepted**；172c wuxia Ch1-Ch100 **100/100 accepted**；两个非 sci-fi 体裁 Ch100 五门 PASS |
| V9 生产化地基 | 173：显式 LLM client registry + `aclose_llm_clients()`，pipeline 收尾对称关闭 LLM client + sqlite checkpointer，`SONGYAN_FORCE_EXIT` 最外层兜底；174：`configure_logging()` 接入 CLI + harness，`logs/app/*.jsonl` 落盘，第三方 WARNING 起，关键字段与 `logs/chapter_runs` 对齐；175：`llm_call_usage` 逐调用落库（token/cost 双来源标记、按重试尝试计行、agent 归因），`run_cost_budget` 双检查熔断（DB 权威）+ `total_cost` 双接线，`songyan report` 成本视图；177：`songyan export` 正式 service + CLI，accepted head 正文导出，支持 `md/txt` 与 `flat/arc/volume`，xuanhuan/wuxia Ch100 实库验收通过；178：运行资源迁入包内并用 `importlib.resources` 加载，`evals/seeds` 与 `schema.sql` 入 wheel，非仓库 cwd 资源枚举 + `create-project` + Ch1-3 生成通过；179：`songyan run` 输出 `run_id`，`--mode-id` 默认回读项目 mode，README CLI 表补 `index`；180：`songyan doctor` 默认无成本只读自检，支持 JSON、显式 DB 初始化与 LLM client 探针；181：GitHub Actions 覆盖 ruff/mypy/default pytest/CLI pytest，CLI 测试与 mypy 清零；182：`scripts/five_gate_check.py` 与 `scripts/segment_audit.py` 正式收编，包内 sci-fi baseline，双体裁 Ch100 重放 PASS；183：`songyan profile show/diff/upsert` 上线，支持 DB override 调参不改代码；184：genres/creative_modes 包内 `_schema.json` + loader 预校验上线，坏资源 fail fast，`_schema` 元文件不污染资源列表 |
| V9.4 urban 标定 | **Task 185 已完成（2026-07-20）**：base_budget=12000 经 run1/run2（DB override）/run3（registry 默认值）三轮 end15 实跑标定，budget 峰值 ≤0.9643、emergency=0（172k 的 17 次连续 emergency 消除）；T9 全部命中逐条定性与定点修（检测器精度 8 项 + urban writer_rules 禁 `//` 注释体），终态检测器复测 run3/run2 accepted 正文 **T9=0**；run3 15/15、overdue 3、CED 5.46；185 终态初值为 12000（187.p 后 Ch100 爬坡 registry 为 14000）；scifi end10 回归 10/10、T9 1→0（精度修复预期后果）、无漂移；执行记录见 `archive/v9/185-urban-short-window-calibration-DONE.md` |
| V9.5 urban Ch100 | **Task 187 已完成（2026-07-22）**：正式样本 DB `.tmp/task172b_urban_ch100.db`、project `81e345042b124ee2a73094b82e4be555`、run `run-d22b1a44`；Ch1-Ch100 **100/100 accepted**，five-gate PASS（budget 0.9595、CED 0.11、overdue 100、health 8.6、gap 0），segment audit PASS（critical_orphans=0、halt_would_fire=false），T9=0（187.x/y/z precision 修复 + deterministic clean 后复跑）。终判证据落盘 `.tmp/187_urban_ch100_final.json` / `.tmp/187_seg100_audit.json` / `.tmp/187_seg100_metrics.md` |
| V10.1 Ch200 baseline | **Task 189 已完成（2026-07-23）**：sci-fi Ch200 事实源 `.tmp/task171_ch1_ch200.db`、project `835afdf11a294b5eac74a5d8998bd9a2`、run `run-fb39245c`；Ch125/150/175/200 显式 baseline 回放均 PASS；canonical baseline `tasks/189-scifi-ch200-baseline.json`（`.tmp/189_scifi_ch200_baseline.json` 仅为可选工作副本）；Ch200 指标 budget 0.9888、CED 0.3803、overdue 352、health 9.8、accepted 200/200、T9=0、segment audit 已按 `up_to=200` 截断且 critical_orphans=0 / halt_would_fire=false；完整 `songyan metrics` Ch200 慢路径仍未作为 Task 189 验收证据，后续如需复算走后缀修复或 Ch200 总验收 |
| V10.1 Ch100 盘点 | **Task 190 已完成（2026-07-24）**：xuanhuan=REBUILD_REQUIRED（DB 被覆盖，仅 1 章 0 accepted，project_id 已变）、wuxia=BLOCKED_DIRTY_SAMPLE（100/100、five-gate PASS、T9=1 meta Ch28 省略号占位，需 pre-Ch200 clean）、urban=CONTINUE_READY（100/100、five-gate PASS、T9=0）；统一盘点文件 `tasks/190-ch100-terminal-source-inventory-DONE.md` + `.tmp/190_ch100_source_inventory.json` |
| V10.1 Ch200 harness | **Task 191 已完成（2026-07-24）**：新增 `scripts/run_v10_ch200_climb.py`，冻结 V10 Ch200 DB/project/segment/audit/metrics 路径；支持 `--init`、`--init-from-source`、`--status`、`--audit`、`--to` 与 `--dry-run`；强制 Task 190 三态准入（urban allowed，wuxia/xuanhuan blocked），复制前校验 source DB 为 clean Ch100、source 与 Task 190 inventory 匹配、source `genre_id` 匹配、T9 meta/duplicate/timeline clean，并在目标 DB 创建 V10 `project_runs`；Ch125+ five-gate 显式绑定 `tasks/189-scifi-ch200-baseline.json`；聚焦测试 `tests/test_191_ch200_harness.py` **10 passed**，全量 pytest **2993 passed, 2 skipped, 1 xfailed**，ruff 通过；未启动 Ch101 |
| V10.2 Ch200 任务书 | **Task 192/193/194 任务书已建立（2026-07-24）**：192 要求 xuanhuan 先恢复/重建 clean Ch100，再初始化 Ch200；193 要求 wuxia 先对 Ch28 省略号占位执行版本化 deterministic clean 并重跑 T9=0；194 明确 urban 是当前唯一可直接初始化的 CONTINUE_READY source。Task 192 期间发现 scifi 短窗口回归失败（ContextEmergency halt），已通过 192.p 修复并复验；尚未启动任何非 sci-fi Ch200 实跑 |
| V10.2 Task 192.p | **已完成（2026-07-25）**：冻结原 scifi 失败现场 `.tmp/backups/192_scifi_short_regression_failed_20260725-120940/`；定位 Ch8 settlement JSON 输出 4096 token 截断导致 parse failure；`SettlementExtractor` 结构化输出预算提升到 8192；`RUN_ID=192` Ch100 rebuild 默认 `ON_FAILURE=abort`，历史 172b/172c 默认 isolate 不变；scifi end10 复跑 `run-e71bccd8` 10/10 completed、failed=[]、wrapper `PASS_NORMAL_EXIT`；全量 pytest **3004 passed, 2 skipped, 1 xfailed**，ruff 全绿；DONE：`tasks/192.p-scifi-short-regression-context-emergency-DONE.md` |
| V10.2 Task 192.q/r + Ch25 | **192.q/192.r 已完成，Task 192 第一段到 Ch25（2026-07-25）**：192.q 修复 CreativeDirector 未转义内部英文引号导致的 JSON parse failure，同时保持多 JSON 对象拒绝语义；bits-code-guard 最终 review 0 P0/P1/P2；最终全量 pytest **3006 passed, 2 skipped, 1 xfailed**，ruff 全绿；scifi end10 回归 10/10 completed、failed=[]、T9=0、budget_peak 0.979、wrapper PASS_NORMAL_EXIT；192.r 冻结 Ch24 settlement numerical validation failure，resume 后未复现；最终 Ch25 报告 `docs/reports/192-xuanhuan-ch100-climb.md`：25/25 accepted、failed=[]、budget_peak 0.8632、emergency=0、overdue=0、health=9.1、CED/1k=2.0874；wrapper `run-20260725-162600836` PASS_NORMAL_EXIT |
| V10.2 Task 192 Ch50 / 192.s | **Ch50 已完成并清到 T9=0（2026-07-25）**：wrapper `run-20260725-183118441` PASS_NORMAL_EXIT；run `run-2f42e276` completed，Ch1-Ch50 completed，failed=[]，accepted heads 50/50，cost 6.740467；初判 DB SHA256 `5422A2234F1965CD07DEBA1B20CF834E91BA920287203C927B74A467274E90CA`，T9 duplicate=1（Ch8 paragraph 37 duplicates paragraph 22），冻结 `.tmp/backups/192s_xuanhuan_ch50_t9_duplicate_20260725-2132/`；192.s 使用版本化 deterministic clean 创建 Ch8 `clean-8-6-cd06a7b7`（parent `v-d62aa178`），修复后 DB SHA256 `E375918948D8467987FE25138DAD7D16A47EEB82D0E95D7FA22370B34D641926`；复判 T9=0、five-gate PASS、segment audit `critical_orphans=0` / `halt_would_fire=false`；DONE：`tasks/192.s-xuanhuan-ch50-t9-duplicate-clean-DONE.md` |
| V10.2 Task 192 Ch75 / 192.t | **Ch75 已完成并修复到 segment audit PASS（2026-07-26）**：wrapper `run-20260725-214429675` PASS_NORMAL_EXIT；初判 DB `.tmp/task172b_xuanhuan_ch100.db` SHA256 `97D65464F71B30BB065C297CAE09FFF732A13071A902F3A502B08634F0A8E7BF`；run `run-2f42e276` completed，Ch1-Ch75 completed，failed=[]，accepted heads 75/75，cost 10.668106；five-gate Ch75 PASS；T9 Ch75 PASS（meta_artifact=0、duplicate=0、timeline=0）；segment audit 初判 **FAIL**：`critical_orphans=5`、`halt_would_fire=true`，hotspots Ch72=33 / Ch68=25 / Ch73=22；192.t 使用 `SettingTrackingRepository.promote_to_active()` 将 5 条 active critical tracking 刷到 Ch75 accepted version `v-6afe9dd8`，修复后 DB SHA256 `85D1399373E5D3F0FA4DD276C0476EC0407E33396A35696918786AA41173F606`；复判 segment audit **PASS**：`critical_orphans=0`、`halt_would_fire=false`；DONE `tasks/192.t-xuanhuan-ch75-segment-audit-critical-orphans-DONE.md` |
| V10.2 Task 192 Ch81 / 192.u | **Ch81 已完成并修复到 hard gate / segment audit PASS（2026-07-26）**：wrapper `run-20260726-011647464` 触发硬门后被人工 Ctrl-C 中止；初判 DB SHA256 `A9E67CA43BC9FF081E2CE4B3E3FEDE3FD5657B08A776B253EDC90BA9153BFD30`；run `run-2f42e276` Ch1-Ch81 completed，failed=[]，accepted heads 81/81，cost 11.604514；Ch81 初判 gate triggered：`health_low_p1_halt: P1_count=1 (critical orphaned setting)`；P1 target `xuanhuan_lingyuan.technique.lingyuan_quan_first_form`；segment audit 初判 **FAIL**：`critical_orphans=10`、`halt_would_fire=true`；192.u 创建版本化 continuity patch `fix-81-5-214e4cd7`（parent `v-df18b9ed`），刷新 10 条 critical tracking，resolve Ch81 setting marks，并修复 Task 192 默认 `HALT_RETRIES=0` 防止 hard gate 后自动 resume；修复后 DB SHA256 `FA551AE2067CA0DBFCB3FFAD831C8B550B55BA97018E032FDDA24075229DD5F9`；复判 segment audit **PASS**：`critical_orphans=0`、`halt_would_fire=false`；T9=0；five-gate PASS；focused tests 2 passed；ruff PASS；全量 pytest `3006 passed, 2 skipped, 1 xfailed`（wrapper `run-20260726-021612840`）；scifi end10 回归 Ch1-Ch10 completed、failed=[]（wrapper `run-20260726-023003613`）；DONE `tasks/192.u-xuanhuan-ch81-health-low-p1-critical-orphan-DONE.md` |
| V10.2 Task 192 Ch93 / 192.v | **Ch93 已完成并修复到 hard gate / segment audit PASS（2026-07-26）**：wrapper `run-20260726-033037136` `PASS_NORMAL_EXIT`；初判 DB SHA256 `DC62F654AE5764B8212A7620891766350271BFC84549D60EEF050E652BE51459`；run `run-2f42e276` Ch1-Ch93 completed，failed=[]，accepted heads 93/93，total_cost=13.606846；hard gate `health_low_p1_halt: P1_count=1 (critical orphaned setting)`；P1 target `xuanhuan_lingyuan.relationship.guardian_hunter_deception`；segment audit 初判 **FAIL**：`critical_orphans=2`、`total_orphans=74`、`halt_would_fire=true`；192.v 创建版本化 continuity patch `fix-93-6-a98c0576`（parent `v-ef690afa`），刷新 `xuanhuan_lingyuan.relationship.guardian_hunter_deception` 与 `protagonist.spirit.space` 两条 critical tracking，resolve Ch93 P1 mark，并将 run 从 hard-gate `paused` 恢复为可 resume 的 `running`；最终 DB SHA256 `BCA37C47E0C7C5A8725E7C5333635BF9EAF639BE3E5C1D2437C5264C4F10A092`；复判 segment audit **PASS**：`critical_orphans=0`、`halt_would_fire=false`；T9=0；five-gate PASS；DONE `tasks/192.v-xuanhuan-ch93-health-low-p1-critical-orphan-DONE.md` |
| V10.2 Task 192 Ch99 settlement / 192.w | **Ch99 settlement numerical validation 已修复（2026-07-26）**：通过 single-chapter resume runner `.tmp/run_192w_ch99_resume.py` 重跑 Ch99，wrapper `run-20260726-062134627` `PASS_NORMAL_EXIT`；Ch99 accepted/current head `v-34d19e11`，accepted heads 99/99，run failed=[]，DB SHA256 `DAC367B5F88DB84B90394F71F6CB6C0188AC187C7AFECBF833C1C9FCD70DFE08`；T9=0，five-gate PASS；post-fix segment audit @99 **FAIL**：`critical_orphans=4`、`halt_would_fire=true`，已路由 192.x；DONE `tasks/192.w-xuanhuan-ch99-settlement-numerical-validation-DONE.md` |
| V10.2 Task 192 Ch99 segment audit / 192.x | **Ch99 segment audit 已修复到 PASS（2026-07-26）**：创建版本化 continuity patch `fix-99-6-86643cba`（parent `v-34d19e11`），刷新 4 条 critical tracking 到 Ch99 accepted version；最终 DB SHA256 `F61372E46AD6B2ADF6A45DC598F33361179EC59E0D10939C0FB3692651D0FAE6`；复判 segment audit **PASS**：`critical_orphans=0`、`halt_would_fire=false`；T9=0；five-gate PASS；DONE `tasks/192.x-xuanhuan-ch99-segment-audit-critical-orphans-DONE.md` |
| V10.2 Task 192 Ch100 source | **xuanhuan clean Ch100 source 已复核为 CONTINUE_READY（2026-07-26）**：wrapper `run-20260726-064032548` `PASS_NORMAL_EXIT`；run `run-2f42e276` completed，Ch1-Ch100 completed，failed=[]，accepted heads 100/100，total_cost=14.86454；Ch100 accepted/current head `v-c5278e2a`；DB SHA256 `259DA168BD7BE44199A72D74AADE58666494D886EBA58B6096BAAEDA773FC452`；five-gate PASS（budget 0.8632、CED/1k 0.043、overdue 6、health 8.5、gap 0）；segment audit PASS（critical_orphans=0、halt_would_fire=false）；T9=0；profile view `diff_count=0`（DB has no override）；`.tmp/190_ch100_source_inventory.json` 已将 xuanhuan 更新为 `CONTINUE_READY` |
| V10.2 Task 192 Ch105 / 192.y | **Ch105 direct P1 已修复（2026-07-26）**：原 hard gate `health_low_p1_halt` P1 target `xuanhuan_lingyuan.technique.lingyuan_quan_first_form`；创建版本化 continuity patch `fix-105-5-75d18199`（parent `v-04f5c7df`），resolve P1 mark，run 从 paused 恢复为 running；T9=0；post-fix segment audit @105 **FAIL**：`critical_orphans=13`、`halt_would_fire=true`，已路由 192.z；DONE `tasks/192.y-xuanhuan-ch105-health-low-p1-critical-orphan-DONE.md` |
| V10.2 Task 192 Ch105 segment audit / 192.z | **Ch105 segment audit 已修复到 PASS（2026-07-26）**：创建 Ch105 accepted continuity patch `fix-105-6-4cc94f2e`（parent `fix-105-5-75d18199`），刷新 13 条 critical tracking 到 Ch105 accepted version；最终 DB SHA256 `E87011FDE32DD16E439CC13CE442F655F2461C9D7F52D38B1AA0F32A98B21333`；复判 segment audit **PASS**：`critical_orphans=0`、`total_orphans=68`、`halt_would_fire=false`；T9=0；run `running`、failed=[]；DONE `tasks/192.z-xuanhuan-ch105-segment-audit-critical-orphans-DONE.md` |
| V10.2 Task 192 Ch106 invalid model / 192.aa | **invalid model run-state pollution 已清理（2026-07-26）**：恢复 Ch106→Ch125 时 shell 未显式设置 `LLM_MODEL`，链路回退 `deepseek-chat` 并在 Ch106-Ch108 GoalPlanner 前失败；确认 Ch106-Ch108 无 accepted head 后，使用 `ProjectRunRepository.update()` 将 run 恢复为 `current_chapter=105`、`failed=[]`、`status=running`；accepted 仍为 105/105；DB SHA256 `A28A59EF06D0F93DBA33AC0CEF99BBA35CB9E96BA8106062D5D2072154CAC618`；DONE `tasks/192.aa-xuanhuan-ch106-invalid-model-run-state-cleanup-DONE.md` |
| V9.1 阶段 D 实跑验收（2026-07-19） | 熔断实证：¥0.05 预算 ¥0.0514 停（paused + 成本明细 + 章保留），提额 resume 至 completed，成本跨 3 进程 0.0514→0.3647 连续；scifi end10：10/10、0 halt、overdue=0、budget 峰值 0.8325、usage 151 行 estimate 0%、总成本 ¥0.886（≈¥0.089/章）、report 成本视图正确；173 挂死根因确证（sqlite checkpointer 泄漏）真修后 2.5s 自然退出；T9=1（Ch4 countdown_increase，diagnostic 级内容启发式，非系统性） |
| 172c wuxia 段 3 | Ch51-75 完成（75/75 accepted，0 halt）；Ch75 五门：budget PASS、CED FAIL、**overdue 203 vs sci-fi 117 FAIL**、health 5.6 FAIL、completeness PASS |
| 172c.r 修复落地 | resolve 失效四层根因全修：prompt card 1.0.4 补 resolve 契约、settlement 事实源纳 overdue、resolve 防幻觉校验、5.3 同事务覆写修复；health 口径对齐 vdim（archived/dormant/active-overdue 全计）；12 新测试绿 |
| 172c.s Ch21 诊断 | clean rerun Ch1-Ch21 accepted 后 `health_low_streak_halt`：health 5.1、overdue 21（报告 25）、CED/1k 8.9173、budget peak 0.9739、before_emerg_peak 1.2847、resolved/archived=3；根因为 floor=12 长窗口过短 + plant 密度高 |
| 172c.s Ch25 smoke | 第三轮 clean DB project `273a8408be8e4caf8cbc1e91954da600`：25/25 accepted，halt=None，budget peak 0.9646，before-emerg peak 1.2566，overdue 0，health 8.8，resolved/archived 13；`vdim_compare.py 25` 五门 PASS，consistency CED 0.23（20 issues）vs sci-fi 0.33（32 issues） |
| 172c.t / 172c final | clean rerun project `273a8408be8e4caf8cbc1e91954da600`：Ch100 100/100 accepted，halt=None，budget peak 0.965，CED 0.17（58 issues）vs sci-fi 0.40（157 issues），overdue 35 vs 168，health 8.3；`.tmp/vdim_compare.py 100` 五门 PASS |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| `python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10` | 三体裁各 10/10、0 halt；CED 见上（`archive/v8/reports/172a.7-regression-end10.json`） |
| xuanhuan `--end 15`（floor=12） | overdue@<15=2（DB 严证）；Ch1-13 accepted（Ch11 isolate 瞬时） |
| `python -m pytest tests/ -q` | 2691 passed, 2 skipped, 1 xfailed（含 172a.p 13 新测试） |
| `ruff check src/ tests/` | 无新增 error |
| 172b `--to 100` | Ch1-Ch100 100/100 accepted、0 halt；`python .tmp/vdim_compare.py 100` → 五门 PASS |
| 172b.q CED 终判 | xuanhuan 154 consistency issues / 347,290 words = 0.4434；sci-fi 157 / 394,839 = 0.3976；≤ ×1.15 ceiling 0.4573 |
| `python -m pytest tests/ -q --ignore=tests/cli/test_cli.py` | **2746 passed, 2 skipped, 1 xfailed**（395s；172e-172i 新增 41 测试全绿；`tests/cli/test_cli.py` 4 个失败为既有 CLI 输出格式问题，与本次改动无关） |
| 172c wuxia 段 3 实跑（`TEMPLATE_ID=wuxia RUN_ID=172c python scripts/run_172b_ch100_climb.py --to 75`） | 75/75 accepted，0 halt；`.tmp/vdim_compare.py 75` 五门中 budget/completeness PASS，CED/overdue/health FAIL |
| `ruff check src/ tests/` | **All checks passed** |
| 172c.r `python -m pytest tests/ -q` | **2779 passed, 2 skipped, 1 xfailed**（850s；含 172c.r 新增 12 测试） |
| 172c.r `ruff check src/ tests/` | **All checks passed**（含 172c.q 遗留 E501 顺手修复） |
| 172c.r 实跑回归（`run_172a7_genre_validation.py --templates scifi --end 10` + `--templates wuxia --end 15`） | **通过**：scifi 10/10 accepted、8 resolved；wuxia 15/15 accepted、9 resolved、0 failed；结果落盘 `.tmp/172cr_scifi_end10.json` / `.tmp/172cr_wuxia_end15.json` |
| 172c.s 聚焦测试 | `python -m pytest tests/test_172cs_wuxia_health_calibration.py tests/test_172ap_foreshadowing_horizon_floor.py tests/test_continuity_health_governance.py tests/test_continuity_auditor_suggested_marks.py -q` → **49 passed**；相邻 continuity/gate 测试 **75 passed**；`ruff check src/ tests/` 全绿 |
| 172c.s voice-anchor 聚焦测试 | `python -m pytest tests/test_172cs_wuxia_health_calibration.py tests/test_dialogue_style_card.py tests/test_llm_auditor.py -q` → **54 passed** |
| 172c.t 聚焦测试 | `python -m pytest tests/test_172ct_wuxia_health_overdue_weight.py tests/test_123_gates.py::test_health_low_streak_ignores_recovered_health_score -q` → **5 passed** |
| 172c wuxia Ch100 终判 | `$env:TEMPLATE_ID='wuxia'; python .tmp\vdim_compare.py 100` → **PASS**：accepted 100/100，budget 0.965，CED 0.17 vs 0.40，overdue 35 vs 168，health 8.3 |
| 172c 收口全量验证 | `python -m pytest tests/ -q` → **2791 passed, 2 skipped, 1 xfailed**；`ruff check src/ tests/` → **All checks passed** |
| 172k 三档实跑（`run_172a7_genre_validation.py`：xuanhuan end10 / urban end15 / wuxia end20） | **全 accepted**：10/10、15/15、20/20 gap=0；T9=0、overdue=0、budget 峰值 ≤0.9893、0 halt；落盘 `.tmp/172k_xuanhuan_end10.json` / `.tmp/172k_urban_end15.json` / `.tmp/172k_wuxia_end20.json` |
| 173/174 聚焦测试 | `python -m pytest tests/test_173_llm_client_cleanup.py tests/test_174_logging_setup.py -q` → **14 passed**（含 review 修复新增 1 用例） |
| 173/174 全量默认测试 | `python -m pytest tests/ -q` → **2815 passed, 2 skipped, 1 xfailed**（471s；review 修复后复验，含新增关闭失败健壮性用例） |
| 173/174 ruff | `ruff check src/ tests/ scripts/run_172a7_genre_validation.py scripts/run_172b_ch100_climb.py` → **All checks passed** |
| 173/174 真实 smoke 尝试 | `LOG_LEVEL=WARNING` + scifi end1/end2 曾启动；确认 console 无 LiteLLM DEBUG 请求/响应，仅 WARNING；生成链路耗时过长，为控制成本中止，未作为 end10 通过证据 |
| 175 阶段 D 实跑验收（2026-07-19） | 熔断实证：¥0.05 预算 ¥0.0514 停（paused + 明细 + 章保留），提额 resume 至 completed，成本跨 3 进程连续；scifi end10：10/10、0 halt、overdue=0、budget 峰值 0.8325、usage 151 行 estimate 0%、总成本 ¥0.886、report 成本视图正确；173 挂死根因确证（sqlite checkpointer 泄漏）真修后 2.5s 自然退出；T9=1（Ch4 countdown_increase，diagnostic 级，非系统性） |
| 175 全量验证（阶段 D 收尾） | `python -m pytest tests/ -q` → **2882 passed, 2 skipped, 1 xfailed**；`ruff check src/ tests/` → All checks passed |
| 177 导出验收（2026-07-19） | `tests/test_177_export_service.py` **15 passed**（含 review follow-up：不自动迁移源库 + skipped CLI 输出）；全量 pytest（Task 176 wrapper）**2897 passed, 2 skipped, 1 xfailed**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿；xuanhuan Ch100 arc 导出 100 章/4 文件，wuxia Ch100 flat 导出 100 章/1 文件，xuanhuan volume 忽略 `(0,0)` 占位并导出 100 章/2 文件；两库 Ch1/50/100 正文段 hash 与 DB 一致 |
| 178 wheel 打包验收（2026-07-19） | Task 178 资源测试 **6 passed**；资源相关测试组 **137 passed, 1 warning**；全量 pytest（Task 176 wrapper）**2903 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿；`pip wheel --no-deps .` 产出 `songyan-2.0.0-py3-none-any.whl`；非仓库 cwd + wheel install 资源枚举命中 7 genre / 4 mode / 12 template id / prompt cards / literary plugins / `evals/seeds` / `schema.sql`；`create-project --template scifi` 成功；wheel Ch1-3 **3/3 accepted**；scifi end10 **10/10 accepted**、budget 峰值 0.9693、总成本约 ¥0.8744、`t9_issue_count=1`（诊断残留，未写成 T9=0） |
| 179 CLI 体验验收（2026-07-19） | 聚焦 CLI 测试 `tests/test_130_gate_mode.py` + `tests/cli/test_cli.py::TestRunCommandExperience` + `test_index_help` → **12 passed**；默认全量 pytest（Task 176 wrapper）**2903 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿；`bits-code-guard` diff-only review 0 P0/P1/P2；`tests/cli/test_cli.py` 全文件 4 个既有 create-project 失败仍归 Task 181 |
| 180 doctor 验收（2026-07-20） | `tests/cli/test_doctor_command.py` → **12 passed**；默认全量 pytest（Task 176 wrapper）**2903 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿；`bits-code-guard` diff-only review 发现 1 个 P2（schema 只验表名），已修复为关键迁移列/索引 drift 检测并补回归测试 |
| 181 CI/测试清零验收（2026-07-20） | `python -m pytest tests/cli -q` → **35 passed**；`mypy src/` → **Success: no issues found in 172 source files**；`ruff check src/ tests/` 全绿；默认全量 pytest（Task 176 wrapper）**2904 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`bits-code-guard` 分组 review 发现 1 个 P2（zip-backed `outline.json` 未 `as_file()`），已修复并补回归测试；`.github/workflows/ci.yml` 覆盖 ruff/mypy/default pytest/CLI pytest |
| 182 五门工具收编验收（2026-07-20） | `python scripts/five_gate_check.py --genre xuanhuan ... --up-to 100 --format json` → **PASS**（100/100、budget 0.9811、CED 0.4434、overdue 166、health 9.1）；wuxia Ch100 → **PASS**（100/100、budget 0.9646、CED 0.1662、overdue 35、health 8.3）；`.tmp/vdim_compare.py` 对照逐门一致；`scripts/segment_audit.py` 输出 hotspot / next-audit / health trajectory；`tests/test_182_five_gate_tools.py` **10 passed**；默认全量 pytest（Task 176 wrapper）**2914 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；CLI **35 passed**；mypy **174 source files 0 errors**；ruff 全绿；code review P2 已修复 |
| 183 Profile CLI 验收（2026-07-20） | `tests/test_183_profile_cli.py` **7 passed**；`songyan profile show/diff/upsert --genre <g>` 接入；show/diff 只读不创建缺失 DB；upsert 写入“代码默认模型 + 用户显式字段”的 DB profile，避免 registry 调优值误写为 override；`--reset` 清空 override 意图；默认全量 pytest（Task 176 wrapper）**2921 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；CLI **35 passed**；mypy **175 source files 0 errors**；ruff 全绿；code review P2 已修复 |
| 184 JSON Schema 验收（2026-07-20） | `src/songyan/genres/data/_schema.json` + `src/songyan/creative_modes/data/_schema.json` 接入；loader 在 Pydantic 前执行 JSON Schema 校验；7+4 生产资源通过，unknown field / wrong type / invalid enum 被拒；`_schema` 不进入 profile/mode 列表；资源/schema 聚焦测试 **86 passed**；默认全量 pytest（Task 176 wrapper）**2930 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；CLI **35 passed**；mypy **176 source files 0 errors**；ruff 全绿；code review P2 已修复 |
| 185 标定实跑（2026-07-20） | run1（base12000 override）：14/15（Ch13 结算瞬时失败 isolate）、budget 0.8917、emergency 0、T9 原值 12、成本 ¥1.594；run2（同候选 clean rerun）：15/15、budget 0.9396、T9 原值 3、¥1.489；run3（registry 12000、无 override）：**15/15、budget 0.9643、emergency 0、overdue 3、CED 5.46**、¥1.733；终态检测器复测 run3/run2 accepted 正文 **T9=0**（`.tmp/185_t9_recompute_note.json`） |
| 185 scifi end10 回归（2026-07-20） | **10/10 accepted、0 halt、T9=0**、overdue=0、budget 峰值 0.7662、before_emergency 1.2352 未贴 halt 线；T9 诊断残留 1→0 为精度修复预期后果；落盘 `.tmp/185_scifi_end10_regression.json` |
| 185 验证（2026-07-20） | `tests/test_185_t9_precision_fixes.py` **18 passed**（含真拼接/真回跳/换措辞回跳守护）+ harness **4 passed**；默认全量 pytest（Task 176 wrapper）**2952 passed, 2 skipped, 1 xfailed**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；CLI **35 passed**；mypy **176 source files 0 errors**；ruff 全绿 |
| 187 Ch100 终判（2026-07-22） | `scripts/five_gate_check.py --genre urban --up-to 100` → **PASS**：100/100 accepted，budget 0.9595，CED 0.11，overdue 100，health 8.6，gap 0；`scripts/segment_audit.py --up-to 100` → **PASS**：critical_orphans=0、halt_would_fire=false；`songyan metrics --chapters 1-100` → **T9=0**（meta/artifact=0、duplicate=0、timeline=0） |
| 187 收口验证（2026-07-22） | 聚焦测试 `tests/test_185_t9_precision_fixes.py` + `tests/test_162_timeline_consistency.py` → **47 passed**；默认全量 pytest（Task 176 wrapper）**2981 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`；`ruff check src/ tests/` 全绿 |

## 项目整理

- V5/V6/V7 历史报告已归档到 `archive/v5/reports/`、`archive/v6/reports/`、`archive/v7/reports/`。
- Task 170 文学提质中间过程稿已归档到 `archive/v7/tasks/`，入口保留总览与关键 DONE 文档。
- Task 172（Ch250）已归档到 `archive/v7/tasks/172-ch250-transition-validation-archived.md`。
- V8 已全量闭环并归档（2026-07-18）：全部任务文档（172-172l）与报告（172a.1/172a.4/172a.7/172b/172c）迁移至 `archive/v8/`（索引 `archive/v8/INDEX.md`）；`tasks/V8-README.md` 保留为历史事实总索引；`docs/reports/v8-literature-and-landscape-review.md` 保留活跃入口。
- **V8 后续技术债**：172e-172i 已全部完成，覆盖 `GenreRuntimeProfile` 字段接线、回退语义澄清、占位字段移除与文档修复。
- V9 已全量闭环并归档（2026-07-23）：单项任务文档 173-188 迁移至 `archive/v9/`（索引 `archive/v9/INDEX.md`）；`tasks/V9-README.md` 保留为 V9 历史事实总索引。
- 工作区目录已整理（2026-07-23）：`tasks/` 仅保留阶段 README、`TEMPLATE.md` 与未来规划；V5/V6/V7/V9 单项任务文档分别归档到 `archive/v5/tasks/`、`archive/v6/tasks/`、`archive/v7/tasks/`、`archive/v9/`；早期 Superpowers 计划/规格归档到 `archive/superpowers/`。

## 下一步

1. **继续 Task 192 xuanhuan Ch200 climb 到 Ch125（下一步，按编号推进）**：192.z 已修复 Ch105 segment audit blocker，192.aa 已清理 invalid model 失败痕迹；使用 `LLM_MODEL=deepseek/deepseek-v4-flash` + `scripts/run_v10_ch200_climb.py --to 125 --genre xuanhuan` 恢复 Ch106→Ch125，段边界必须先审计再继续，Ch125 five-gate 必须显式传入 `tasks/189-scifi-ch200-baseline.json`。
2. **Task 193 wuxia Ch28 clean + Ch200**：T9=1（Ch28 省略号占位段），需按 `tasks/193-wuxia-ch200-climb.md` 执行版本化 deterministic clean 并重跑 T9 确认 T9=0；其余章节可直接续跑。
3. **Task 194 urban Ch200**：urban 是当前唯一 `CONTINUE_READY` 体裁，可按 `tasks/194-urban-ch200-climb.md` 初始化 V10 Ch200 DB；但在当前 goal 下不得跳过 192/193。
4. **段边界纪律**：Ch125/150/175/200 必须先审计再继续；任一硬门失败时冻结现场并开父任务后缀修复。
5. **守护项**：后续 CED 仍使用 consistency-only、merged/source、正文证据口径；不得把文学 craft 或 `rule-mr-*` 聚合工作项计入 CED；T9 仍不接受解释性豁免；Ch125+ five-gate 必须显式传入 `tasks/189-scifi-ch200-baseline.json`。

## 入口

- **V10 规划入口（V10.2 Task 192 xuanhuan Ch200 climb 中）：`tasks/V10-README.md`**
- V10 Task 189 DONE：`tasks/189-ch200-baseline-and-checkpoints-DONE.md`
- V10 Task 189 baseline：`tasks/189-scifi-ch200-baseline.json`
- V10 Task 189 任务书：`tasks/189-ch200-baseline-and-checkpoints.md`
- V10 Task 190 任务书：`tasks/190-ch100-terminal-source-inventory.md`
- V10 Task 190 DONE：`tasks/190-ch100-terminal-source-inventory-DONE.md`
- V10 Task 190 统一盘点：`.tmp/190_ch100_source_inventory.json`
- V10 Task 191 任务书：`tasks/191-ch200-harness-preparation.md`
- V10 Task 191 DONE：`tasks/191-ch200-harness-preparation-DONE.md`
- V10 Task 191 harness：`scripts/run_v10_ch200_climb.py`
- V10 Task 192 任务书：`tasks/192-xuanhuan-ch200-climb.md`
- V10 Task 192.p DONE：`tasks/192.p-scifi-short-regression-context-emergency-DONE.md`
- V10 Task 192.q DONE：`tasks/192.q-xuanhuan-ch17-creative-director-json-parse-DONE.md`
- V10 Task 192.r DONE：`tasks/192.r-xuanhuan-ch24-settlement-numerical-validation-DONE.md`
- V10 Task 192.s DONE：`tasks/192.s-xuanhuan-ch50-t9-duplicate-clean-DONE.md`
- V10 Task 192.t 任务书：`tasks/192.t-xuanhuan-ch75-segment-audit-critical-orphans.md`
- V10 Task 192.t DONE：`tasks/192.t-xuanhuan-ch75-segment-audit-critical-orphans-DONE.md`
- V10 Task 192.u 任务书：`tasks/192.u-xuanhuan-ch81-health-low-p1-critical-orphan.md`
- V10 Task 192.u DONE：`tasks/192.u-xuanhuan-ch81-health-low-p1-critical-orphan-DONE.md`
- V10 Task 192.v 任务书：`tasks/192.v-xuanhuan-ch93-health-low-p1-critical-orphan.md`
- V10 Task 192.v DONE：`tasks/192.v-xuanhuan-ch93-health-low-p1-critical-orphan-DONE.md`
- V10 Task 192.w 任务书：`tasks/192.w-xuanhuan-ch99-settlement-numerical-validation.md`
- V10 Task 192.w DONE：`tasks/192.w-xuanhuan-ch99-settlement-numerical-validation-DONE.md`
- V10 Task 192.x 任务书：`tasks/192.x-xuanhuan-ch99-segment-audit-critical-orphans.md`
- V10 Task 192.x DONE：`tasks/192.x-xuanhuan-ch99-segment-audit-critical-orphans-DONE.md`
- V10 Task 192.y DONE：`tasks/192.y-xuanhuan-ch105-health-low-p1-critical-orphan-DONE.md`；Task 192.z 任务书：`tasks/192.z-xuanhuan-ch105-segment-audit-critical-orphans.md`；Task 192.z DONE：`tasks/192.z-xuanhuan-ch105-segment-audit-critical-orphans-DONE.md`；Task 192.aa DONE：`tasks/192.aa-xuanhuan-ch106-invalid-model-run-state-cleanup-DONE.md`
- V10 Task 192 Ch75 执行报告：`docs/reports/192-xuanhuan-ch100-climb.md`
- V10 Task 193 任务书：`tasks/193-wuxia-ch200-climb.md`
- V10 Task 194 任务书：`tasks/194-urban-ch200-climb.md`
- V9 任务事实入口（已完成）：`tasks/V9-README.md`
- V9 归档索引：`archive/v9/INDEX.md`
- V9 Task 173-188 单项任务文档：`archive/v9/`
- V9 Task 185 完成报告：`archive/v9/185-urban-short-window-calibration-DONE.md`
- V9 Task 186 任务书：`archive/v9/186-urban-ch100-climb.md`
- V9 Task 187 执行记录：`archive/v9/187-urban-ch100-climb-execution.md`
- V9 Task 187 DONE：`archive/v9/187-urban-ch100-climb-execution-DONE.md`
- V9 Task 188 DONE：`archive/v9/188-v9-closure-and-archive-DONE.md`
- V8 历史任务事实（已收尾，含 V8.5）：`tasks/V8-README.md`
- V8 归档索引（全部任务文档与报告）：`archive/v8/INDEX.md`
- V8 长调研报告（GenreRuntimeProfile 设计依据，活跃参考）：`docs/reports/v8-literature-and-landscape-review.md`
- V9 中篇爬坡冻结口径参照：`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1
- 172k C 判据证据补完（含 V9 urban/wuxia base_budget 标定观察）：`archive/v8/tasks/172k-c-dimension-evidence-closure.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
