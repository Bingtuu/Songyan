# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V8-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | **V8 已完成验收并完成 172c 增强收口**：P/C/Q/S/V 五维全绿；xuanhuan + wuxia 两个非 sci-fi 体裁均已达成 Ch100 五门 PASS |
| V7 收尾 | **已完成**。sci-fi/space_opera + webnovel_intense 单一体裁稳定跑到 Ch200，200/200 accepted，D1 hard clean pass；Ch201-Ch220 20/20 accepted |
| V8.1 运行时画像 | **已完成**（Task 172a + 172a.p）。`GenreRuntimeProfile` 把 Context Diet 2.0 运行时契约从 sci-fi 默认值解耦；xuanhuan Ch8 halt 已消除（base_budget=15000） |
| V8.3 文学护栏 | **已完成**（Task 172d）。`literary_guardrail_observe` 去科幻硬编码，lexicon/主角名参数化到 `GenreProfile`，三体裁各配一套；DONE 文档已补齐 |
| V8 当前主线 | **Task 172c 已完成**：wuxia clean rerun Ch1-Ch100 100/100 accepted，0 halt，budget/CED/overdue/health/completeness 五门 PASS |
| V8 验收进度 | **P/C/Q/S/V 五维度已实证达标** |
| V8 文档治理 | **已完成**：`tasks/V8-README.md` 已明确 Task 编号是 trace id；阶段任务、前置并行、撞墙修复、后续增强已分层展示 |
| **V8 技术债** | **172e-172i 已完成**：`GenreRuntimeProfile` 声明后未接线的字段已全部接到消费者；`load_profile()` 已改为注册表基线 + DB 字段级覆盖层 |

## 最新证据

| 维度 | 事实 |
|------|------|
| P 可插拔 | scifi profile 全默认 → 逐值回退旧行为；scifi --end 10 10/10、overdue=0、budget Ch1=8250=legacy 公式 |
| C 完成度 | scifi/wuxia/urban `--end 10` 各 **10/10 accepted**；xuanhuan `--end 15` 14–15/15（Ch2 瞬时 LLM JSON 错误，非系统性） |
| Q 质量同标 | CED：wuxia 8.48 < urban 8.75 < scifi 9.60 < xuanhuan 10.48（同量级）；全体裁 budget<1.0、T9=0、0 halt |
| S 状态可控 | 172a.p horizon floor=12：floor12 实跑 DB 严证 **overdue@<15 = 2 < 5**（vs floor=0 的 28），44 伏笔 0 floor 违规 + 数学下界证明 |
| V 中篇爬坡 | 172b xuanhuan Ch1-Ch100 **100/100 accepted**；172c wuxia Ch1-Ch100 **100/100 accepted**；两个非 sci-fi 体裁 Ch100 五门 PASS |
| 172c wuxia 段 3 | Ch51-75 完成（75/75 accepted，0 halt）；Ch75 五门：budget PASS、CED FAIL、**overdue 203 vs sci-fi 117 FAIL**、health 5.6 FAIL、completeness PASS |
| 172c.r 修复落地 | resolve 失效四层根因全修：prompt card 1.0.4 补 resolve 契约、settlement 事实源纳 overdue、resolve 防幻觉校验、5.3 同事务覆写修复；health 口径对齐 vdim（archived/dormant/active-overdue 全计）；12 新测试绿 |
| 172c.s Ch21 诊断 | clean rerun Ch1-Ch21 accepted 后 `health_low_streak_halt`：health 5.1、overdue 21（报告 25）、CED/1k 8.9173、budget peak 0.9739、before_emerg_peak 1.2847、resolved/archived=3；根因为 floor=12 长窗口过短 + plant 密度高 |
| 172c.s Ch25 smoke | 第三轮 clean DB project `273a8408be8e4caf8cbc1e91954da600`：25/25 accepted，halt=None，budget peak 0.9646，before-emerg peak 1.2566，overdue 0，health 8.8，resolved/archived 13；`vdim_compare.py 25` 五门 PASS，consistency CED 0.23（20 issues）vs sci-fi 0.33（32 issues） |
| 172c.t / 172c final | clean rerun project `273a8408be8e4caf8cbc1e91954da600`：Ch100 100/100 accepted，halt=None，budget peak 0.965，CED 0.17（58 issues）vs sci-fi 0.40（157 issues），overdue 35 vs 168，health 8.3；`.tmp/vdim_compare.py 100` 五门 PASS |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| `python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10` | 三体裁各 10/10、0 halt；CED 见上（`docs/reports/172a.7-regression-end10.json`） |
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

