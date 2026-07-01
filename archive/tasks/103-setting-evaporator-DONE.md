# Task 103: SettingEvaporator — DONE

> **Phase**: V5.0 Context Diet 2.0 — 核心组件 3/4
> **完成日期**: 2026-06-13
> **状态**: 已完成

---

## 做了什么

实现了 SettingEvaporator（设定蒸发器），Context Diet 2.0 的第三个核心组件。

1. **`resolve_confidence` 计算函数**: 基于时间衰减、叙事相关性和硬约束标记，纯规则计算每条 active setting 的 resolve_confidence（<10ms/条）。
2. **SettingEvaporator 类**: 轻量规则节点，SettlementExtractor 后自动 archive 低 confidence 设定（阈值 0.3）。
3. **设定合并逻辑**: 每 50 章执行一次 O(n²) 两两关键词重叠度扫描，合并相似度 ≥0.9 的重复设定，保留最早创建的 setting_key。
4. **Workflow 集成**: 在 `settlement_extractor_node` 中，SettlementExtractor 之后、SummaryWriter 之前插入 SettingEvaporator 调用。
5. **Repository 层增强**: `settlement_repo.py` 新增 `list_active_with_tracking()`（JOIN setting_tracking）和 `archive_by_confidence()`（批量 archive）。

---

## 改了哪些文件

| 文件 | 变更 |
|------|------|
| `src/songyan/agents/setting_evaporator/__init__.py` | **新建** — `_calculate_resolve_confidence` + `SettingEvaporator` 类 |
| `src/songyan/db/settlement_repo.py` | **新增** — `list_active_with_tracking()`、`archive_by_confidence()` |
| `src/songyan/workflows/_nodes.py` | **修改** — settlement_extractor_node 集成 SettingEvaporator 调用 |
| `tests/test_setting_evaporator.py` | **新建** — 11 个单元测试覆盖 confidence 计算、蒸发、合并 |
| `tasks/103-setting-evaporator-DONE.md` | **新建** — 本文档 |

---

## 测试数据

- **单元测试**: `pytest tests/test_setting_evaporator.py -v` → **11 passed, 0 failed**
- **全量回归**: `pytest tests/ -q` → **1422 passed, 21 failed**（全部 pre-existing，无新增失败）
- **ruff 检查**: `ruff check src/songyan/agents/setting_evaporator/__init__.py` → **All checks passed**（Task 103 引入的 2 个新错误已修复）

---

## 验证结果

| 指标 | 结果 |
|------|------|
| `resolve_confidence` 计算耗时 | <10ms/条（纯规则，无 LLM 调用） |
| 蒸发阈值 | 0.3（可配置） |
| 合并扫描间隔 | 每 50 章 |
| 合并相似度阈值 | 0.9 |
| hard_constraint 设定 | 永不蒸发（critical 类别或出现在 target_events 中） |

---

## 已知限制

1. **相似度代理精度**: 使用 `_compute_keyword_overlap` 作为 embedding 相似度的轻量代理，对于语义相似但关键词不重叠的设定可能漏合并。
2. **合并性能**: O(n²) 扫描在设定数量 >200 时可能变慢，当前设计针对 <200 条 active settings。
3. **误蒸发风险**: 纯规则判断可能误 archive 非 critical 但对后续叙事重要的设定，需通过人工抽检验证误判率 <5%。
4. **ruff pre-existing 错误**: 项目存在 336 个 pre-existing lint 错误（主要为 import 排序和行过长），Task 103 未引入新增错误。
