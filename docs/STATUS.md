# Songyan 项目状态

> 短状态板。这里只保留当前判断、最新证据和下一步，避免挤占开发上下文。任务细节看 `tasks/V7-README.md`，文档路由看 `docs/INDEX.md`，长历史看 `archive/`。

## 当前判断

| 项 | 结论 |
|----|------|
| 当前阶段 | V7 阶段 Z：Ch200 已完成，171v 文学护栏小窗口未通过出口 |
| 是否可进入 172 | **否**。必须先做 `171w / 171v-hardening`，再重验 Ch201-Ch220 |
| 主线事实 | Task 171 Ch200：run `run-fb39245c`，200/200 accepted，gaps=[]，Halt=None |
| D1 洁净度 | 171t/171u 后 Ch200 accepted head 达成 D1 hard clean pass：T9 meta/artifact=0、duplicate=0，T6b critical orphan peak=0 |
| 171v 小窗口 | run `run-e27b763f`，Ch201-Ch220 partial：19/20 accepted，failed=[207]，Halt=None |
| 171v 判定 | 护栏已进入 planning/prompt 链路，但未稳定改变正文输出 |
| 当前风险 | P0/P1 工程风险为 0；当前阻塞是 171v 出口未达标，不是 Ch200 主线回退 |

## 最新证据

| 维度 | 事实 |
|------|------|
| 小窗口稳定性 | Ch201-Ch220 完成 19/20；Ch207 被 isolate，run 状态 partial；无 AutoHalt |
| Ch207 失败原因 | Settlement 数值校验：`escape_pod_communication_array_integrity closing_value (0.0) != formula (63.000)`，进入 `settlement_review` |
| T9 hard clean | accepted 19 章 meta/artifact=0、duplicate=0，D1 洁净护栏继续有效 |
| 171v 注入 | CreativeDirector 对 Ch201-Ch220 20/20 注入 171v 护栏；Ch205/210/215/220 均注入“配角独立目标护栏” |
| 角色主动性 | accepted 19 章 `character_autonomy_score` 均值约 2.816，10/19 章低于 3.0 |
| 配角目标 | 4/4 次注入，但正文命中 0；Ch210 约束配角为“指挥官”，正文中也未出现 |
| 概念密度 | 多章新增设定数 >1，Ch217 达到 9；概念预算尚未形成有效约束 |
| 母题疲劳 | 有改善但未清零；后段出现若干 `motif_fatigue_count=0`，但多章仍为 1/2 |
| 报告口径 | `docs/reports/task-171-ch200-long-run-report.md` 已恢复 Ch1-Ch200 的 200/200 主报告口径 |

## 最近验证

| 命令 / 证据 | 结果 |
|-------------|------|
| `python -m pytest tests/test_171v_literary_guardrails.py tests/test_creative_director.py tests/test_writer.py tests/test_rule_auditor.py -q` | 173 passed |
| `python -m pytest tests/test_171v_literary_guardrails.py tests/test_108_core_nodes.py tests/test_rule_auditor.py -q` | 100 passed |
| `python -m pytest tests/ -q` | 2600 passed, 2 skipped, 1 xfailed, 2 warnings |
| `ruff check src/ tests/` | passed |
| Ch201-Ch220 live window | run `run-e27b763f` partial，19/20 accepted，failed=[207] |

## 下一步

1. **开 171w / 171v-hardening**：不要进入 172。
2. 修复/强化四个点：
   - 171v 结构化字段持久化到 `creative_briefs`，并保留到 revision/accepted metadata；
   - 配角目标从“注入建议”升级为可验证的必达约束，优先使用已入库核心配角；
   - 为主动选择和概念预算增加 observe 检测，避免只在 prompt 中出现；
   - 诊断 Ch207 settlement 数值校验失败，避免重验窗口继续留下非文学缺口。
3. 重跑 Ch201-Ch220。通过条件：20/20 accepted、T9=0、配角目标落正文、主动性不再连续低位、概念密度受控。
4. 只有 171v 重验通过后，才启动 Task 172 Ch250。

## 入口

- V7 任务事实：`tasks/V7-README.md`
- 当前任务规格：`tasks/171v-ch200-plus-literary-readability-guardrails.md`
- Ch200 主报告：`docs/reports/task-171-ch200-long-run-report.md`
- Ch200 分析：`docs/reports/task-171-ch200-analysis-and-next-step-report.md`
- 文学框架：`docs/reports/v7-literary-framework-review.md`
- 文档索引：`docs/INDEX.md`
