# Task 020-A 交接报告：Mock 端到端集成测试 + Checkpoint 恢复

> **Phase**: Phase 4 — 评测与优化
> **状态**: ✅ 完成
> **日期**: 2026-05-25
> **测试增量**: +9（626 total）

---

## 做了什么

实现了完整的 Mock 端到端集成测试套件，验证 LangGraph 工作流各节点通过 ID 从 DB 加载数据的链路正确，覆盖全部 6 条用户决策路径和 checkpoint 中断恢复机制。

### 新增文件

- `tests/integration/__init__.py`
- `tests/integration/conftest.py` — 测试基础设施（隔离 DB fixture、MockLLM fixture、响应构建器）
- `tests/integration/test_paths.py` — 6 条路径测试（A~F）
- `tests/integration/test_checkpoint.py` — Checkpoint 恢复 + 状态一致性测试

### 修复的代码 Bug（集成测试过程中发现）

| 文件 | 问题 | 修复 |
|------|------|------|
| `src/songyan/workflows/_nodes.py` | `genre.genre_rules` 属性不存在（`GenreProfile` 无此字段） | 导入 `_build_genre_rules` 并在 `rule_auditor_node` / `settlement_extractor_node` 中使用 |
| `src/songyan/workflows/_nodes.py` | `human_confirm_node` edit 时未计算 `version_number` | 查询现有版本数量并设置正确的 `version_number` |
| `src/songyan/agents/summary_writer.py` | `call_llm` 传入未定义的参数 `max_tokens` / `expect_json` | 移除非法参数 |
| `src/songyan/agents/summary_writer.py` | `parse_llm_response` 返回 `dict`，但代码当作有 `.data` 属性的对象使用 | 直接使用返回的 `dict` |
| `src/songyan/db/review_repo.py` | `get_by_version` 排序不稳定，`created_at` 相同时可能返回 rule/llm report 而非 merged report | 添加 `audit_type='merged'` 过滤 |
| `src/songyan/db/review_repo.py` | `create` 硬编码 `audit_type="merged"` | 添加 `audit_type` 参数，默认 `"merged"` |
| `src/songyan/agents/rule_auditor.py` | `save_rule_audit` 未区分 `audit_type` | 传入 `audit_type="rule"` |
| `src/songyan/agents/llm_auditor.py` | `save_llm_audit` 未区分 `audit_type` | 传入 `audit_type="llm"` |
| `src/songyan/workflows/phase1_graph.py` | `build_phase1_graph()` 每次创建新的 `MemorySaver`，导致 `run_chapter_pipeline` 和 `resume_human_confirm` 无法共享 checkpoint | 使用模块级单例 `_checkpointer` + `reset_checkpointer()` |

---

## 验证命令

```bash
# 集成测试
pytest tests/integration/ -v
# Expected: 9 passed

# 全量回归
pytest -q
# Expected: 626 passed
```

---

## 已知限制

- 所有 LLM 调用均为 mock，未验证真实 LLM 响应解析
- 性能测试在 020-C 中实现
- 种子项目基础设施在 020-B 中实现

---

## 下游依赖

- **020-B**: 评测集基础设施（runner + 种子项目配置）
- **020-C**: 验收指标收集 + 性能测试 + 文档收尾
