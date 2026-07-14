# V7 审计修复验证报告

> **审计计划**: 针对 `docs/reports/v7-audit/pass13-final-audit-report.md` 中列出的 P0/P1 问题进行修复后的验证。
> **报告日期**: 2026-07-13
> **基线**: pass13 最终汇总报告（P0×6, P1×24, P2×41）
> **目标**: 在 Ch250 长跑前清零 P0，并尽量完成高优先级 P1。

---

## 1. 执行摘要

本次修复围绕 pass13 审计报告中的 6 项 P0 及若干高优先级 P1 展开。修复后：

- **P0**: 6/6 已修复并验证通过（含 P0-5 默认测试门禁限时）。
- **P1-9 / P1-10 / P1-13 / P1-20 / P1-21 / P1-22 / P1-23** 已完成或已决策。
- **P1-13**（`character_update.old_value` 严格校验）经用户决策，保持"DB 回填 + warning"行为，与 Task 114a 回归测试一致，不改为严格报错。
- **非 performance 测试门禁**: `pytest -m "not performance" tests/` 通过，耗时 ≤ 180s。
- **类型检查**: `mypy src/` 通过。
- **Lint**: 未引入新告警；剩余 14 个 pre-existing 告警（E501/E402/W292/I001）。

---

## 2. P0 修复状态

| ID | 问题 | 修复文件 | 状态 | 验证命令 |
|---|---|---|---|---|
| P0-1 | WAL/SHM 文件删除 | `src/songyan/db/connection.py` | ✅ 已修复 | `pytest tests/db/test_connection.py -q` |
| P0-2 | `chapter_versions` 原地 UPDATE | `src/songyan/db/repository.py` | ✅ 已修复 | `pytest tests/integration/test_paths.py tests/integration/test_checkpoint.py tests/integration/test_ch41_50_validation.py -q` |
| P0-3 | RevisionHandler 整章重写 | `src/songyan/agents/revision_handler/__init__.py` | ✅ 已修复 | `pytest tests/test_revision_handler.py tests/test_task138n_mandatory_reference_revision.py -q` |
| P0-4 | mypy strict 失败 | 全 `src/` | ✅ 已修复 | `mypy src/` |
| P0-5 | 全量 pytest 超时 | `pyproject.toml` + 多个测试文件 | ✅ 已修复 | `pytest -m "not performance" tests/ -q` |
| P0-6 | `rewrite_node` 截断不一致 | `src/songyan/workflows/_nodes.py` | ✅ 已修复 | `pytest tests/test_rewrite_node.py tests/test_phase1_graph.py -q` |

### P0-5 具体措施

将以下慢测试/模块标记为 `@pytest.mark.performance`：

- `tests/integration/test_checkpoint.py`
- `tests/test_154_llm_rate_limit_and_budget.py`
- `tests/test_157_v6_acceptance.py`
- `tests/test_dialogue_style_card.py`
- `tests/test_load_layered_summaries.py`
- `tests/test_validation_gapfill.py`
- `tests/workflows/test_checkpointer.py`
- `tests/test_145_stage_a_metrics.py`
- `tests/test_151_mr_adaptive_cap_and_relevance.py`
- `tests/test_170_adaptive_gate_validation.py`
- `tests/test_171w_text_guardrail_observe.py`
- `tests/test_settlement_indexing.py`
- `tests/db/test_character_state_lifecycle.py`
- `tests/test_163_concept_budget.py`
- `tests/test_eval_runner.py::test_run_seed_project_all_configs`

非 performance 套件结果：

```
2414 passed, 2 skipped, 210 deselected in 175.59s
```

---

## 3. P1 修复状态

| ID | 问题 | 修复文件 | 状态 | 备注 |
|---|---|---|---|---|
| P1-1 | 关键路径裸 `except Exception` | `src/songyan/workflows/_nodes.py` | ✅ | 已收窄异常类型 |
| P1-9 | `foreshadowings.source_version_id` 允许 NULL | `src/songyan/db/schema.sql`, `src/songyan/db/settlement_repo.py` | ✅ | 列改为 `NOT NULL REFERENCES ... ON DELETE CASCADE`；Repository 强制非空 |
| P1-10 | `numerical_ledgers` 未持久化 formula | `src/songyan/db/schema.sql`, `src/songyan/db/settlement_repo.py`, `src/songyan/db/migrations.py` | ✅ | 新增 `formula` 列并持久化 |
| P1-13 | `character_update.old_value` 无校验 | `src/songyan/agents/settlement_extractor/_validate.py` | ✅ 已决策 | 保持"DB 回填 + warning"行为；与 Task 114a 回归测试一致，不改为严格报错 |
| P1-20 | 空 `source_quote` 绕过校验 | `src/songyan/agents/settlement_extractor/_quote_filter.py` | ✅ | 空 quote 返回 `False` |
| P1-21 | latest brief 选择逻辑脆弱 | `src/songyan/evals/literary_guardrails.py` | ✅ | 改用 `ROW_NUMBER()` |
| P1-22 | `_brief_builder.py` 裸 except | `src/songyan/agents/creative_director/_brief_builder.py` | ✅ | 收窄为 `pydantic.ValidationError` |
| P1-23 | `generate_dialogue_style_cards` 异常捕获错误 | `src/songyan/agents/creative_director/__init__.py` | ✅ | 捕获 `LLMError` / `LLMResponseParseError` |

---

## 4. 全量回归结果

```
2623 passed, 2 skipped, 1 xfailed, 2 warnings in 644.15s (0:10:44)
```

与 pass13 审计基线（`2623 passed, 2 skipped, 1 xfailed, 2 warnings`）完全一致。修复过程中发现并修正了 `tests/integration/test_checkpoint.py` 因 P0-2（accept 创建新版本）导致的版本数/ID 断言过时问题。

---

## 5. 剩余债务与建议

### 5.1 P1-13 已决策

当前实现（Task 114a）在 `_validate_settlement` 中检测到 `old_value` 与 DB 不一致时，自动用 DB 当前值回填并记录 info log。回归测试 `test_ch103_old_value_backfill_*` 明确依赖此行为。

pass13 审计要求：`old_value` 必须与 DB 当前值一致，否则报错或 `needs_human_review`。

**决策结果**：经用户确认，保持当前"DB 回填 + warning"行为，不引入严格报错 / `needs_human_review`。原因：与 Task 114a 回归测试语义一致，且当前 warning 机制已能暴露不一致事件。

### 5.2 其他建议

- **P1-5 / P1-6 / P1-7 / P1-8 / P1-11**: schema 编号、表缺失、外键、唯一约束等可在 Ch250 爬坡中分批治理。
- **P1-16 CRLF**: 仓库存在大量 LF/CRLF 混合；建议统一 `.gitattributes` 并一次性格式化，但本次未处理以避免 diff 爆炸。
- **P2**: 按 pass13 报告分批推进。

---

## 6. 验证命令速查

```powershell
# 非 performance 测试门禁（目标 ≤180s）
python -m pytest -m "not performance" tests/ -q

# 全量回归
python -m pytest tests/ -q

# 类型检查
mypy src/

# Lint
ruff check src/ tests/
```

---

> **松烟入墨，字句成锋。**
> 本报告将随全量回归结果更新。
