# Songyan TDD（测试驱动开发）方案

> 目标：让每个 AI 在开发时都有明确的"先写测试 → 再写实现 → 验证通过"的闭环，且测试标准能被自动化验证。

---

## 1. TDD 三层模型

```
┌─────────────────────────────────────────────┐
│  Layer 3: 集成测试（Integration Tests）      │
│  - 跨模块端到端测试                          │
│  - LangGraph 工作流测试                      │
│  - 每个 Phase 完成后运行                     │
├─────────────────────────────────────────────┤
│  Layer 2: 模块测试（Module Tests）           │
│  - 单个 Agent/Service 的输入输出测试         │
│  - Mock LLM / Mock DB                        │
│  - 每个 Task 完成后必须运行                  │
├─────────────────────────────────────────────┤
│  Layer 1: 模型测试（Model Tests）            │
│  - Pydantic 模型验证                         │
│  - 数据转换/序列化测试                       │
│  - 每个数据模型变更后运行                    │
└─────────────────────────────────────────────┘
```

---

## 2. AI 的 TDD 工作流

每个 Task 的开发遵循 **Red → Green → Refactor** 循环：

```
1. 读取 Task 规格 → 理解输入输出契约
        │
        ▼
2. 写测试（先不写实现）
   - test_input_output.py — 验证输入输出格式
   - test_edge_cases.py — 边界条件
   - test_error_handling.py — 错误处理
        │
        ▼
3. 运行测试 → 预期失败（Red）
   pytest tests/test_xxx.py -v
        │
        ▼
4. 写最小实现 → 让测试通过（Green）
        │
        ▼
5. 运行测试 → 验证通过
        │
        ▼
6. 重构 → 保持测试通过（Refactor）
        │
        ▼
7. 生成 DONE.md → 交接
```

---

## 3. 每层测试的具体内容

### 3.1 Layer 1: 模型测试（Model Tests）

**每个 Pydantic 模型必须有测试**：

```python
# tests/test_models.py
import pytest
from songyan.models.project import ProjectSetting
from songyan.models.creative_mode import CreativeModeProfile

def test_project_setting_validation():
    """ProjectSetting 必须能正确验证"""
    setting = ProjectSetting(
        title="测试小说",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="张三",
    )
    assert setting.title == "测试小说"
    assert setting.mode_id == "webnovel"

def test_project_setting_default_mode():
    """默认 mode 必须是 webnovel"""
    setting = ProjectSetting(
        genre_id="xuanhuan",
        protagonist_name="张三",
    )
    assert setting.mode_id == "webnovel"

def test_project_setting_invalid_genre():
    """无效 genre_id 应该允许（由加载器校验，不在模型层）"""
    # 模型层不校验 genre_id 是否存在，由 GenreProfileLoader 校验
    setting = ProjectSetting(
        genre_id="invalid_genre",
        protagonist_name="张三",
    )
    assert setting.genre_id == "invalid_genre"

def test_creative_mode_profile_from_dict():
    """CreativeModeProfile 必须能从 dict 加载"""
    data = {
        "id": "webnovel",
        "name": "网文模式",
        "enabled_nodes": {"pre_write": ["goal_planner"]},
        "audit_weights": {"narrative_pacing": 1.2},
    }
    mode = CreativeModeProfile(**data)
    assert mode.id == "webnovel"
    assert mode.audit_weights["narrative_pacing"] == 1.2
```

**测试标准**：
- 所有模型字段都有默认值或必须值测试
- 复杂嵌套模型（如 ContextPackage）有完整组装/拆解测试
- 枚举值（ReviewCategory、PipelineStage）有全部值测试

### 3.2 Layer 2: 模块测试（Module Tests）

**每个 Agent/Service 必须有测试**，使用 Mock：

