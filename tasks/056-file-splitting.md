# Task 056: 大文件拆分

> **Phase**: V3.0 Layer 1 — 消解代码结构债
> **优先级**: P1
> **依赖**: Layer 0 全部完成（052 ~ 055）
> **预计工作量**: 中（2~3 天）

---

## Goal

将 5 个超过 400 行的 Agent 文件拆分为多个 <=400 行的模块，降低认知负荷，不改任何函数行为。

## Context

当前代码库中多个 Agent 文件远超 AGENTS.md 规则 64 的 400 行上限：

| 文件 | 当前行数 | 拆分目标 |
|------|---------|---------|
| `settlement_extractor.py` | ~859 | 拆出 `_validate.py` + `_apply.py`，主模块保留 `extract()` |
| `context_manager.py` | ~663 | 拆出 `_assemblers.py`，主模块保留 `assemble()` + `BudgetPruner` |
| `revision_handler.py` | ~655 | 拆出 `_patch_engine.py` + `_diff.py`，主模块保留 `revise()` |
| `continuity_auditor.py` | ~388 | 拆出 `_scanners.py` + `_constraints.py`，主模块保留 `audit()` |
| `creative_director.py` | ~446 | 拆出 `_brief_builder.py`，主模块保留 `generate_creative_brief()` |

## In Scope（必须完成）

- [ ] **`settlement_extractor.py` 拆分**:
  - `src/songyan/agents/settlement_extractor/_validate.py` — `_validate_settlement()` 及所有 `_validate_*` 子函数
  - `src/songyan/agents/settlement_extractor/_apply.py` — `_apply_to_db()` 及所有 Repository 调用
  - 主模块保留 `extract_settlement()` 编排 + `_build_state_settlement()` + `_calculate_impact_score()` + `_extract_open_threads()`
- [ ] **`context_manager.py` 拆分**:
  - `src/songyan/agents/context_manager/_assemblers.py` — `_build_character_snapshots()` / `_build_recent_plot()` / `_build_genre_rules()` 等
  - 主模块保留 `assemble()` + `BudgetPruner` + `_estimate_package()`
- [ ] **`revision_handler.py` 拆分**:
  - `src/songyan/agents/revision_handler/_patch_engine.py` — `_apply_patches()` + `_find_text_span()`
  - `src/songyan/agents/revision_handler/_diff.py` — `_difflib_fuzzy_search()` + `_paragraph_fallback_search()`
  - 主模块保留 `run_revision()` + `_determine_issues_fixed()` + `save_revision_output()`
- [ ] **`continuity_auditor.py` 拆分**:
  - `src/songyan/agents/continuity_auditor/_scanners.py` — 各维度扫描函数
  - `src/songyan/agents/continuity_auditor/_constraints.py` — `_generate_constraints()` + `write_constraints()`
  - 主模块保留 `audit()` 编排
- [ ] **`creative_director.py` 拆分**:
  - `src/songyan/agents/creative_director/_brief_builder.py` — CreativeBrief 构造逻辑
  - 主模块保留 `generate_creative_brief()` 编排

## Out of Scope（明确不做）

- 不改任何函数签名或行为
- 不引入新的抽象层或 base class
- 不合并/重构跨模块的重复代码
- 不修改 `pyproject.toml` 或任何 `__init__.py` 的导出路径

## 接口契约

所有拆分后的模块通过同级目录 `__init__.py` 或相对导入暴露。对外公共 API 不变。

```python
# settlement_extractor/__init__.py
from ._apply import _apply_to_db
from ._validate import _validate_settlement
from .settlement_extractor import extract_settlement

__all__ = ["extract_settlement"]
```

## 测试要求

### Layer 3: 集成测试
- [ ] 拆分后 `pytest tests/ -x -q` 全部通过（测试数不减少）
- [ ] 没有因拆分引入的新 import 错误

## 验收标准

- [ ] 全部 5 个文件拆分完成，主模块 <= 500 行（考虑到拆分成本，放宽到 500）
- [ ] `pytest tests/ -x -q` 全部通过
- [ ] `pyproject.toml` 或任何 `__init__.py` 的导出路径不变
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/056-file-splitting-DONE.md`

## 参考文档

- `prd/v3.0-stability-closed-loop.md` — 5.1 文件拆分
- `AGENTS.md` — 规则 64
