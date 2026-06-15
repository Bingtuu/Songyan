# Task 014: LiteraryAuditor Agent — 完成报告

> **完成日期**: 2026-05-25
> **提交**: 6609886

---

## 做了什么

实现了 LiteraryAuditor Agent —— 文学性诊断，不阻塞主流程。对章节进行文学层面的深度观察，识别人物工具化、概念空转、过度润滑、有价值裂隙、套路化风险、复调弱化、作者侵入等 7 类文学性问题，输出 4 维度评分（整体文学质量、人物自治度、概念落地度、裂隙保留度）。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/literary_auditor.py` | LiteraryAuditor：`run_literary_audit()` Prompt 渲染 → LLM 调用 → JSON 解析 → LiteraryAuditResult + `save_literary_audit()` 保存到 `literary_observations` 表 |
| `prompts/literary_auditor.md` | LiteraryAuditor Prompt 模板（7 类观察类型 + 4 维度评分 + JSON 输出格式） |
| `tests/test_literary_auditor.py` | LiteraryAuditor 测试（29 个测试） |
| `tasks/014-literary-auditor.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_literary_audit`, `save_literary_audit` |

---

## 如何运行

```bash
# 运行 LiteraryAuditor 测试
pytest tests/test_literary_auditor.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：498 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不驱动 RevisionHandler（文学性诊断不直接产生修订，仅供人工参考）
- 不做数值验证（RuleAuditor 已覆盖，Task 012）
- 不做设定一致性检查（LLMAuditor 已覆盖，Task 013）
- 不做 LangGraph 编排（Task 019 负责）

---

## 接口使用示例

```python
from songyan.agents.literary_auditor import run_literary_audit, save_literary_audit
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.models import ContextPackage

# 运行文学性诊断
result = await run_literary_audit(
    content=chapter_version.content,
    context_package=context_package,
    temperature=0.5,
)

print(len(result.observations))              # 观察数量
print(result.literary_quality_score)          # 整体文学质量 0-10
print(result.character_autonomy_score)        # 人物自治度 0-10
print(result.conceptual_grounding_score)      # 概念落地度 0-10
print(result.fissure_preservation_score)      # 裂隙保留度 0-10
print(result.summary)                         # 诊断摘要

# 保存到数据库
await save_literary_audit(
    db=LiteraryObservationRepository(),
    version_id=chapter_version.version_id,
    result=result,
)
```

---

## 设计要点

- **7 类观察类型**：character_tooling, conceptual_idling, excessive_smoothing, valuable_fissure, cliche_risk, polyphony_weakness, authorial_intrusion
- **4 维度评分**：literary_quality_score, character_autonomy_score, conceptual_grounding_score, fissure_preservation_score（全部 clamp 到 0-10）
- **valuable_fissure 保护**：`observation_type == "valuable_fissure"` 时强制 `preserve=True`，供 RevisionHandler 识别保护
- **JSON 解析**：复用 `llm/parsing.py` 的 `parse_llm_response`
- **字段验证**：无效 observation_type 过滤，无效 severity 回退到 "suggestion"
- **正文截断**：MAX_CONTENT_LENGTH=8000
- **温度策略**：0.5（比 LLMAuditor 0.3 略高，鼓励创造性观察）
- **不阻塞流程**：即使 LLM 调用失败或 JSON 解析失败，也不会抛出阻塞异常（`parse_llm_response` 会抛出 `LLMResponseParseError`，但调用方可选择是否捕获）