```python
# tests/test_goal_planner.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from songyan.agents.goal_planner import define_chapter_goal
from songyan.models.project import ProjectSetting
from songyan.models.chapter import ChapterGoal

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.projects.get = AsyncMock(return_value=ProjectSetting(
        title="测试小说",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="张三",
        core_hook="打脸升级",
    ))
    db.chapter_versions.list_by_project = AsyncMock(return_value=[])
    return db

@pytest.fixture
def mock_llm():
    """Mock LLM 返回固定结构"""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content='''
    {
        "chapter_number": 1,
        "target_events": ["主角发现神秘洞穴"],
        "emotional_arc": "好奇→紧张",
        "hooks": ["洞穴深处传来低语"],
        "word_count_target": 3000,
        "chapter_type": "布局章"
    }
    '''))
    return llm

@pytest.mark.asyncio
async def test_goal_planner_output_structure(mock_db, mock_llm):
    """GoalPlanner 必须输出结构化 ChapterGoal"""
    result = await define_chapter_goal(
        project_id="test-project",
        chapter_number=1,
        db=mock_db,
        llm=mock_llm,
    )
    assert isinstance(result, ChapterGoal)
    assert result.chapter_number == 1
    assert len(result.target_events) >= 1
    assert result.word_count_target > 0

@pytest.mark.asyncio
async def test_goal_planner_respects_genre_pacing(mock_db, mock_llm):
    """GoalPlanner 必须遵守 Genre Profile 的节奏规则"""
    result = await define_chapter_goal(
        project_id="test-project",
        chapter_number=1,
        db=mock_db,
        llm=mock_llm,
    )
    # 玄幻题材 pacing_rule: "三章内必有明确反馈"
    # ChapterGoal 应该包含至少 1 个能产生反馈的事件
    assert len(result.target_events) >= 1
```

**Mock 策略**：
- **Mock DB**：返回固定的测试数据，不连接真实 SQLite
- **Mock LLM**：返回固定的 JSON 响应，不调用真实 API
- **Mock 文件系统**：对 `genres/*.json` 的加载使用临时文件

**测试标准**：
- 每个公共函数/方法至少有 1 个正向测试
- 每个错误路径至少有 1 个异常测试
- 边界条件（空输入、最大值、特殊字符）有测试

### 3.3 Layer 3: 集成测试（Integration Tests）

**每个 Phase 完成后运行端到端测试**：

```python
# tests/test_graph.py
import pytest
from songyan.workflows.phase1_graph import build_phase1_graph

@pytest.mark.asyncio
async def test_full_phase1_workflow():
    """Phase 1 完整工作流测试"""
    graph = build_phase1_graph()
    
    # 初始化状态
    initial_state = {
        "project_id": "test-project",
        "chapter_number": 1,
        "mode_id": "webnovel",
        "current_version_id": None,
        "revision_round": 0,
        "status": "init",
    }
    
    # 运行工作流（使用 Mock DB 和 Mock LLM）
    result = await graph.ainvoke(initial_state)
    
    # 验证最终状态
    assert result["status"] == "done"
    assert result["current_version_id"] is not None
    assert result["revision_round"] <= 2
```

**集成测试标准**：
- 每个 LangGraph 节点至少被调用一次
- 数据流从起点到终点完整验证
- 错误分支（如 RevisionHandler 触发 2 轮后仍有问题）有测试

---

## 4. 测试覆盖标准

| 层级 | 覆盖率目标 | 验证时机 | 失败处理 |
|------|-----------|----------|----------|
| 模型测试 | 100% 模型字段 | 每次模型变更 | 阻塞提交 |
| 模块测试 | > 80% 公共接口 | 每个 Task 完成 | 阻塞交接 |
| 集成测试 | 所有工作流分支 | 每个 Phase 完成 | 阻塞进入下一阶段 |

---

## 5. AI 应该在哪一步测试什么

### 5.1 Phase 1（基础设施）：模型 + Repository 测试

**Task 001 完成后**：
```bash
pytest tests/test_init.py -v
# 验证：import songyan 成功、目录结构正确
```

**Task 002 完成后**：
```bash
pytest tests/test_models.py -v
# 验证：所有 Pydantic 模型可实例化、验证正确
```

**Task 003 完成后**：
```bash
pytest tests/test_db.py -v
# 验证：schema 可创建、连接可开关
```

**Task 004 完成后**：
```bash
pytest tests/test_repository.py -v
# 验证：所有 CRUD 操作正确、版本链可追溯
```

### 5.2 Phase 2（写前管线）：Agent 输入输出测试

**Task 007-011 完成后**：
```bash
pytest tests/test_goal_planner.py -v
pytest tests/test_creative_director.py -v
pytest tests/test_context_manager.py -v
pytest tests/test_writer.py -v
# 验证：每个 Agent 输出符合契约、Mock LLM 测试通过
```

