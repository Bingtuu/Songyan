# Task 058d: Revision 收敛性修复 + 058c 效果验证 — DONE

> **完成日期**: 2026-06-04
> **状态**: ✅ 已完成
> **测试基线**: 1107 passed, 0 failed

---

## 做了什么

### P1 — `new_issues_introduced` 检测修复

修复了 RevisionHandler 引入新问题不被检测的代码 bug（`new_issues_introduced` 被硬编码为 `[]`）。

**修改文件**:

| 文件 | 修改内容 |
|------|---------|
| `src/songyan/agents/revision_handler/__init__.py` | 新增 `_detect_new_issues()` 函数（4 维度检测），修改 `_build_revision_output()` 和 `run_revision()` 传入 rule results |
| `src/songyan/workflows/_nodes.py` | `revision_handler_node`: 保存 revision 后对新版本运行 RuleAudit，重建 `RevisionOutput`；`review_merger_node`: 反序列化 `_new_issues_introduced` 并传入 `merge_reviews` |
| `src/songyan/workflows/review_merger.py` | `merge_reviews()`: 新增 `previous_new_issues` 参数，合并到 `all_issues` |
| `src/songyan/workflows/phase1_graph.py` | `Phase1State`: 新增 `_new_issues_introduced: list[dict] \| None` 字段，初始化默认值 |

**检测维度**:
- AI 腔增加 (`ai_tell_count`) → `SHOW_DONT_TELL` / major
- 疲劳词增加 (`fatigue_word_count`) → `DESCRIPTION_SENSORY` / major
- 首屏钩子丢失 (`has_opening_hook` True→False) → `NARRATIVE_HOOK` / critical
- 章末钩子丢失 (`has_ending_hook` True→False) → `NARRATIVE_HOOK` / critical

**新增测试**: 20 个（全部通过）
- `TestDetectNewIssues` (8 tests)
- `TestBuildRevisionOutputWithNewIssues` (3 tests)
- `TestMergeReviewsPreviousNewIssues` (3 tests)
- `TestNewIssuesIntroducedFlow` (4 tests)
- `tests/test_review_merger.py` (2 tests)

### P1 — 058c 效果验证

基于 058b 30 章基线数据（133,440 字）完成效果评估报告。

**关键基线数据**:
- 平均 revision 轮次: 1.79
- 字数 CV: 17.7%
- 平均 RuleAudit 得分: 0.95
- 平均 LLM audit issues: 7.38

**理论预期**（待 V3.1 大规模验证）:
- 字数超标率应降低（Writer Prompt 威慑 + RuleAuditor 强制检测）
- Ch35+ budget_used 应稳定在 <3.0x（上下文膨胀 4 项修复）
- Round 2 revision 引入新问题应减少（058d 检测 + 合并）

**验证报告**: `docs/review/058d_validation_report.md`

---

## 不做什么（与任务文档一致）

- ❌ 截断重写策略（2 轮未收敛时触发整章重写）— 风险高，留待 V3.1
- ❌ 大规模重新生成（只分析基线 + 测试验证，未重跑 30 章）
- ❌ Writer Prompt 重写（058c 已做最小修改）
- ❌ RAG 修复
- ❌ Settlement 数据噪声修复

---

## 验证方式

```bash
# 运行全部测试
pytest tests/ --ignore=tests/integration -q
# 预期: 1107 passed, 0 failed

# 专项测试
pytest tests/test_revision_handler.py::TestDetectNewIssues -q
pytest tests/test_revision_handler.py::TestBuildRevisionOutputWithNewIssues -q
pytest tests/test_review_merger.py -q
pytest tests/test_058d_integration.py -q
```

---

## 已知限制

1. **3 章样本量不足**: 058c 效果的理论预期正面，但需 V3.1 的 10 章+验证才能得出统计结论
2. **RAG 未生效**: `vector_store.total_chunks=0`，已知问题
3. **上下文膨胀残余**: Ch30 仍 ~41K tokens，根本解决需 V3.1 分层摘要
4. **截断重写策略未实现**: 2 轮未收敛时触发重写，留待 V3.1

---

## 交接状态

- [x] 代码实现完成
- [x] 测试通过（pytest -v: 1107 passed, 0 failed）
- [x] 不违反 AGENTS.md 任何规则
- [x] 更新了 `docs/STATUS.md`
- [x] 生成了 `tasks/058d-revision-convergence-fix-DONE.md`
- [x] 验证报告写入 `docs/review/058d_validation_report.md`
