# Task 002: Pydantic 数据模型 — 交接报告

## 完成状态

- [x] 代码实现
- [x] 测试通过
- [x] 文档更新

---

## 改了哪些文件

### 新增模型文件（10 个）

| 文件 | 模型数 | 说明 |
|------|--------|------|
| `src/songyan/models/__init__.py` | — | 公共导出 |
| `src/songyan/models/project.py` | 1 | ProjectSetting |
| `src/songyan/models/character.py` | 2 | Character, CharacterState |
| `src/songyan/models/chapter.py` | 3 | ChapterGoal, ChapterVersion, ChapterHead |
| `src/songyan/models/genre.py` | 1 | GenreProfile（含 from_dict） |
| `src/songyan/models/creative_mode.py` | 3 | CreativeModeProfile, CreativeBrief, Tension |
| `src/songyan/models/context.py` | 9 | ContextPackage + 8 个子类 |
| `src/songyan/models/review.py` | 7 | ReviewCategory(StrEnum) + ReviewIssue + RuleAuditResult + LLMAuditResult + MergedReviewReport |
| `src/songyan/models/literary.py` | 2 | LiteraryObservation, LiteraryAuditResult |
| `src/songyan/models/revision.py` | 3 | RevisionInput, Patch, RevisionOutput |
| `src/songyan/models/settlement.py` | 6 | StateSettlement + 5 个子类 |

**总计：35 个 Pydantic v2 模型类，758 行代码。**

### 新增测试文件（3 个）

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `tests/models/test_batch1_foundation.py` | 20 | project, character, chapter, genre |
| `tests/models/test_batch2_context_review.py` | 34 | creative_mode, context, review, literary |
| `tests/models/test_batch3_settlement_revision.py` | 14 | revision, settlement |

---

## 如何验证

```bash
# 1. 导入验证
python -c "from songyan.models import ProjectSetting, ChapterGoal, ContextPackage, MergedReviewReport, StateSettlement"

# 2. 运行测试
pytest tests/models/ -v
# Expected: 68 passed in ~0.2s

# 3. 代码风格
ruff check src/songyan/models/
# Expected: 0 errors
```

---

## 关键设计决策

1. **循环依赖处理**：`ContextPackage` → `CreativeBrief` → `ChapterGoal`。通过直接模块导入（而非 `from __future__ import annotations` + 字符串引用）解决，因为依赖链是单向的，无实际循环。

2. **StateSettlement 验证**：模型层**仅做结构验证**（类型、必填字段、枚举值）。业务验证（`old_value` 匹配 DB、`source_quote` 存在正文、`closing_value` 公式计算）留给 Repository/Service 层（Task 004+）。

3. **ReviewCategory**：使用 `enum.StrEnum`（Python 3.11+），而非 `str, Enum`，满足 ruff UP042 规则。

4. **文件拆分**：测试按 3 个批次拆分到 `tests/models/`，避免单文件 >400 行。

---

## 已知问题 / 限制

- `ContextPackage.assembled_at` 使用 `datetime.now()`，在测试中可能导致微秒级差异。后续如有需要可 mock。
- `GenreProfile.from_dict()` 和 `CreativeModeProfile.from_dict()` 仅为简单 `**data` 展开，未做深度校验（JSON Schema 校验留给 Task 005/006）。

---

## 下一步依赖

- **Task 003（SQLite Schema）**：需要 `models/` 中所有模型定义的字段来设计表结构
- **Task 004（Repository 层）**：直接依赖所有模型进行 CRUD
- **Task 005（Genre Profile）**：需要 `GenreProfile` 模型来加载 JSON 配置
- **Task 006（CreativeMode Profile）**：需要 `CreativeModeProfile` 模型来加载 JSON 配置
- **Task 008+（Agents）**：所有 Agent 的输入输出都依赖本 Task 的模型