## 项目整理

- V5/V6/V7 历史报告已归档到 `archive/v5/reports/`、`archive/v6/reports/`、`archive/v7/reports/`。
- Task 170 文学提质中间过程稿已归档到 `archive/v7/tasks/`，入口保留总览与关键 DONE 文档。
- Task 172（Ch250）已归档到 `archive/v7/tasks/172-ch250-transition-validation-archived.md`。
- V8 新产物：172a.1 常量审计 + scifi baseline、172a.4 预算解耦、172a.7 多体裁矩阵报告、172b Ch100 报告，均在 `docs/reports/`；172a.p/172b/172b.p/172b.q/172d 任务书在 `tasks/`；Task 编号治理规则已内嵌到 `tasks/V8-README.md`。
- **V8 后续技术债**：172e-172i 已全部完成，覆盖 `GenreRuntimeProfile` 字段接线、回退语义澄清、占位字段移除与文档修复。

## 下一步

1. **V8 技术债清理**：✅ 已完成（172e-172i）。`GenreRuntimeProfile` 声明后未接线的字段已全部接到消费者；`load_profile()` 已改为注册表基线 + DB 字段级覆盖层；`arc_summarization_enabled` / `outline_dimming_enabled` / `mismatch_tolerance` 占位字段已移除。
2. **V8 收口**：172b 已达标，V8 五维验收全绿；保持 `tasks/V8-README.md` 为事实入口，并按其中的编号治理规则维护后续任务。
3. **172c 主线**：✅ 已完成。wuxia clean rerun Ch100 五门 PASS；事实入口见 `tasks/172c-wuxia-ch100-clean-rerun-DONE.md` 与 `docs/reports/172c-wuxia-ch100-climb.md`。
4. **后续方向**：urban 第三体裁 Ch100、跨体裁 Ch200、按体裁深度调参划归 V9 或后续任务。
5. **守护项**：后续 CED 仍使用 consistency-only、merged/source、正文证据口径；不得把文学 craft 或 `rule-mr-*` 聚合工作项计入 CED。

## 入口

- V8 任务事实：`tasks/V8-README.md`
- Task 172 完成报告：`tasks/172-project-template-plugin-DONE.md`
- Task 172a 规划：`tasks/172a-v8-genre-runtime-profiles.md`
- Task 172a.7 短窗口验证报告：`docs/reports/172a.7-genre-short-window-validation.md`
- Task 172a.p 伏笔 horizon 下限：`tasks/172a.p-foreshadowing-horizon-floor.md`
- Task 172b Ch100 爬坡：`tasks/172b-xuanhuan-ch100-climb.md`
- Task 172b Ch100 报告：`docs/reports/172b-xuanhuan-ch100-climb.md`
- Task 172b.q CED 终段修复：`tasks/172b.q-consistency-ced-repair.md`
- Task 172c wuxia Ch100 爬坡：`tasks/172c-wuxia-ch100-climb.md`
- Task 172c wuxia Ch100 修复后干净重跑：`tasks/172c-wuxia-ch100-clean-rerun.md` / `tasks/172c-wuxia-ch100-clean-rerun-DONE.md`（已完成）
- Task 172c.p wuxia 物品追踪修复：`tasks/172c.p-wuxia-forgotten-inventory-tracking.md`
- Task 172c.q wuxia 物品身份语义补强：`tasks/172c.q-wuxia-inventory-identity.md`
- Task 172c.r wuxia 伏笔回收与 continuity 健康度修复：`tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix.md` / `tasks/172c.r-wuxia-foreshadowing-resolve-and-health-fix-DONE.md`（已完成）
- Task 172c.s wuxia 长窗口伏笔 horizon 与 continuity health 校准：`tasks/172c.s-wuxia-long-window-foreshadowing-and-health-calibration.md`（已完成）
- Task 172c.t wuxia health overdue 权重长窗口校准：`tasks/172c.t-wuxia-health-overdue-weight-calibration.md`（已完成）
- Task 172d 文学护栏跨体裁化：`tasks/172d-cross-genre-literary-guardrails.md`
- V8 运行时契约补完（172e-172i）：
  - `tasks/172e-context-manager-profile-wiring.md`
  - `tasks/172f-evaporation-profile-wiring.md`
  - `tasks/172g-character-decay-profile-wiring.md`
  - `tasks/172h-continuity-profile-wiring.md`
  - `tasks/172i-profile-fallback-semantics-and-docs.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
