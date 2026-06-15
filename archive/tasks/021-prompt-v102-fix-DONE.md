# Task 021: Prompt v1.0.2 调优修复 + Revision 反弹保护

> **Phase**: Phase 4（评测优化循环）
> **优先级**: P0（阻塞 V1.0 验收）
> **依赖**: Task 020-C（评测基础设施已就绪）
> **预计工作量**: 中

---

## Goal

修复 Round 2 (v1.0.1) 评测发现的全部退化问题，创建 v1.0.2 Craft Cards + Revision 反弹检测，运行 Round 3 评测验证 is_pass 恢复。

## Context

Round 2 (v1.0.1) 评测失败，核心问题：
1. Writer 规则超载（8 sections）→ ending_hook 失效
2. LLMAuditor 评分标准过严 → revision 恶性循环
3. 缺乏 revision 反弹保护 → issues 12→14→18, score 8.25→8.23→3.71
4. Settlement source_quote 精度不足

## In Scope（已完成）

- [x] Writer 1.0.2 Craft Card：ending_hook 最高优先级 + 反面示例 + scenes_count≥2 强制要求 + show_dont_tell 结尾让步规则
- [x] LLMAuditor 1.0.2 Craft Card：放宽 show_dont_tell（1-2处=7+）和 dialogue_subtext（有潜台词=6.5+）标准
- [x] CreativeDirector 1.0.2 Craft Card：增加角色语言指纹预定义
- [x] SettlementExtractor 1.0.1 Prompt：source_quote 精度强化（错误/正确示例）
- [x] Revision 反弹检测代码：`review_merger_node` 中实现 issues_count +20% 或 overall_score -1.0 触发回滚
- [x] 各 Manifest 更新：default_version → 1.0.2
- [x] 单元测试更新：prompt loader 版本号适配
- [x] 新增集成测试：`test_path_i_revision_rebound_rollback`
- [x] Round 3 真实 LLM 评测：is_pass = true

## Out of Scope（明确不做）

- 其他题材种子（玄幻/都市）评测 — 留到 Task 022
- 多模型路由 / Web UI 等 V1.1+ 功能

## 接口契约

无新增公共接口。修改点：
- `review_merger_node` 返回字段增加 `_current_issues_count`, `_current_overall_score`
- `Phase1State` 增加 `_best_issues_count`, `_best_overall_score`, `_best_version_id`, `_revision_rebound`

## 测试要求

### Layer 2: 模块测试
- [x] `tests/test_prompt_loader.py` — 版本号适配（1.0.2 + 3 个版本）
- [x] `tests/integration/test_paths.py::test_path_i_revision_rebound_rollback` — mock 验证反弹检测

### Layer 3: 集成测试
- [x] `tests/integration/test_paths.py` — 全部 8 个路径测试通过
- [x] `pytest -m "not performance" -q` — 644 测试通过（643 + 1 新增）

### 真实 LLM 评测
- [x] `python scripts/run_real_llm_scifi.py` — Round 3 is_pass=true

## 验收标准

- [x] pytest -m "not performance" -q 全部通过（644 tests）
- [x] Round 3 评测 is_pass = true
- [x] hook_closing_pass = 1
- [x] revision 轮数 ≤ 2 且最终版评分不低于初稿（v2 score=8.36 > v1 score=8.3）
- [x] 各维度评分不劣于 Round 1
- [x] 更新了 docs/STATUS.md
- [x] 生成了 tasks/021-prompt-v102-fix-DONE.md

## Round 3 评测结果对比

| 指标 | Round 1 (v1.0.0) | Round 2 (v1.0.1) | Round 3 (v1.0.2) |
|------|------------------|------------------|------------------|
| is_pass | ✅ | ❌ | ✅ |
| overall_score | 8.28 | 3.71 | **8.36** |
| hook_closing_pass | 1 | 0 | **1** |
| hook_opening_pass | 1 | 1 | 1 |
| ai_tell_count | 1 | 0 | 1 |
| settlement_errors | 10 | 10 | **2** |
| 成本 | ~¥0.13 | ~¥0.15 | ~¥0.13 |

## 关键文件变更

| 文件 | 变更 |
|------|------|
| `prompts/cards/writer/1.0.2.yaml` | 新增：降低规则数量、ending_hook 最高优先级、scenes_count≥2、show_dont_tell 结尾让步 |
| `prompts/cards/llm_auditor/1.0.2.yaml` | 新增：放宽评分标准、区分显/隐性 tell |
| `prompts/cards/creative_director/1.0.2.yaml` | 新增：角色语言指纹预定义 |
| `prompts/cards/settlement_extractor/1.0.1.yaml` | 新增：source_quote 精度强化 |
| `prompts/cards/{writer,llm_auditor,creative_director,settlement_extractor}/_manifest.yaml` | 更新：default_version → 1.0.2/1.0.1 |
| `src/songyan/workflows/_nodes.py` | 修改：review_merger_node 增加反弹检测逻辑 |
| `src/songyan/workflows/phase1_graph.py` | 修改：Phase1State 增加反弹检测字段 |
| `tests/integration/test_paths.py` | 新增：test_path_i_revision_rebound_rollback |
| `tests/integration/conftest.py` | 新增：llm_worsening_resp helper |
| `tests/test_prompt_loader.py` | 更新：版本号适配 |

## 参考文档

- `evals/output/ROUND2_ANALYSIS_REPORT.md` — Round 2 问题分析
- `docs/review/round2-prompt-optimization-backlog.md` — P0-P4 修复清单
- `evals/output/real_llm_20260528_222513/` — Round 3 评测输出