### 5.3 Phase 3（审查修订）：规则检测 + 语义审查测试

**Task 012-015 完成后**：
```bash
pytest tests/test_rule_auditor.py -v
pytest tests/test_llm_auditor.py -v
pytest tests/test_literary_auditor.py -v
pytest tests/test_revision_handler.py -v
# 验证：RuleAuditor < 200ms、LLMAuditor 输出符合结构
```

### 5.4 Phase 4（结算闭环）：集成测试

**Task 016-019 完成后**：
```bash
pytest tests/test_graph.py -v
pytest tests/test_settlement_extractor.py -v
# 验证：完整工作流跑通、状态结算正确
```

---

## 6. 测试自动化验证

### 6.1 Makefile / Task Runner

```makefile
# Makefile
.PHONY: test test-models test-modules test-integration test-all

test:
	pytest tests/ -v

test-models:
	pytest tests/test_models.py -v

test-modules:
	pytest tests/test_*.py --ignore=tests/test_graph.py -v

test-integration:
	pytest tests/test_graph.py -v

test-all:
	pytest tests/ -v --cov=songyan --cov-report=term-missing
```

### 6.2 CI 预检查（本地）

```bash
# pre-commit 或手动运行
make test-all
# 覆盖率 < 80% 或任何测试失败 → 阻塞提交
```

### 6.3 交接时的测试报告

每个 DONE.md 必须包含测试报告：

```markdown
## 测试报告

```bash
$ pytest tests/test_xxx.py -v
============================= test session starts ==============================
tests/test_xxx.py::test_case_1 PASSED
tests/test_xxx.py::test_case_2 PASSED
tests/test_xxx.py::test_case_3 PASSED
============================== 3 passed in 0.5s ===============================
```

- 测试覆盖率：85%（模块层）
- 无已知失败的测试
```

---

## 7. Mock 工具集

### 7.1 Mock LLM（共用）

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm():
    """返回可配置响应的 Mock LLM"""
    def _factory(response_content: str):
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=MagicMock(content=response_content))
        return llm
    return _factory

@pytest.fixture
def mock_db():
    """返回内存 SQLite 的 Mock DB"""
    from songyan.db.connection import get_test_db
    return get_test_db()
```

### 7.2 测试数据工厂

```python
# tests/factories.py
from songyan.models.project import ProjectSetting
from songyan.models.chapter import ChapterGoal

def make_project(**kwargs) -> ProjectSetting:
    defaults = {
        "title": "测试小说",
        "genre_id": "xuanhuan",
        "mode_id": "webnovel",
        "protagonist_name": "张三",
        "core_hook": "打脸升级",
    }
    defaults.update(kwargs)
    return ProjectSetting(**defaults)

def make_chapter_goal(**kwargs) -> ChapterGoal:
    defaults = {
        "chapter_number": 1,
        "target_events": ["事件1"],
        "emotional_arc": "压抑→爆发",
        "hooks": ["钩子1"],
        "word_count_target": 3000,
        "chapter_type": "布局章",
    }
    defaults.update(kwargs)
    return ChapterGoal(**defaults)
```

---

## 8. 验收指标与测试映射

| 验收指标 | 对应测试 | 验证方式 |
|----------|----------|----------|
| 设定硬错误数 = 0 | `test_world_consistency_zero_critical` | Mock LLM 返回 critical issue → 断言流程进入修订 |
| AI 腔 < 2 处/章 | `test_ai_tells_count` | 输入含 AI 腔文本 → 断言检测结果 < 2 |
| 疲劳词 < 3 处/章 | `test_fatigue_words_count` | 输入含疲劳词文本 → 断言检测结果 < 3 |
| 状态结算准确率 > 90% | `test_settlement_old_value_match` | Mock DB 返回固定值 → 断言 settlement 一致 |
| 首屏钩子达标率 100% | `test_opening_hook_detection` | 输入无钩子文本 → 断言 has_opening_hook = False |
| 章末钩子达标率 100% | `test_ending_hook_detection` | 输入无钩子文本 → 断言 has_ending_hook = False |

---

> **核心原则：每个 Task 必须有测试，每个交接必须有测试报告，每个 Phase 必须有集成测试。**
