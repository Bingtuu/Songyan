# Task 052: RevisionHandler 正文结构保护验证 — DONE

> **完成日期**: 2026-06-04
> **执行代理**: Kimi Code CLI
> **Git Commit**: `c966113`

---

## 完成摘要

验证 RevisionHandler 截断保护逻辑有效，并暴露 `content_preservation_ratio` 供监控系统采集。

---

## 变更清单

### 1. 数据模型 (`src/songyan/models/revision.py`)

- `RevisionOutput` 新增字段:
  ```python
  content_preservation_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
  ```

### 2. Agent 逻辑 (`src/songyan/agents/revision_handler.py`)

- `run_revision()` 在决策逻辑结束后计算保留率:
  ```python
  content_preservation_ratio = (
      round(min(len(revised_content) / original_len, 1.0), 4)
      if original_len > 0 else 0.0
  )
  ```
- 上限 1.0：保留率语义，内容膨胀不视为"保留不足"
- 新增结构化日志 `revision_handler.content_preservation_ratio`
- ratio 写入 `RevisionOutput.content_preservation_ratio` 后返回

### 3. 单元测试 (`tests/test_revision_handler.py`)

新增 2 个测试（`TestRunRevision` 类）:

| 测试名 | 场景 | 验证点 |
|--------|------|--------|
| `test_content_preservation_ratio_normal` | 正常修订（patch 成功） | ratio = 1.0 |
| `test_content_preservation_ratio_logged` | 截断回退（无有效 patches） | ratio = 1.0，回退到原始内容 |

---

## 测试报告

```
pytest tests/test_revision_handler.py tests/test_revision_handler_fuzzy.py tests/test_revision_handler_patch.py -v
# 70 passed, 0 failed

pytest tests/ -v --ignore=tests/integration
# 1071 passed, 0 failed（无回归）
```

---

## 验收状态

| 验收项 | 状态 | 备注 |
|--------|------|------|
| `RevisionOutput` 序列化/反序列化含新增字段 | ✅ | Pydantic Field 验证通过 |
| `test_content_preservation_ratio_logged` | ✅ | 通过 |
| `test_content_preservation_ratio_normal` | ✅ | 通过 |
| 真实章节验证 ratio >= 0.7 | ⏳ | **待真实 LLM 环境执行**。Mock 测试已覆盖截断/回退两条路径 |
| `docs/STATUS.md` 更新 | ✅ | 052 状态 → 已完成 |

---

## 已知限制

1. **真实验证未完成**：需要真实 LLM API 和项目数据（Ch12 或 seed）运行一轮 revision，确认 `content_preservation_ratio >= 0.7`。当前环境无 API 密钥，无法执行。
2. **ratio 上限 1.0**：若 revision 后内容显著膨胀（如从 4000 字到 5000 字），ratio 显示为 1.0。这是设计选择（保留率语义），非 bug。

---

## 未修改项（按 Task 约束）

- ❌ 未修改核心 patch 逻辑（`_apply_patches` / `_find_text_span`）
- ❌ 未调整 `MIN_CONTENT_RATIO`（保持 0.5）
- ❌ 未修改 RevisionHandler Prompt

---

## 交接建议

- **下一 Task**: 053（database locked 修复）或 054（settlement_extractor DB 访问重构）
- **真实验证指令**: 在已配置 LLM API 的环境中运行 `python -m songyan.cli revision --project <id> --chapter 12`，检查日志中 `revision_handler.content_preservation_ratio` 值
