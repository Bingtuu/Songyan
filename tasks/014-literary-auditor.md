# Task 014: LiteraryAuditor Agent

> **Phase**: Phase 2 — 审查环节（可选，不阻塞流程）
> **优先级**: P1
> **依赖**: Task 011 (Writer Agent)
> **预计工作量**: 小

---

## Goal

实现 LiteraryAuditor Agent —— 文学性诊断，不阻塞主流程。对章节进行文学层面的深度观察，识别人物工具化、概念空转、过度润滑、有价值裂隙、套路化风险、复调弱化、作者侵入等 7 类文学性问题。

## Context

LiteraryAuditor 是审查环节的**可选** Agent，与 RuleAuditor（规则检测）和 LLMAuditor（语义审查）形成互补：
- RuleAuditor：表层模式检测（AI 腔、疲劳词、钩子、节奏）
- LLMAuditor：中层语义审查（设定一致性、叙事质量、对话质量、描写质量）
- **LiteraryAuditor**：深层文学诊断（人物自治、概念落地、裂隙保留、复调强度）

**关键特性**：
- 不阻塞流程：即使诊断失败，也不影响章节进入 Revision/Settlement
- 仅供人工参考：输出不直接驱动 RevisionHandler
- 观察性而非评判性：重点是"发现有趣的裂隙"而非"挑错"

## In Scope（必须完成）

- [ ] `run_literary_audit()` 主入口 — 可纯代码 + 可选 LLM
- [ ] Prompt 模板：`prompts/literary_auditor.md`
- [ ] 7 类文学性观察识别
- [ ] 组装 `LiteraryAuditResult`（observations + 4 维度评分）
- [ ] 保存到 `literary_observations` 表
- [ ] 测试：Prompt 渲染、结果组装、边界条件、集成测试

## Out of Scope（明确不做）

- 不驱动 RevisionHandler（文学性诊断不直接产生修订）
- 不做数值验证（RuleAuditor 已覆盖）
- 不做设定一致性检查（LLMAuditor 已覆盖）

## 接口契约

```python
async def run_literary_audit(
    content: str,
    context_package: ContextPackage | None = None,
    temperature: float = 0.5,
) -> LiteraryAuditResult:
    """运行文学性诊断（可选，不阻塞流程）.

    Args:
        content: 章节正文
        context_package: 上下文包（提供创作意图、张力地图、允许裂隙等）
        temperature: LLM 温度（默认 0.5，比 LLMAuditor 略高以鼓励创造性观察）

    Returns:
        LiteraryAuditResult
    """

async def save_literary_audit(
    db: LiteraryObservationRepository,
    version_id: str,
    result: LiteraryAuditResult,
    observation_id: str | None = None,
) -> None:
    """保存 LiteraryAuditResult 到 literary_observations 表."""
```

## 数据模型

复用已有模型：
- `LiteraryAuditResult` — 文学审计结果
- `LiteraryObservation` — 单个观察

### 观察类型说明

| 类型 | 说明 | severity 建议 |
|------|------|--------------|
| character_tooling | 人物成为剧情工具，缺乏自主决策 | notice/suggestion |
| conceptual_idling | 概念在空中打转，没有落地到具体场景 | suggestion |
| excessive_smoothing | 过度润滑——所有矛盾都被平滑处理，缺乏张力 | suggestion |
| valuable_fissure | 有价值的裂隙——看似不合逻辑但可深挖的细节 | highlight |
| cliche_risk | 套路化风险——情节/描写落入俗套 | notice |
| polyphony_weakness | 复调弱化——所有声音听起来像同一个人 | suggestion |
| authorial_intrusion | 作者侵入——叙述者声音压过了人物声音 | notice |

### 评分维度

| 维度 | 说明 | 高分标准 |
|------|------|---------|
| literary_quality_score | 整体文学质量 | 描写有质感、节奏有变化 |
| character_autonomy_score | 人物自治度 | 人物做出出乎作者意料的选择 |
| conceptual_grounding_score | 概念落地度 | 抽象概念通过具体场景呈现 |
| fissure_preservation_score | 裂隙保留度 | 有价值的异常/矛盾被保留而非抹平 |

## 测试要求

### Layer 1: Prompt 渲染
- [ ] ContextPackage 正确注入（创作意图、张力地图、允许裂隙）
- [ ] 正文截断（参考 LLMAuditor MAX_CONTENT_LENGTH）

### Layer 2: 结果组装
- [ ] observations 正确解析
- [ ] 无效 observation_type 过滤
- [ ] severity 回退
- [ ] preserve 标记对 valuable_fissure 设为 True
- [ ] 4 维度评分 clamp 到 0-10

### Layer 3: 保存验证
- [ ] Mock DB 保存调用

### Layer 4: 集成测试
- [ ] Mock LLM → 完整流程

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_literary_auditor.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 tasks/014-literary-auditor-DONE.md 交接文件

## 参考实现

参考 Task 013 LLMAuditor 的结构：
- `src/songyan/agents/llm_auditor.py` — Prompt 渲染 + LLM 调用 + JSON 解析 + 结果组装
- `src/songyan/llm/parsing.py` — 复用 `parse_llm_response()`
- `tests/test_llm_auditor.py` — 测试结构
