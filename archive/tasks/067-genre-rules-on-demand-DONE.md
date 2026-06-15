# Task 067: genre_rules 按需加载 — DONE

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-05
> **实际工作量**: ~2 小时

---

## 实现摘要

将 `GenreProfile` 的全量注入改为按需加载，按当前章节类型 (`chapter_type`) 过滤 `reviewer_focus` 和 `satisfaction_types`，预计节约 ~500 tokens/章。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/songyan/agents/context_manager/_assemblers.py` | `_build_genre_rules()` 新增 `chapter_goal` 参数；新增 `_filter_genre_profile()` 函数 |
| `src/songyan/workflows/_nodes.py` | 3 处调用更新签名，传入 `goal`；`settlement_extractor_node` 新增 `goal` 加载逻辑 |
| `tests/test_context_manager.py` | 更新现有测试调用签名 |
| `tests/test_genre_filter.py` | 新增 10 个单元测试（过滤逻辑 + 回退保护） |

### 过滤规则

按 `chapter_type` 硬编码映射过滤 `reviewer_focus` 和 `satisfaction_types`：

| chapter_type | reviewer_focus 保留 | satisfaction_types 保留 |
|-------------|---------------------|------------------------|
| `combat` | 科技设定是否前后一致, 战斗逻辑是否合理 | 科技突破, 危机化解, 生存逆袭 |
| `cultivation_breakthrough` | 科技设定是否前后一致, 突破过程是否有层次 | 境界突破, 战力跃升, 资源获取 |
| `daily` | 人物动机是否可信, 世界观设定是否自洽 | 情感满足, 信息揭示, 人物成长 |
| 默认/未知 | 保留全部（不降级）| 保留全部 |

最小保留数保护：`MIN_RETAIN = 2`，过滤后不足 2 条则回退到全部。

---

## 测试覆盖

| 测试文件 | 数量 | 说明 |
|----------|------|------|
| `tests/test_genre_filter.py` | 10 passed | 新增：combat/daily/未知类型过滤 + 回退保护 + 不修改原对象 |
| `tests/test_context_manager.py` | 126 passed | 更新调用签名 |
| `tests/` 全量 | **1148 passed** | 零失败 |

---

## 与 Task 067 原始验收标准的差异

| 原始标准 | 实际完成 | 说明 |
|----------|----------|------|
| 按 `chapter_type` 过滤 `reviewer_focus` | ✅ | 硬编码映射实现 |
| 同时过滤 `satisfaction_types` | ✅ | 扩展了原始范围，同样节省 token |
| 3 种 `chapter_type` 测试覆盖 | ✅ | combat / daily / cultivation_breakthrough + 回退 |
| 不修改配置文件格式 | ✅ | 零变更 |
| `pytest tests/ -x -q` 全部通过 | ✅ | 1148 passed |
| 更新 STATUS.md | ✅ | 测试数 1138→1148，067 标记完成 |
| 生成 DONE 文件 | ✅ | 本文件 |

---

## 参考

- `src/songyan/agents/context_manager/_assemblers.py` — `_build_genre_rules()` + `_filter_genre_profile()`
- `tests/test_genre_filter.py` — 过滤逻辑单元测试
