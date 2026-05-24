# Task 014: LiteraryAuditor Agent — 完整开发指令

> **用途**: 将本文档作为完整上下文交给 AI，直接开始编码 Task 014。
> **状态**: 规格已确定，待编码实现。

---

## 1. 项目背景

**Songyan** 是一个多 Agent 小说写作系统。当前处于 Phase 2 — Agent 能力层开发阶段。

### 技术栈
- Python 3.11.4, Pydantic v2, pytest+pytest-asyncio
- LangGraph>=0.2, LangChain 1.3.1, langchain-litellm (ChatLiteLLM)
- SQLite (aiosqlite) 唯一长期事实源，WAL 模式
- 架构约束：单文件 < 400 行，所有函数带类型标注，异步优先 async/await

### 当前测试基线
- **469 passed**, ruff 0 errors
- **Git 状态**: 本地与 origin/main 同步

---

## 2. 已完成任务（上下文）

```
Phase 1 基础设施:
  Task 001-007: 项目初始化、Pydantic 模型、SQLite Schema、Repository 层、
                Genre Profile、CreativeModeProfile、CLI 创建项目
  Task 017: Quality Utils (AI腔/疲劳词/钩子/段落节奏/数值验证, 77 tests)

Phase 2 Agent 能力层:
  Task 008: GoalPlanner (LLM Client + 章节目标, 32 tests)
  Task 009: CreativeDirector (CreativeBrief + 张力地图, 23 tests)
  Task 010: ContextManager (上下文包组装 + Token 预算裁剪, 36 tests)
  Task 011: Writer (章节正文生成 + Scene 分割 + 版本保存, 37 tests)
  Task 012: RuleAuditor (纯代码规则检测 + Quality Utils, 29 tests)
  Task 013: LLMAuditor (LLM 语义审查 12 维度 + JSON 解析, 33 tests)
```

---

## 3. Task 014 目标

实现 **LiteraryAuditor Agent** —— 文学性诊断，不阻塞主流程。

### 核心特性
- **不阻塞流程**：即使诊断失败，也不影响章节进入 Revision/Settlement
- **仅供人工参考**：输出不直接驱动 RevisionHandler
- **观察性而非评判性**：重点是"发现有趣的裂隙"而非"挑错"

### 需要创建的文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/literary_auditor.py` | Agent 主代码 |
| `prompts/literary_auditor.md` | Prompt 模板 |
| `tests/test_literary_auditor.py` | 测试 |
| `tasks/014-literary-auditor-DONE.md` | 完成交接文件 |

### 需要修改的文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `run_literary_audit`, `save_literary_audit` |

---

## 4. 数据模型（已存在，直接使用）

```python
# src/songyan/models/literary.py

class LiteraryObservation(BaseModel):
    observation_id: str
    observation_type: Literal[
        "character_tooling",      # 人物工具化
        "conceptual_idling",      # 概念空转
        "excessive_smoothing",    # 过度润滑
        "valuable_fissure",       # 有价值的裂隙
        "cliche_risk",            # 套路化风险
        "polyphony_weakness",     # 复调弱化
        "authorial_intrusion",    # 作者侵入
    ]
    description: str
    evidence_quote: str | None = None
    severity: Literal["notice", "suggestion", "highlight"] = "suggestion"
    recommendation: str = ""
    preserve: bool = False  # 对 valuable_fissure 建议保留


class LiteraryAuditResult(BaseModel):
    auditor_id: str = "literary_auditor"
    observations: list[LiteraryObservation] = Field(default_factory=list)
    literary_quality_score: float = 0.0      # 整体文学质量 0-10
    character_autonomy_score: float = 0.0    # 人物自治度 0-10
    conceptual_grounding_score: float = 0.0  # 概念落地度 0-10
    fissure_preservation_score: float = 0.0  # 裂隙保留度 0-10
    summary: str = ""
    duration_ms: int = 0
```

### 评分维度说明

| 维度 | 高分标准 |
|------|---------|
| literary_quality_score | 描写有质感、节奏有变化 |
| character_autonomy_score | 人物做出出乎作者意料的选择 |
| conceptual_grounding_score | 抽象概念通过具体场景呈现 |
| fissure_preservation_score | 有价值的异常/矛盾被保留而非抹平 |

---

