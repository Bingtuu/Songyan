# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V9-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | **V9 已开工**：生产化地基 + urban 第三体裁 Ch100，Task 173-188 扁平编号，事实入口 `tasks/V9-README.md`。**V9.1 长跑可靠性全部完成**（173/174/175/176 ✅）；**V9.2 Task 177/178/179/180 ✅ 完成**：`songyan export` 已能从 accepted head 导出 flat/arc/volume Markdown/txt 纯净书稿；wheel 打包与资源加载已修复并通过非仓库 cwd 验收；CLI 三坑已修复；`songyan doctor` 已上线；下一步 Task 181 CI 上线与测试清零 |
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
| V9 生产化地基 | 173：显式 LLM client registry + `aclose_llm_clients()`，pipeline 收尾对称关闭 LLM client + sqlite checkpointer，`SONGYAN_FORCE_EXIT` 最外层兜底；174：`configure_logging()` 接入 CLI + harness，`logs/app/*.jsonl` 落盘，第三方 WARNING 起，关键字段与 `logs/chapter_runs` 对齐；175：`llm_call_usage` 逐调用落库（token/cost 双来源标记、按重试尝试计行、agent 归因），`run_cost_budget` 双检查熔断（DB 权威）+ `total_cost` 双接线，`songyan report` 成本视图；177：`songyan export` 正式 service + CLI，accepted head 正文导出，支持 `md/txt` 与 `flat/arc/volume`，xuanhuan/wuxia Ch100 实库验收通过；178：运行资源迁入包内并用 `importlib.resources` 加载，`evals/seeds` 与 `schema.sql` 入 wheel，非仓库 cwd 资源枚举 + `create-project` + Ch1-3 生成通过；179：`songyan run` 输出 `run_id`，`--mode-id` 默认回读项目 mode，README CLI 表补 `index`；180：`songyan doctor` 默认无成本只读自检，支持 JSON、显式 DB 初始化与 LLM client 探针 |
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

## 项目整理

- V5/V6/V7 历史报告已归档到 `archive/v5/reports/`、`archive/v6/reports/`、`archive/v7/reports/`。
- Task 170 文学提质中间过程稿已归档到 `archive/v7/tasks/`，入口保留总览与关键 DONE 文档。
- Task 172（Ch250）已归档到 `archive/v7/tasks/172-ch250-transition-validation-archived.md`。
- V8 已全量闭环并归档（2026-07-18）：全部任务文档（172-172l）与报告（172a.1/172a.4/172a.7/172b/172c）迁移至 `archive/v8/`（索引 `archive/v8/INDEX.md`）；`tasks/V8-README.md` 保留为历史事实总索引；`docs/reports/v8-literature-and-landscape-review.md` 保留活跃入口。
- **V8 后续技术债**：172e-172i 已全部完成，覆盖 `GenreRuntimeProfile` 字段接线、回退语义澄清、占位字段移除与文档修复。

## 下一步

1. **V9.2 交付与发布（181）**：177 export、178 wheel 打包/资源加载、179 CLI 三坑、180 doctor 环境自检已完成；下一步 Task 181 CI 上线与测试清零，详见 `tasks/V9-README.md`。
2. **V10 预登记**：跨体裁 Ch200（基线扩 Ch200 checkpoint + 口径冻结）、优秀度信号包（跨章同质化指数/中文 AI 腔规则包/judge 偏差对策/perplexity gate/style card）、结构升级 spike（KG 图 diff / validity interval / Storyline Tree）。
3. **守护项**：后续 CED 仍使用 consistency-only、merged/source、正文证据口径；不得把文学 craft 或 `rule-mr-*` 聚合工作项计入 CED。

## 入口

- **V9 任务事实入口（已开工）：`tasks/V9-README.md`**
- V9 Task 173 DONE：`tasks/173-interpreter-exit-hang-fix-DONE.md`
- V9 Task 174 DONE：`tasks/174-logging-system-foundation-DONE.md`
- V9 Task 175 DONE：`tasks/175-cost-tracking-and-budget-circuit-breaker-DONE.md`
- V9 Task 176 DONE：`tasks/176-windows-anti-hang-wrapper-DONE.md`
- V9 Task 177 DONE：`tasks/177-export-book-manuscript-DONE.md`
- V9 Task 178 DONE：`tasks/178-wheel-packaging-resource-loading-DONE.md`
- V9 Task 179 DONE：`tasks/179-cli-experience-fixes-DONE.md`
- V9 Task 180 DONE：`tasks/180-doctor-environment-check-DONE.md`
- V8 历史任务事实（已收尾，含 V8.5）：`tasks/V8-README.md`
- V8 归档索引（全部任务文档与报告）：`archive/v8/INDEX.md`
- V8 长调研报告（GenreRuntimeProfile 设计依据，活跃参考）：`docs/reports/v8-literature-and-landscape-review.md`
- V9 中篇爬坡冻结口径参照：`archive/v8/tasks/172b-xuanhuan-ch100-climb.md` §1.1
- 172k C 判据证据补完（含 V9 urban/wuxia base_budget 标定观察）：`archive/v8/tasks/172k-c-dimension-evidence-closure.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
