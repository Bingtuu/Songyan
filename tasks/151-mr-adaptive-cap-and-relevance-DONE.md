# Task 151: MR 上限自适应 + 相关性排序 — DONE

> **状态**: ✅ 完成  
> **合入时间**: 2026-07-02  
> **全量回归**: `2129 passed, 2 skipped, 1 xfailed, 2 warnings`  
> **Lint**: `ruff check src/ tests/` 通过

---

## 实现内容

### 151a — MR 上限自适应

- 修改 `src/songyan/workflows/_helpers.py` 的 `_load_critical_mandatory_references`：
  - 新增关键字参数 `active_critical_count` 与 `mainline_thread_keys`。
  - 当 `max_mandatory_references` 为 `None` 时，使用自适应公式：
    ```python
    cap = min(max(active_critical_count, scenes_count * 2, 6), 16)
    ```
  - 下限 6（保证少量关键设定必注入），上限 16（防 Writer 过载）。
  - 显式传入 `max_mandatory_references` 时仍按旧行为覆盖自适应值，保持向后兼容。

### 151b — 相关性排序

- 当提供 `mainline_thread_keys` 时，critical 设定若 `setting_key` 或 `setting_name` 与任一主线 key 子串匹配（双向、不区分大小写），则视为"主线相关"。
- 排序键改为 `(is_mainline_related, silent_chapters, -introduced_in_chapter)` 降序：
  - 主线相关项优先；
  - 同组内沉默章数多者优先；
  - 同沉默下越早引入者优先。
- 无骨架 / 无线索时 `mainline_thread_keys` 为 `None` 或空集，排序退化为旧的 `(silent_chapters, -introduced_in_chapter)`。

### 调用链路

- `assemble_context_package` 在调用 MR 加载前，先通过 `_compute_mandatory_reference_inputs` 计算 `active_critical_count` 与 `mainline_thread_keys`，再传入 `_load_critical_mandatory_references`。
- `rewrite_node` 同样复用 `_compute_mandatory_reference_inputs`，确保 rewrite 路径的 MR 也走自适应 + 相关性逻辑。
- 截断日志 `task138n.mandatory_references_truncated` 保留并增强，新增字段：`adaptive_cap`、`active_critical_count`、`mainline_related_count`。

---

## 文件变更

| 文件 | 变更 |
|------|------|
| `src/songyan/workflows/_helpers.py` | 新增 `_extract_mainline_thread_keys`、`_compute_mandatory_reference_inputs`；重写 `_load_critical_mandatory_references` 实现自适应上限与相关性排序；更新 `assemble_context_package` 调用点。 |
| `src/songyan/workflows/_nodes.py` | `rewrite_node` 调用 `_compute_mandatory_reference_inputs` 并将结果传入 `_load_critical_mandatory_references`。 |
| `tests/test_151_mr_adaptive_cap_and_relevance.py` | 新增 11 个单测，覆盖自适应上限、相关性排序、无骨架回退、集成装配、MAX_ORPHANED 未改动。 |
| `tasks/V6-README.md` | Task 151 状态更新为 ✅ 完成，指向本 DONE 文档。 |
| `docs/STATUS.md` | 当前阶段状态更新为 Task 151 完成。 |

---

## 测试结果

```text
python -m pytest tests/test_151_mr_adaptive_cap_and_relevance.py -v
11 passed

python -m pytest tests/test_149_input_side_demotion.py tests/test_150_infer_category_tightening.py -v
19 passed

python -m pytest tests/ -q
2129 passed, 2 skipped, 1 xfailed, 2 warnings

ruff check src/ tests/
All checks passed!
```

---

## 关键决策

1. **上限 16 的安全依赖**：Task 149 已将超额 critical 降级为 candidate，压低 `active_critical_count` 基数；本 Task 的相关性排序进一步确保主线相关项优先注入。两者共同保证 cap 升到 16 不会复现 138m 的 43 条 MR 过载。若在没有 Task 149 的代码基上合入，应临时将上限保守回退到 ≤12。
2. **`MAX_ORPHANED` 未改动**：`continuity_auditor/_constraints.py` 的 `MAX_ORPHANED=12`（约束生成侧）保持原样，未扩散修改范围。
3. **无骨架回退**：`_compute_mandatory_reference_inputs` 在查询叙事骨架表失败时返回空主线 key 集合，函数退化为旧排序；对未初始化 schema 的测试环境也兼容。
4. **不新增 LLM / Agent**：仅使用已有的 `SettingTrackingRepository` 与 `load_narrative_goal_context`，无新增 LLM 调用。

---

## 公式与排序规则

- **自适应上限**：`cap = min(max(active_critical_count, scenes_count * 2, 6), 16)`
- **相关性匹配**：`setting_key` 或 `setting_name`（lower）与任一 `mainline_thread_key`（lower）互相子串匹配。
- **排序**：`(is_mainline_related, silent_chapters, -introduced_in_chapter)` 降序。

---

## 后续工作

- Task 152：critical 显式 resolve/作废出口。
- 阶段 B 完成后，在 Ch~100 位置复测 `rule_auditor.mandatory_reference_missing` 命中率，确保较 138n 不升高。
- 观测 `mandatory_references_truncated` 频率变化，入 `docs/reports/`。
