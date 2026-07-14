# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V8-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | **V8**：多体裁可插拔质量 + 章数爬坡 |
| V7 收尾 | **已完成**。sci-fi/space_opera + webnovel_intense 单一体裁稳定跑到 Ch200，200/200 accepted，D1 hard clean pass；Ch201-Ch220 20/20 accepted |
| V8.1 运行时画像 | **已完成**（Task 172a + 172a.p）。`GenreRuntimeProfile` 把 Context Diet 2.0 运行时契约从 sci-fi 默认值解耦；xuanhuan Ch8 halt 已消除（base_budget=15000） |
| V8.3 文学护栏 | **代码完成**（Task 172d）。`literary_guardrail_observe` 去科幻硬编码，lexicon/主角名参数化到 `GenreProfile`，三体裁各配一套 |
| V8 当前主线 | **Task 172b**：xuanhuan Ch100 中篇爬坡（V 维度），实跑进行中 |
| V8 验收进度 | P/C/Q/S 四维度已实证达标；V 维度（Ch100 爬坡）进行中 |

## 最新证据

| 维度 | 事实 |
|------|------|
| P 可插拔 | scifi profile 全默认 → 逐值回退旧行为；scifi --end 10 10/10、overdue=0、budget Ch1=8250=legacy 公式 |
| C 完成度 | scifi/wuxia/urban `--end 10` 各 **10/10 accepted**；xuanhuan `--end 15` 14–15/15（Ch2 瞬时 LLM JSON 错误，非系统性） |
| Q 质量同标 | CED：wuxia 8.48 < urban 8.75 < scifi 9.60 < xuanhuan 10.48（同量级）；全体裁 budget<1.0、T9=0、0 halt |
| S 状态可控 | 172a.p horizon floor=12：floor12 实跑 DB 严证 **overdue@<15 = 2 < 5**（vs floor=0 的 28），44 伏笔 0 floor 违规 + 数学下界证明 |
| V 中篇爬坡 | 172b xuanhuan Ch100 爬坡进行中（budget 曲线 <1.0、0 halt） |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| `python scripts/run_172a7_genre_validation.py --templates scifi wuxia urban --end 10` | 三体裁各 10/10、0 halt；CED 见上（`docs/reports/172a.7-regression-end10.json`） |
| xuanhuan `--end 15`（floor=12） | overdue@<15=2（DB 严证）；Ch1-13 accepted（Ch11 isolate 瞬时） |
| `python -m pytest tests/ -q` | 2691 passed, 2 skipped, 1 xfailed（含 172a.p 13 新测试） |
| `ruff check src/ tests/` | 无新增 error |
| 172b `--to 100`（进行中） | Ch1-4 accepted、budget 0.5-0.77、0 halt（`scripts/run_172b_ch100_climb.py`） |

## 项目整理

- V5/V6/V7 历史报告已归档到 `archive/v5/reports/`、`archive/v6/reports/`、`archive/v7/reports/`。
- Task 170 文学提质中间过程稿已归档到 `archive/v7/tasks/`，入口保留总览与关键 DONE 文档。
- Task 172（Ch250）已归档到 `archive/v7/tasks/172-ch250-transition-validation-archived.md`。
- V8 新产物：172a.1 常量审计 + scifi baseline、172a.4 预算解耦、172a.7 多体裁矩阵报告，均在 `docs/reports/`；172a.p/172b/172d 任务书在 `tasks/`。

## 下一步

1. **172b Ch100 爬坡**（进行中）：等分段（Ch25/50/75/100）指标，对标 sci-fi Ch1-100 基线；达标即 V 维度收尾、V8 五维度全绿。
2. 若 172b 中途撞墙 → 按 `172b.p` 定点修复（不放宽口径）。
3. 172b 达标后 → **172c** 第二体裁（wuxia，已预置 horizon_floor=12）Ch100 爬坡。

## 入口

- V8 任务事实：`tasks/V8-README.md`
- Task 172 完成报告：`tasks/172-project-template-plugin-DONE.md`
- Task 172a 规划：`tasks/172a-v8-genre-runtime-profiles.md`
- Task 172a.7 短窗口验证报告：`docs/reports/172a.7-genre-short-window-validation.md`
- Task 172a.p 伏笔 horizon 下限：`tasks/172a.p-foreshadowing-horizon-floor.md`
- Task 172b Ch100 爬坡：`tasks/172b-xuanhuan-ch100-climb.md`
- Task 172d 文学护栏跨体裁化：`tasks/172d-cross-genre-literary-guardrails.md`
- V7 归档：`archive/v7/INDEX.md`
- V6 归档：`archive/v6/INDEX.md`
- V5 归档：`archive/v5/INDEX.md`
