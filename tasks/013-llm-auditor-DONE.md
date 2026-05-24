# Task 013: LLMAuditor Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了 LLMAuditor Agent —— 调用 LLM 对章节进行语义层面的深度审查，覆盖 12 个维度（一致性、叙事质量、对话质量、描写质量、题材专项），输出结构化的 LLMAuditResult。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/llm_auditor.py` | LLMAuditor：`run_llm_audit()` Prompt 渲染 → LLM 调用 → JSON 解析 → LLMAuditResult + `save_llm_audit()` 保存 |
| `src/songyan/llm/parsing.py` | 公共 LLM JSON 解析工具：`extract_json()` + `parse_llm_response()` |
| `prompts/llm_auditor.md` | LLMAuditor Prompt 模板（12 维度审查说明 + JSON 输出格式） |
| `tests/test_llm_auditor.py` | LLMAuditor 测试（33 个测试） |
| `tasks/013-llm-auditor.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_llm_audit`, `save_llm_auditor` |

---

## 如何运行

```bash
# 运行 LLMAuditor 测试
pytest tests/test_llm_auditor.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：469 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不做规则检测（RuleAuditor 负责，Task 012）
- 不做文学性诊断（LiteraryAuditor 负责，Task 014）
- 不做合并报告逻辑（RevisionHandler 或编排层负责）

---

## 接口使用示例

```python
from songyan.agents.llm_auditor import run_llm_audit, save_llm_audit
from songyan.db.review_repo import ReviewReportRepository
from songyan.models import ContextPackage

# 运行 LLM 语义审查
result = await run_llm_audit(
    content=chapter_version.content,
    context_package=context_package,
    temperature=0.3,
)

print(len(result.issues))              # 发现问题数
print(result.dimension_scores)          # 各维度评分
print(result.cliche_risk_score)         # 套路化风险 0-10
print(result.character_autonomy_score)  # 人物自治度 0-10
print(result.summary)                   # 审查摘要

# 保存到数据库
await save_llm_audit(
    db=ReviewReportRepository(),
    version_id=chapter_version.version_id,
    result=result,
)
```

---

## 设计要点

- **12 维度审查**：world_consistency, character_behavior, timeline, new_setting_unregistered, narrative_pacing, narrative_hook, info_dump, dialogue_distinctness, dialogue_subtext, description_sensory, show_dont_tell, genre_numerical
- **JSON 解析**：复用公共 `llm/parsing.py` 的 `extract_json` + `parse_llm_response`
- **字段验证**：无效 category 过滤，无效 severity/fix_type 回退，score clamp 到 0-10
- **正文截断**：MAX_CONTENT_LENGTH=8000，防止超长正文超出 Token 预算
- **温度策略**：0.3（比 Writer 0.8 低，要求稳定的审查输出）
- **综合评分**：维度平均分×0.7 + 文学性加权×0.3 - critical/major 扣分
