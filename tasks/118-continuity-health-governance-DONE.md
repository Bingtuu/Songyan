# Task 118-DONE: ContinuityAuditor Health 低分治理策略

> **Phase**: V5.0 Phase 4 — 质量信号治理
> **优先级**: P2
> **依赖**: Task 117 完成
> **完成日期**: 2026-06-20
> **测试**: 23 passed（test_continuity_health_governance.py）
> **lint**: ruff check src/ tests/ 通过
> **全量回归**: 1699 passed（pytest tests/ -q）

---

## 做了什么

### 1. P1/P2/P3 分级策略实现

在 `src/songyan/agents/continuity_auditor/continuity_health.py` 中实现了三档分级分类函数：

**`classify_continuity_mark`** — 将单个 continuity mark 分类为 P1/P2/P3：

| 条件 | 等级 | 说明 |
|------|------|------|
| `mark_type == "character"` 或 note 含 `mismatch`/`矛盾` | P1 | 角色状态矛盾 |
| `mark_type == "item"` | P3 | 遗忘物品（低敏感度） |
| note 含 `recurring`/`overdue`/`逾期` | P2 | 重复出现或逾期伏笔 |
| note 含 `background`/`technical`/`historical` | P3 | 低敏感度背景项 |
| `mark_type == "setting"` + `priority >= 10` 且无低敏感度关键词 | P1 | critical orphaned |
| `priority >= 10` 其他 | P3 | 高 priority 但非 critical |
| `priority == 9` | P1 | state mismatch 生成 |
| `priority == 7-8` | P2 | 中等 priority |
| 其他 | P3 | 轻微疑点 |

**`classify_health_score`** — 基于 health_score 和构成项分类整体严重等级：
- 有 `state_mismatch` → P1
- 有 `critical` orphaned settings → P1
- health_score < 3.0 → P1
- health_score 3.0-5.0 → P2
- health_score 5.0-7.0 → P3
- health_score >= 7.0 → P3

**`classify_report`** — 对 ContinuityReport 中各类问题按 P1/P2/P3 分组计数。

### 2. HumanMark 新增字段

**`src/songyan/models/human_mark.py`** — 为 `HumanMark` 新增：
- `version_id: str | None` — 关联产生此标记的版本 ID
- `severity: Literal["P1", "P2", "P3"] | None` — 连续性问题严重等级

### 3. DB Schema 迁移

**`src/songyan/db/migrations.py`** — 新增 `_migrate_human_marks_extra_fields` 迁移函数：
- 添加 `version_id TEXT` 列
- 添加 `severity TEXT` 列

### 4. Repository 层支持

**`src/songyan/db/human_mark_repo.py`** — `_row_to_mark` 新增 `version_id`/`severity` 字段读取；`create` SQL INSERT 新增两列。

### 5. ContinuityAuditor 集成

**`src/songyan/agents/continuity_auditor/_constraints.py`** — `_generate_constraints` 新增 `version_id` 参数：
- `critical` category → severity=P1
- `recurring` category → severity=P2
- `background`/`technical`/`historical` → severity=P3
- `state_mismatch` → severity=P1
- `overdue` foreshadowing → severity=P2

**`src/songyan/workflows/phase2_graph.py`** — ContinuityAuditor 调用处更新为 `await auditor.write_constraints(report, version_id=final_version_id)`。

### 6. 指标收集函数

**`collect_continuity_health_metrics`** — 异步收集指定章节范围内的 continuity health 指标：
- health_low_chapters
- total_reports
- affected_chapters
- human_marks_summary（total/P1/P2/P3/unresolved）
- chapter_details

### 7. 测试覆盖

**`tests/test_continuity_health_governance.py`** — 23 个测试：

Layer 1（分类测试）:
- `test_orphaned_critical_is_p1` — critical orphaned setting → P1
- `test_orphaned_background_is_p3` — background orphaned setting → P3
- `test_state_mismatch_is_p1` — character state mismatch → P1
- `test_overdue_foreshadowing_is_p2` — overdue foreshadowing → P2
- `test_forgotten_item_is_p3` — forgotten item → P3
- `test_human_mark_instance` — HumanMark 实例传入也能正确分类
- `test_score_below_3_is_p1` — health_score < 3.0 → P1
- `test_score_3_to_5_is_p2` — health_score 3.0-5.0 → P2
- `test_score_5_to_7_is_p3` — health_score 5.0-7.0 → P3
- `test_score_with_state_mismatch_is_p1` — 有 state_mismatch 时 P1
- `test_score_with_critical_orphaned_is_p1` — 有 critical orphaned 时 P1
- `test_empty_report` — 空报告 P1/P2/P3 全 0
- `test_critical_orphaned_is_p1` — critical orphaned 计入 P1
- `test_recurring_orphaned_is_p2` — recurring orphaned 计入 P2
- `test_background_orphaned_is_p3` — background orphaned 计入 P3
- `test_state_mismatch_is_p1` — state_mismatch 计入 P1
- `test_overdue_foreshadowing_is_p2` — overdue foreshadowing 计入 P2

Layer 2（数据追踪测试）:
- `test_severity_field_in_human_mark` — HumanMark 支持 severity 字段
- `test_version_id_field_in_human_mark` — HumanMark 支持 version_id 字段
- `test_generate_constraints_sets_severity` — _generate_constraints 设置正确 severity
- `test_generate_constraints_sets_version_id` — _generate_constraints 正确传递 version_id
- `test_generate_constraints_version_id_defaults_to_none` — version_id 默认 None

Layer 3（章节信息追踪）:
- `test_human_mark_note_contains_chapter_info` — note 包含章节信息，created_at_chapter 正确

---

## 改了哪些文件

| 文件 | 变更 |
|------|------|
| `src/songyan/models/human_mark.py` | 新增 `version_id`/`severity` 字段 |
| `src/songyan/agents/continuity_auditor/continuity_health.py` | 新建模块：5 个分类/收集函数 |
| `src/songyan/db/human_mark_repo.py` | 新增两列的读写支持 |
| `src/songyan/db/migrations.py` | 新增 migration 函数 |
| `src/songyan/agents/continuity_auditor/_constraints.py` | 新增 `version_id` 参数和 severity 设置 |
| `src/songyan/agents/continuity_auditor/__init__.py` | `write_constraints` 透传 `version_id` |
| `src/songyan/workflows/phase2_graph.py` | ContinuityAuditor 调用处传入 `version_id` |
| `tests/test_continuity_health_governance.py` | 新建：23 个测试 |

---

## 验证结果

### 单元测试（Task 118 聚焦）
```
23 passed in 0.11s
```

### 全量回归
```
1699 passed, 4 skipped, 1 xfailed, 4 xpassed
```

### lint
```
All checks passed!
```

---

## 已知限制

1. **不新增硬门禁**：V5.0 收口阶段 health_low 仍为软复核，不阻断 accept。
2. **分级策略基于规则**：使用 note 关键词和 mark_type/priority 判断，未引入 LLM 语义判断。
3. **`collect_continuity_health_metrics` 未接入 streaming report**：函数已实现，但未在 DG 报告中调用。
4. **Ch111-Ch150 基线统计**：未执行（`_check118.ps1` 临时脚本已创建但未运行）。

---

## 下一步

- Task 119：长跑报告入口与 Windows Wrapper 加固
- Task 120：V5.0 Final Acceptance Package
