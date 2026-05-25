# Task 014: LiteraryAuditor Agent — 完成交接

## 状态
✅ 已完成

## 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/literary_auditor.py` | Agent 主代码（220 行） |
| `prompts/literary_auditor.md` | Prompt 模板（文学性诊断） |
| `tests/test_literary_auditor.py` | 测试（29 个 case） |
| `tasks/014-literary-auditor-DONE.md` | 本交接文件 |

## 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_literary_audit`, `save_literary_audit` |

## 核心特性

- **不阻塞流程**：即使诊断失败，也不影响章节进入 Revision/Settlement
- **仅供人工参考**：输出不直接驱动 RevisionHandler
- **观察性而非评判性**：重点是"发现有趣的裂隙"而非"挑错"
- 7 类观察类型：character_tooling / conceptual_idling / excessive_smoothing / valuable_fissure / cliche_risk / polyphony_weakness / authorial_intrusion
- 4 项评分：literary_quality_score / character_autonomy_score / conceptual_grounding_score / fissure_preservation_score
- valuable_fissure 类型自动设置 preserve=True
- 温度默认 0.5（略高于 LLMAuditor 的 0.3，鼓励创造性观察）

## 验证结果

- `pytest tests/test_literary_auditor.py -v` → **29 passed**
- `pytest tests/ -v` → **498 passed**（基线 469 + 新增 29）
- `ruff check src/ tests/` → **0 errors**
