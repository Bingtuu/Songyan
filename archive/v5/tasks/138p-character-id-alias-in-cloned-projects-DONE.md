# Task 138p：克隆/延续项目中的角色 ID Alias 断裂修复

> **类型**: Bugfix / 数据质量
> **状态**: 已完成（代码实现 + 新增单测）
> **前置**: Task 138o 已完成，Ch31-Ch50 长窗口验证通过，但在日志中发现大量 `settlement.character_id_not_found character_id=char_001` 警告。
> **依赖**: 无新增依赖，复用现有 `CharacterRepository`、`SettlementExtractor` 与项目克隆逻辑。

## 背景

在 Task 138k/138n/138o 的长窗口 rehearsal 中，为了不从 Ch1 重新生成，脚本会从源项目 `e95a1fa3` 克隆出一个新的验证项目。`_clone_characters()` 的实现会给每个角色生成新的 ID：

```python
new_id = f"char-{target_project_id[:8]}-{i + 1:03d}"
```

该函数虽然返回了 `char_001 -> new_id` 的 alias 映射，但调用方没有把它注册到 SettlementExtractor。因此 Writer 生成的正文仍使用原始角色 ID（如 `char_001`）指代主角，而 SettlementExtractor 从正文解析出 `char_001` 后，在当前项目的 `characters` 表中找不到该 ID，于是：

- 跳过 `character_updates`（`action=skip`）
- 跳过 `numerical_updates`（`action=skip_numerical`）
- 发出 `settlement.character_id_not_found` / `settlement.unknown_character_field` 警告

这导致克隆项目的 `character_states` 表长期为空，主角的 physical_state / emotional_state / relationship 等状态没有快照，降低了长窗口证据的完整性。

## 目标

消除克隆/延续项目中的 `settlement.character_id_not_found` 警告，确保 character state 和 numerical ledger 在克隆项目中正常写入。

## 验收标准

- [x] 修复后，克隆角色时自动把 `char_001` -> 新项目 ID 的 alias 注册到 SettlementExtractor。
- [x] 新增单元测试覆盖：克隆项目角色 ID 映射 + SettlementExtractor 解析 fallback。
- [x] 全量 `pytest tests/ -q` 与 `ruff check src/ tests/` 通过，无回归。
- [ ] 后续使用修复后的脚本启动一次 Ch1-Ch10（或 Ch1-Ch5）rehearsal，确认 `character_id_not_found` 警告为 0；若时间不允许，可在下次长窗口验证时顺带观察。
- [x] 更新本任务文件状态为 DONE，并同步 `docs/STATUS.md`、`tasks/V5-README.md`、`docs/INDEX.md`。

## 候选方案

### 方案 A：克隆时保留原始 character_id

修改 `_clone_characters()`，不再为克隆角色生成新 ID，而是直接复制原 `character_id`。

**优点**：改动最小，不需要修改 SettlementExtractor。

**缺点**：`characters.character_id` 是全局主键，源项目和克隆项目在同一数据库中并存时会产生主键冲突，因此不可行。

### 方案 B：克隆时建立 alias 映射（已采用）

继续使用新 ID 避免主键冲突，但在克隆完成后把 `char_001 -> new_id` 注册到 SettlementExtractor 已有的全局 alias 表。`run_136_v52_enforce_validation.py` 已使用同样机制，只需让 138k/138n 脚本也调用 `register_character_aliases()`。

**优点**：
- 不改动表结构；
- 与既有 alias 机制保持一致；
- 避免全局主键冲突。

**缺点**：
- alias 是进程级全局状态，多项目并发时可能互相污染（当前 CLI 为单项目运行，风险可控）；
- 长期应在 `characters` 表增加 `aliases` 字段（Task 094 已标注为长期方案）。

### 方案 C：SettlementExtractor 按角色名/主角身份 fallback

当 `character_id` 找不到时，尝试按角色名、主角标记或出场频率匹配到一个有效角色。

**优点**：不需要改克隆逻辑。

**缺点**：匹配逻辑容易出错（同名角色、化名等），确定性不如方案 B。

## 实际实现

采用**方案 B**：
- 新建 `src/songyan/utils/project_clone.py`，提供 `clone_characters(source_project_id, target_project_id)`；
- 该函数在克隆角色后调用 `register_character_aliases(aliases)`；
- `scripts/run_138k_long_window_rehearsal.py` 与 `scripts/run_138n_ch1_ch30_rerun.py` 删除本地 `_clone_characters()`，改为导入 `songyan.utils.project_clone.clone_characters()`。

## 实现步骤（已完成）

1. **新建公共克隆函数**
   - 文件：`src/songyan/utils/project_clone.py`
   - 函数：`async def clone_characters(source_project_id, target_project_id) -> dict[str, str]`
   - 行为：克隆角色并调用 `register_character_aliases(aliases)`。

2. **新增单元测试**
   - 文件：`tests/test_task138p_character_id_alias.py`
   - 覆盖：克隆后 alias 映射正确；SettlementExtractor 的 `_normalize_character_id()` 能正确解析；空源项目不报错。

3. **更新 rehearsal 脚本**
   - `scripts/run_138k_long_window_rehearsal.py`：删除本地 `_clone_characters()`，改为 `from songyan.utils.project_clone import clone_characters`。
   - `scripts/run_138n_ch1_ch30_rerun.py`：同上。

4. **后续可选验证**
   - 使用修复后的脚本重新跑 Ch1-Ch10（或 Ch1-Ch5），确认 `character_id_not_found` 为 0；若时间不允许，可在下次长窗口验证时顺带观察。

## 不做的事

- 不修改正常新建项目的角色 ID 生成逻辑（`char_001`、`char_002` 等保持不变）；
- 不引入新的 Agent 类型；
- 不改动 `characters` 表结构（保留 Task 094 长期方案）；
- 不修改 `SettlementExtractor` 的核心解析逻辑，仅复用已有 alias 注册机制。

## 风险与 Fallback

- **风险**：`register_character_aliases()` 使用进程级全局字典，多项目并发运行可能污染。
  - 缓解：当前 CLI 与脚本均为单项目运行；测试用例已显式清理 `_CHARACTER_ID_ALIASES`。
  - 长期 Fallback：在 `characters` 表中增加 `aliases` 字段， settlement 时按项目 scope 查询。
- **风险**：`char_001`、`char_002` 等通用 ID 顺序与源项目角色顺序不一致。
  - 当前实现假设 `_clone_characters()` 的枚举顺序与源项目一致（原脚本即如此）；若未来源项目角色顺序不稳定，应改为基于原始 ID 本身的 alias 映射。

## 参考

- 138o 报告：`archive/v5/reports/task-138o-ch31-ch50-long-window-validation-report.md`
- 克隆脚本：`scripts/run_138k_long_window_rehearsal.py`、`scripts/run_138n_ch1_ch30_rerun.py`
- Settlement 应用逻辑：`src/songyan/agents/settlement_extractor/_apply.py:438-539`
- Character 模型与仓库：`src/songyan/db/repository/character_repo.py`、`src/songyan/models/character.py`
