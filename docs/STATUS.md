# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V7-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | V7 阶段 Z：Ch200 已完成，171w 硬化已闭环，可评估进入 172 |
| 是否可进入 172 | **是**。Ch201-Ch220 20/20 accepted，Ch207 settlement 缺口已修复；171w-a/b/c/d 四工作包全部落地 |
| 主线事实 | Task 171 Ch200：run `run-fb39245c`，200/200 accepted，gaps=[]，Halt=None |
| D1 洁净度 | 171t/171u 后 Ch200 accepted head 达成 D1 hard clean pass：T9 meta/artifact=0、duplicate=0，T6b critical orphan peak=0 |
| 171v 小窗口 | run `run-e27b763f`，Ch201-Ch220 **20/20 accepted，failed=[], Halt=None, status=completed** |
| 171w 进展 | 171w-a 报告脚本参数化 / 171w-b 持久化审计 / 171w-c 正文 observe + ReviewMerger 接线 / 171w-d Ch207 settlement 修复 + 重验均已落地 |
| 当前风险 | P0/P1 工程风险为 0；171w 四个工作包全部落地，可启动 Task 172 Ch250 |

## 最新证据

| 维度 | 事实 |
|------|------|
| 小窗口稳定性 | Ch201-Ch220 **20/20 accepted，failed=[], Halt=None, status=completed** |
| Ch207 修复 | Settlement 数值闭合：解析层 + 验证层双层兜底，LLM 返回 closing_value=0.0 时自动从公式推导；已 accept（`rev-207-7-edf1218b`） |
| T9 hard clean | accepted 20 章 meta/artifact=0、duplicate=0，D1 洁净护栏继续有效 |
| 171v 护栏持久化 | `creative_briefs` 四字段（protagonist_active_choice / new_concept_budget / fatigue_motif_replacements / supporting_character_goal）已完整持久化，可回读审计 |
| 配角目标检测 | 正文 observe 已硬化；ReviewMerger 接线将缺失升级为 major patchable issue（CHARACTER_BEHAVIOR） |
| 报告口径 | Ch200 主报告 run_id 已校准为 `run-fb39245c`；脚本支持 `--run-id` / `--output` / `--include-legacy-harness`；旧 V6 harness 表默认不输出 |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| `python -m pytest tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_rule_auditor.py -q` | 173 passed |
| `python -m pytest tests/test_171v_literary_guardrails.py tests/test_108_core_nodes.py tests/test_rule_auditor.py -q` | 100 passed |
| `python -m pytest tests/ -q` | 2602 passed, 2 skipped, 1 xfailed, 2 warnings |
| `ruff check src/ tests/` | passed |
| `python -m pytest tests/db/test_schema.py tests/db/test_review_settlement_repository.py tests/test_revision_handler.py tests/test_171v_literary_guardrails.py -q` | 120 passed |
| `python -m pytest tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py -q` | 209 passed |
| `python -m pytest tests/test_settlement_extractor.py -q` | 132 passed, 1 xfailed |
| `python -m pytest tests/test_171w_text_guardrail_observe.py -q` | 12 passed |
| `python -m pytest tests/test_171w_text_guardrail_observe.py tests/test_171w_guardrail_persistence.py tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_revision_handler.py tests/db/test_schema.py tests/db/test_review_settlement_repository.py tests/test_108_core_nodes.py -q` | 233 passed |
| `ruff check src/ tests/` | passed |
| Ch201-Ch220 171w-d 重验 | 20/20 accepted, failed=[], Halt=None, status=completed |

## 下一步

1. 171w 四个工作包（a/b/c/d）已全部落地，Ch201-Ch220 20/20 accepted。
2. 可启动 Task 172 Ch250 长跑验证。

## 入口

- V7 任务事实：`tasks/V7-README.md`
- 171v 任务事实：`tasks/171v-ch200-plus-literary-readability-guardrails.md`
- 当前 hardening 规格：`tasks/171w-171v-hardening-and-ch201-ch220-rerun.md`
- Ch200 主报告：`docs/reports/task-171-ch200-long-run-report.md`
- Ch201-Ch220 窗口报告：`docs/reports/task-171w-ch201-ch220-window-report.md`
- Ch200 分析：`docs/reports/task-171-ch200-analysis-and-next-step-report.md`
- 文学框架：`docs/reports/v7-literary-framework-review.md`
- 文档索引：`docs/INDEX.md`
