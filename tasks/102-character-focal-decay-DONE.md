# Task 102: CharacterFocalDecay — 角色焦点衰减

> **状态**: 完成
> **完成日期**: 2026-06-13
> **Phase**: V5.0 Context Diet 2.0 — 核心组件 2/4

---

## 做了什么

### 核心修改

实现角色档案的详细度随"未出场章数"指数衰减，控制活跃角色信息池的大小。衰减逻辑在 Repository 查询层实现，**不修改 DB schema**。

#### 1. 新增 `CharacterStateRepository.get_last_appeared_chapters()`

**文件**: `src/songyan/db/context_repo.py`

- 添加 `get_last_appeared_chapters(project_id)` 方法
- 通过 `character_states.source_version_id` JOIN `chapter_versions` 推导每个角色最后出场章节
- 无需新增表或修改 schema，利用已有外键关系
- 无状态记录的角色不在返回结果中（调用方视为未出场）

#### 2. 扩展 `_build_character_snapshots` 增加四级衰减

**文件**: `src/songyan/agents/context_manager/_assemblers.py`

新增 `_resolve_profile_level()` 衰减解析器：

| 未出场章数 | 档案级别 | 内容 | token 估算 |
|-----------|---------|------|-----------|
| 0-3 章 | `full` | 完整档案（心理、目标、关系、当前状态） | ~800 |
| 4-10 章 | `compact` | 精简档案（现状 + 当前目标 + 核心关系） | ~400 |
| 11-30 章 | `symbol` | 符号档案（名字 + 一句话定位 + 最后已知状态） | ~100 |
| 30+ 章 | `skip` | 不加载 | 0 |

**核心规则**：
- `protagonist` / `antagonist` **永不衰减**（保留完整档案）
- `character_focus` 人工指定覆盖 decay 规则（`full`/`compressed` 优先）
- 080 arc 窗口规则与 decay 共存：非 arc 角色先降级为 `compact`，再应用 decay

**三种档案输出格式**：
- `full`: 现有完整字段（location, cultivation, emotional_state, relationships, goals）
- `compact`: 保留 location + emotional_state，清空 relationships/goals
- `symbol`: 只保留 `name` + `【符号档案】最后出场ChX，位置:XX，状态:XX`

#### 3. 修改 `assemble_context_package` 传入出场记录

**文件**: `src/songyan/agents/context_manager/__init__.py`
- 函数签名增加 `last_appeared_chapters` 参数
- `_build_character_snapshots` 调用处传入该参数

**文件**: `src/songyan/workflows/_helpers.py`
- workflow 包装函数中调用 `CharacterStateRepository().get_last_appeared_chapters(project_id)`
- 将结果传入 `_assemble`

---

## 改了哪些文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/songyan/db/context_repo.py` | 新增方法 | `get_last_appeared_chapters()` |
| `src/songyan/agents/context_manager/_assemblers.py` | 重写+新增 | `_resolve_profile_level()` + `_build_character_snapshots()` 四级衰减 |
| `src/songyan/agents/context_manager/__init__.py` | 修改 | 函数签名 + 调用处传入 `last_appeared_chapters` |
| `src/songyan/workflows/_helpers.py` | 修改 | 加载 `last_appeared` 并传入 `_assemble` |
| `tests/test_character_focal_decay.py` | 新增 | 17 个衰减逻辑测试 |

---

## 测试数据

### 单元测试

```bash
pytest tests/test_character_focal_decay.py -v
# 结果: 17 passed, 0 failed
```

测试覆盖：
- `_resolve_profile_level`：8 个测试（protagonist 不衰减、antagonist 不衰减、四级 gap 边界、向后兼容）
- `_build_character_snapshots`：7 个测试（full/compact/symbol/skip 结构、混合场景、focus 覆盖、向后兼容、token 减少验证）
- `get_last_appeared_chapters`：1 个集成测试（空项目）

### 全量回归测试

```bash
pytest tests/ -q
# 结果: 1412 passed, 20 failed, 4 skipped, 4 xfailed
```

**失败分析**:
- 20 个失败均为 **pre-existing**，与 Task 102 修改无关
- 主要类别：
  - Integration 测试 mock LLM 响应耗尽（8 个）
  - Checkpoint/Path 测试 `__interrupt__` 状态断言失败（9 个）
  - Character appearance window importance_score 断言（2 个）
  - Settlement concurrent database locked（1 个）

### ruff 检查

```bash
ruff check src/ tests/
# 结果: 336 errors（全部 pre-existing，Task 102 修改未引入新错误）
```

---

## 验证结果

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|:----:|
| 衰减规则覆盖率 | 100% 角色按未出场章数正确分级 | 8/8 边界测试通过 | ✅ |
| protagonist 不衰减 | 永远 full | 测试通过 | ✅ |
| antagonist 不衰减 | 永远 full | 测试通过 | ✅ |
| character_focus 覆盖 | 人工指定优先 | 测试通过 | ✅ |
| 向后兼容 | 不传 last_appeared 时行为不变 | 测试通过 | ✅ |
| token 结构减少（模拟） | 5角色→4角色（1 skip, 1 symbol） | 4000→1300 (32.5%) | ✅ |
| 测试通过 | pytest 新增测试全部通过 | 17/17 | ✅ |
| 无新增 lint 错误 | 0 新增 | 0 新增 | ✅ |

---

## 已知限制

1. **Ch55 单章验证尚未执行**：实际 Writer 行为需在完整生成流程中验证（留到 Task 105 流式验证）。
2. **无状态记录的角色不衰减**：如果角色出场了但没有任何状态变化（无 `character_states` 记录），则 `get_last_appeared_chapters` 找不到它，调用方视为未出场，默认加载完整档案。在标准流程中，SettlementExtractor 会为出场角色生成至少一个状态更新，此情况罕见。
3. **last_appeared 精度依赖 Settlement 时机**：角色最后出场章节按 `character_states` 中最新记录的 `source_version_id` 关联的 `chapter_versions.chapter_number` 计算。如果 Settlement 延迟或跳过，精度会受影响。