## 5. 接口契约

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
        temperature: LLM 温度（默认 0.5，比 LLMAuditor 0.3 略高，鼓励创造性观察）
    """

async def save_literary_audit(
    db: LiteraryObservationRepository,
    version_id: str,
    result: LiteraryAuditResult,
    observation_id: str | None = None,
) -> None:
    """保存 LiteraryAuditResult 到 literary_observations 表."""
```

---

## 6. Prompt 模板设计

创建 `prompts/literary_auditor.md`，参考 `prompts/llm_auditor.md` 的风格。

Prompt 应注入：
- 章节正文（截断到 MAX_CONTENT_LENGTH=8000）
- 创作意图（creative_intent）
- 允许裂隙（allowed_fissures）
- 张力地图（required_tensions）
- 7 类观察类型的具体说明

输出 JSON 格式：
```json
{
  "observations": [
    {
      "observation_id": "obs_001",
      "observation_type": "valuable_fissure",
      "description": "描述",
      "evidence_quote": "原文引用",
      "severity": "highlight",
      "recommendation": "建议",
      "preserve": true
    }
  ],
  "literary_quality_score": 7.5,
  "character_autonomy_score": 8.0,
  "conceptual_grounding_score": 6.5,
  "fissure_preservation_score": 7.0,
  "summary": "3-5句话概括文学性诊断结论"
}
```

**重要规则**：
1. valuable_fissure 类型的观察，preserve 应设为 true
2. severity 必须是 notice/suggestion/highlight 之一
3. observation_type 必须是 7 种之一
4. 所有评分 0-10
5. 不要包含 markdown 代码块标记之外的文本

---

## 7. 参考实现模式

### 7.1 Agent 结构（参考 LLMAuditor）

```python
# src/songyan/agents/literary_auditor.py

from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import LiteraryAuditResult, LiteraryObservation, ContextPackage

MAX_CONTENT_LENGTH = 8000
VALID_OBSERVATION_TYPES = {
    "character_tooling", "conceptual_idling", "excessive_smoothing",
    "valuable_fissure", "cliche_risk", "polyphony_weakness", "authorial_intrusion",
}
VALID_SEVERITIES = {"notice", "suggestion", "highlight"}


def _load_prompt_template() -> str:
    ...  # 加载 prompts/literary_auditor.md


def _render_prompt(content: str, context_package: ContextPackage | None) -> str:
    ...  # 变量替换


def _validate_observation_type(value: str) -> str | None:
    ...  # 无效返回 None


def _validate_severity(value: str) -> str:
    ...  # 无效回退到 "suggestion"


def _build_observation(data: dict, index: int) -> LiteraryObservation | None:
    ...  # 从 dict 构建 LiteraryObservation


def _build_literary_audit_result(data: dict) -> LiteraryAuditResult:
    ...  # 组装结果，评分 clamp 到 0-10


async def run_literary_audit(...) -> LiteraryAuditResult:
    start_time = time.perf_counter()
    prompt = _render_prompt(content, context_package)
    llm_response = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_response)
    result = _build_literary_audit_result(data)
    result.duration_ms = int((time.perf_counter() - start_time) * 1000)
    return result


async def save_literary_audit(...) -> None:
    ...  # 调用 db.create()
```

### 7.2 测试结构（参考 test_llm_auditor.py）

```python
# tests/test_literary_auditor.py

class TestRenderPrompt:
    def test_loads_template(self): ...
    def test_includes_context(self): ...

class TestValidateObservationType:
    def test_valid(self): ...
    def test_invalid(self): ...

class TestBuildObservation:
    def test_valid(self): ...
    def test_invalid_type_filtered(self): ...
    def test_valuable_fissure_preserve(self): ...

class TestBuildLiteraryAuditResult:
    def test_full_result(self): ...
    def test_scores_clamped(self): ...

class TestRunLiteraryAudit:
    async def test_full_flow(self): ...
    async def test_invalid_json(self): ...

class TestSaveLiteraryAudit:
    async def test_save(self): ...
```

---

## 8. 关键注意事项

### 8.1 与 LLMAuditor 的区别

| | LLMAuditor | LiteraryAuditor |
|--|-----------|-----------------|
| 目的 | 找出问题并建议修复 | 发现裂隙并建议保留 |
| severity | critical/major/minor/info | notice/suggestion/highlight |
| 阻塞性 | 是（产生 Revision） | 否（仅供人工参考） |
| 温度 | 0.3（稳定） | 0.5（创造性观察） |
| 保存表 | review_reports | literary_observations |

### 8.2 代码规范
- 单文件 < 400 行
- 所有函数带类型标注
- 使用 `from __future__ import annotations`
- 复用 `llm/parsing.py` 的 `parse_llm_response()`
- 复用 `llm/client.py` 的 `call_llm()`
- 使用 `structlog` 记录日志

### 8.3 测试要求
- 新增测试全部通过
- 全量测试通过（当前 469 passed）
- ruff 0 errors

---

## 9. 实现步骤建议

1. 创建 `prompts/literary_auditor.md`
2. 创建 `src/songyan/agents/literary_auditor.py`
3. 修改 `src/songyan/agents/__init__.py` 导出
4. 创建 `tests/test_literary_auditor.py`
5. 运行 `pytest tests/test_literary_auditor.py -v`
6. 运行 `pytest tests/ -v` 确认全量通过
7. 运行 `ruff check src/ tests/`
8. 创建 `tasks/014-literary-auditor-DONE.md`
9. 更新 `docs/STATUS.md`
10. `git add -A && git commit && git push origin main`

---

## 10. 可用 Repository

```python
from songyan.db.review_repo import LiteraryObservationRepository

class LiteraryObservationRepository:
    async def create(self, result: LiteraryAuditResult, observation_id: str, version_id: str) -> None
    async def get_by_version(self, version_id: str) -> LiteraryAuditResult | None
```

---

## 11. 已有相关文件路径

```
src/songyan/models/literary.py          # LiteraryAuditResult, LiteraryObservation
src/songyan/models/context.py            # ContextPackage
src/songyan/db/review_repo.py            # LiteraryObservationRepository
src/songyan/llm/client.py                # call_llm()
src/songyan/llm/parsing.py               # parse_llm_response()
src/songyan/agents/llm_auditor.py        # 参考实现
prompts/llm_auditor.md                   # Prompt 风格参考
tests/test_llm_auditor.py                # 测试结构参考
```
