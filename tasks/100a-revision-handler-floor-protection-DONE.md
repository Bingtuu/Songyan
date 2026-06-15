# Task 100a: RevisionHandler 下限保护 + 字数守卫 — 交接报告

> **状态**: 已完成
> **完成时间**: 2026-06-12
> **验证范围**: 5 章端到端（Ch41-Ch45，项目 proj-e74ef1e4）

---

## 做了什么

### 1. 提升下限常量

| 文件 | 常量 | 旧值 | 新值 |
|------|------|------|------|
| `revision_handler/__init__.py` | `MIN_CONTENT_RATIO` | 0.50 | **0.85** |
| `revision_handler/_segmented_revision.py` | `MIN_PRESERVATION_RATIO` | 0.50 | **0.85** |

### 2. 全局字数下限守卫（`run_segmented_revision`）

拼接完整正文后，若 `content_preservation_ratio < MIN_PRESERVATION_RATIO (0.85)`，直接回退到原始内容，不进入后续 accept 路径。

### 3. `_enforce_revision_word_count` 硬约束增强

- 新增 `min_preserve_ratio: float = 0.85` 参数
- 若 revision 后字数低于 `original_wc * min_preserve_ratio`：
  - **不自动回退到原始 draft**
  - 标记 `reason = "revision_underflow_needs_human_review"`
  - 由上层 quality gate 决定是否继续 revision 或上报人工
- 若 revision 后字数低于下限但高于 0.85x：正常触发 `revision_underflow_fallback`

### 4. patch_engine 路径字数保护

在 `run_revision` 的 patch_engine 分支中，`_enforce_revision_word_count` 返回的 `needs_human_review` 通过 `logger.warning` 明确记录，便于后续质量门拦截。

### 5. 数据库迁移顺序修复

将 `_migrate_lifecycle_status` 提前到 `executescript(sql)` 之前执行，避免旧数据库缺少 `lifecycle_status` 列时 `CREATE INDEX` 失败。

---

## 验证结果

### 单元测试

```
pytest tests/test_revision_handler.py tests/test_088_revision_word_limit.py
       tests/test_079_segmented_revision.py tests/test_revision_handler_patch.py
       tests/test_revision_handler_fuzzy.py -v
# 119 passed, 0 failed
```

### 5 章端到端验证（proj-e74ef1e4，scifi / webnovel）

| 章节 | Accepted 版本 | 字数 | 目标 | 比例 | 最低 Revision 保留率 |
|------|--------------|------|------|------|---------------------|
| Ch41 | rev-41-5 | 3329 | 3500 | 0.951x | 0.995x |
| Ch42 | rev-42-5 | 4080 | 3500 | 1.166x | 0.961x |
| Ch43 | rev-43-5 | 3873 | 3500 | 1.106x | 0.984x |
| Ch44 | rev-44-2 | 4029 | 3500 | 1.151x | 0.988x |
| Ch45 | rev-45-6 | 4180 | 3500 | 1.194x | 0.984x |

**关键结论**：
- 5 章中 RevisionHandler 所有 revision 轮次的最低保留率为 **0.961**（Ch42 v2）
- **无任何 <0.85x 的 revision 结果**，彻底消除了 Ch45 类暴跌风险
- Ch42/Ch43 的 `v-` 版本（Writer rewrite）是 Accept 守卫触发的重写行为，非 RevisionHandler 导致

---

## 代码变更清单

1. `src/songyan/agents/revision_handler/__init__.py`
   - `MIN_CONTENT_RATIO = 0.85`
   - patch_engine 路径增加 `needs_human_review` 分支处理

2. `src/songyan/agents/revision_handler/_segmented_revision.py`
   - `MIN_PRESERVATION_RATIO = 0.85`
   - `run_segmented_revision` 增加全局下限守卫
   - `_enforce_revision_word_count` 增加 `min_preserve_ratio` 和 `needs_human_review`

3. `src/songyan/db/migrations.py`
   - `_migrate_lifecycle_status` 和 `_migrate_setting_category` 提前到 `executescript` 之前

4. `tests/test_088_revision_word_limit.py`
   - 更新断言匹配新行为

---

## 已知限制

- ruff 报告 3 个 pre-existing F401（`_difflib_fuzzy_search`, `_paragraph_fallback_search`, `_find_text_span` 未使用），不在本 Task 范围内
- `ProjectRunResult` 对象缺少 `completed` 属性（日志末尾报错），不影响生成功能

---

## 下一步

- Task 100b: 流程质量门 + 人工 edit 审计修复
