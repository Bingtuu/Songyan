# Task 012: RuleAuditor Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了 RuleAuditor Agent —— 纯代码规则检测，复用 Task 017 的 Quality Utils，对 Writer 生成的章节进行 AI 腔、疲劳词、钩子、段落节奏、字数等维度的自动检测。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/rule_auditor.py` | RuleAuditor：`run_rule_audit()` 纯代码检测 + `save_rule_audit()` 保存 + 综合评分 + 摘要生成 |
| `tests/test_rule_auditor.py` | RuleAuditor 测试（29 个测试） |
| `tasks/012-rule-auditor.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_rule_auditor`, `save_rule_auditor` |

---

## 如何运行

```bash
# 运行 RuleAuditor 测试
pytest tests/test_rule_auditor.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：436 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不调用 LLM（LLMAuditor 负责，Task 013）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做合并报告逻辑（RevisionHandler 或编排层负责）

---

## 接口使用示例

```python
from songyan.agents.rule_auditor import run_rule_audit, save_rule_audit
from songyan.db.review_repo import ReviewReportRepository
from songyan.models import GenreRules

# 运行规则检测
result = await run_rule_audit(
    content=chapter_version.content,
    genre_rules=GenreRules(fatigue_words=["冷笑", "嘴角勾起"]),
    word_count_target=3000,
)

print(result.ai_tell_count)        # AI 腔数量
print(result.fatigue_word_count)   # 疲劳词数量
print(result.has_opening_hook)     # 是否有首屏钩子
print(result.has_ending_hook)      # 是否有章末钩子
print(result.paragraph_rhythm_score)  # 段落节奏评分
print(result.word_count_ok)        # 字数是否达标

# 保存到数据库
await save_rule_audit(
    db=ReviewReportRepository(),
    version_id=chapter_version.version_id,
    result=result,
)
```

---

## 设计要点

- **纯代码检测**：不调用 LLM，全部复用 Task 017 Quality Utils
- **检测维度**：AI 腔 / 疲劳词 / 首屏钩子 / 章末钩子 / 段落节奏 / 字数统计
- **综合评分**：0-10 分，AI 腔(-0.5/个) + 疲劳词(-0.3/个) + 无首屏钩子(-1) + 无章末钩子(-1.5) + 节奏差(-0.3/分) + 字数偏差(-5*偏差率)
- **摘要生成**：自动汇总所有问题点，无问题时显示"通过"
- **保存集成**：自动组装 MergedReviewReport 并写入 review_reports 表
