# Task 016: SettlementExtractor Agent — 完成报告

> **完成日期**: 2026-05-25
> **提交**: (待填写)

---

## 做了什么

实现了 SettlementExtractor Agent —— 章节 accept 后的结构化状态结算。从 accepted 正文中提取角色状态变更、新设定登记、伏笔操作、数值变更，经代码层验证后 INSERT 新快照到 SQLite。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/settlement_extractor.py` | SettlementExtractor：`extract_settlement()` 加载当前状态 → Prompt 渲染 → LLM 调用 → JSON 解析 → `_build_state_settlement()` → `_validate_settlement()` 5 条规则验证 → `apply_settlement()` INSERT 新快照 |
| `prompts/settlement_extractor.md` | SettlementExtractor Prompt 模板（4 类变更提取 + JSON 输出格式） |
| `tests/test_settlement_extractor.py` | SettlementExtractor 测试（40 个测试） |
| `tasks/016-settlement-extractor.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `extract_settlement`, `apply_settlement` |

---

## 如何运行

```bash
# 运行 SettlementExtractor 测试
pytest tests/test_settlement_extractor.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：576 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不做摘要生成（后续 Task 负责）
- 不做 LangGraph 编排
- 不做 HumanConfirm 节点逻辑
- 不处理数值公式之外的数值校验（如境界体系合法性）

---

## 接口使用示例

```python
from songyan.agents.settlement_extractor import extract_settlement, apply_settlement
from songyan.models import GenreRules

# 执行状态结算
settlement = await extract_settlement(
    content=accepted_version.content,
    project_id=project_id,
    chapter_number=chapter_number,
    version_id=accepted_version.version_id,
    genre_rules=GenreRules(pacing_rule="快节奏"),
    temperature=0.3,
)

print(len(settlement.character_updates))      # 角色状态变更数
print(len(settlement.new_settings))            # 新设定登记数
print(len(settlement.foreshadowing_updates))   # 伏笔操作数
print(len(settlement.numerical_updates))       # 数值变更数
print(settlement.validation_status)            # valid / needs_human_review / failed
print(settlement.validation_errors)            # 验证错误列表

# 验证通过后应用结算
if settlement.validation_status == "valid":
    await apply_settlement(
        settlement=settlement,
        project_id=project_id,
        chapter_number=chapter_number,
        version_id=accepted_version.version_id,
    )
```

---

## 设计要点

- **5 条验证规则**：old_value 匹配、source_quote 存在、setting_key 唯一、closing_value 公式、source_version_id 非空
- **INSERT 不 UPDATE**：character_states / setting_snapshots / numerical_ledgers / foreshadowings 均为快照表，只 INSERT
- **复用已有 Repository**：`CharacterRepository.add_state_snapshot()` 已存在，直接复用；`ForeshadowingRepository` / `SettingSnapshotRepository` / `NumericalLedgerRepository` 已有
- **验证失败不阻塞**：`needs_human_review` 状态 + validation_errors，调用方可自行决定后续流程
- **温度 0.3**：精确提取，与 RevisionHandler 一致
- **GenreRules 可选**：玄幻项目注入数值规则，其他题材可不传
