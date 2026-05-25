# Task 016: SettlementExtractor Agent

> **Phase**: Phase 2 — 结算环节
> **优先级**: P0
> **依赖**: Task 011 (Writer), Task 015 (RevisionHandler), 项目 accept 状态
> **预计工作量**: 中

---

## Goal

实现 SettlementExtractor Agent —— 章节 accept 后的结构化状态结算。从 accepted 正文中提取角色状态变更、新设定登记、伏笔操作、数值变更，经代码层验证后 INSERT 新快照到 SQLite。

## Context

SettlementExtractor 是单章闭环的最后一步：

```
Writer → 审查 → RevisionHandler → [accept] → SettlementExtractor → 摘要生成 → done
```

**关键特性**：
- **必须执行**：每章 accept 后必须执行 SettlementExtractor
- **代码验证**：所有 LLM 提取的变更必须经过代码层验证
- **INSERT 不 UPDATE**：character_states 是快照表，永远 INSERT 新记录
- **验证失败不阻塞**：标记 `needs_human_review`，不影响流程继续

## In Scope（必须完成）

- [ ] `extract_settlement()` 主入口 — 加载当前状态 → Prompt 渲染 → LLM 调用 → JSON 解析 → `StateSettlement`
- [ ] `_validate_settlement()` — 代码层验证（old_value、source_quote、setting_key、closing_value）
- [ ] `_apply_settlement()` — 将验证通过的结算结果应用到 DB（INSERT 新快照）
- [ ] `CharacterStateRepository.insert_snapshot()` — 新增方法（快照表 INSERT）⭐
- [ ] Prompt 模板：`prompts/settlement_extractor.md`
- [ ] 测试：验证逻辑、Prompt 渲染、结果组装、DB 应用、集成测试

## Out of Scope（明确不做）

- 不做摘要生成（后续 Task 负责）
- 不做 LangGraph 编排
- 不做 HumanConfirm 节点逻辑（调用方负责在 accept 后触发 SettlementExtractor）
- 不做数值公式之外的数值校验（如境界体系合法性）

## 接口契约

```python
async def extract_settlement(
    content: str,
    project_id: str,
    chapter_number: int,
    version_id: str,
    genre_rules: GenreRules | None = None,
    temperature: float = 0.3,
) -> StateSettlement:
    """执行状态结算 — LLM 提取 + 代码验证.

    Args:
        content: accepted 章节正文
        project_id: 项目 ID
        chapter_number: 章节号
        version_id: accepted 版本 ID（写入 source_version_id）
        genre_rules: 题材规则（可选，用于注入玄幻数值规则等）
        temperature: LLM 温度（默认 0.3，精确提取）

    Returns:
        StateSettlement（含 validation_status 和 validation_errors）
    """

async def apply_settlement(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
) -> None:
    """将验证通过的结算结果应用到数据库 — INSERT 新快照，不 UPDATE 旧记录.

    Args:
        settlement: 验证通过的 StateSettlement
        project_id: 项目 ID
        chapter_number: 章节号
        version_id: 关联版本 ID
    """
```

## 数据模型

复用已有模型：
- `StateSettlement` — 完整结算结果
- `CharacterUpdate` — 角色状态变更
- `NewSetting` — 新设定登记
- `ForeshadowingUpdate` — 伏笔操作
- `NumericalUpdate` / `Increment` / `Decrement` — 数值变更

### 验证规则

| 规则 | 验证内容 | 失败处理 |
|------|---------|---------|
| old_value 匹配 | `character_update.old_value` 必须与 DB 当前值一致 | 记录 error |
| source_quote 存在 | `new_setting.source_quote` 必须在正文中存在 | 记录 error |
| setting_key 唯一 | `new_setting.setting_key` 在项目中不能重复 | 记录 error |
| closing_value 公式 | `closing_value == opening_value + Σincrements - Σdecrements` | 记录 error |
| source_version_id | `foreshadowing_update.source_version_id` 不为空 | 记录 error |

### 输出状态

- `validation_status="valid"` — 全部验证通过，可执行 apply
- `validation_status="needs_human_review"` — 部分验证失败，需人工确认
- `validation_status="failed"` — 严重错误（如 DB 连接失败）

## 测试要求

### Layer 1: 验证逻辑
- [ ] old_value 与 DB 当前值匹配时通过
- [ ] old_value 不匹配时记录 error
- [ ] source_quote 在正文中存在时通过
- [ ] source_quote 不在正文中时记录 error
- [ ] setting_key 唯一时通过
- [ ] setting_key 重复时记录 error
- [ ] closing_value 公式正确时通过
- [ ] closing_value 公式错误时记录 error

### Layer 2: Prompt 渲染
- [ ] 当前角色状态正确注入
- [ ] 当前设定正确注入
- [ ] 当前活跃伏笔正确注入
- [ ] 题材规则正确注入
- [ ] 正文截断（MAX_CONTENT_LENGTH）

### Layer 3: 结果组装
- [ ] character_updates 正确解析
- [ ] new_settings 正确解析
- [ ] foreshadowing_updates 正确解析
- [ ] numerical_updates 正确解析（玄幻）
- [ ] 空结算时返回 valid

### Layer 4: DB 应用
- [ ] character_states INSERT 新快照
- [ ] setting_snapshots INSERT 新设定
- [ ] foreshadowings INSERT/UPDATE
- [ ] numerical_ledgers INSERT 新记录
- [ ] 验证 apply 不 UPDATE 旧记录

### Layer 5: 集成测试
- [ ] Mock LLM → 完整流程
- [ ] 无效 JSON → LLMResponseParseError
- [ ] 全部验证通过 → valid + apply 成功
- [ ] 部分验证失败 → needs_human_review + 不 apply

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_settlement_extractor.py -v` 全部通过
- [ ] `pytest tests/ -v` 全量通过（当前 536 passed）
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] ruff 0 errors
- [ ] 生成了 `tasks/016-settlement-extractor-DONE.md` 交接文件

## 参考实现

参考以下已有代码的结构：
- `src/songyan/agents/llm_auditor.py` — Prompt 渲染 + LLM 调用 + JSON 解析 + 结果组装
- `src/songyan/agents/revision_handler.py` — 验证逻辑 + 结果组装
- `src/songyan/db/settlement_repo.py` — ForeshadowingRepository / SettingSnapshotRepository / NumericalLedgerRepository
- `src/songyan/db/context_repo.py` — CharacterStateRepository（需新增 insert_snapshot）

### 已有相关文件路径

```
src/songyan/models/settlement.py          # StateSettlement, CharacterUpdate, NewSetting, etc.
src/songyan/models/context.py             # GenreRules
src/songyan/db/settlement_repo.py         # ForeshadowingRepository, SettingSnapshotRepository, NumericalLedgerRepository
src/songyan/db/context_repo.py            # CharacterStateRepository（需新增 insert_snapshot）
src/songyan/db/repository.py              # CharacterRepository（获取角色列表）
src/songyan/llm/client.py                 # call_llm()
src/songyan/llm/parsing.py                # parse_llm_response()
```
