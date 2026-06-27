# Task 137: 设定回收闭环与 tracking 刷新机制（V5.2）

> **类型**: 底层缺陷修复 / 实跑验证  
> **日期**: 2026-06-27  
> **前置**: Task 135、Task 136  
> **目标**: 让“设定回收”从“提示 LLM”变成可验证、可自动闭环的机制，降低 enforce 模式下 `orphaned_settings` 的虚假累积，使 Ch12–Ch15 orphan 增长速率降至 Ch9–Ch12 的一半以下。

---

## 1. 背景

Task 136 enforce 模式 Ch1–Ch20 实跑显示：

- Task 133/134 目标已达成（多场景 100%、Settlement 记录率 100%）。
- Task 135 的 health floor 指标通过，但 **orphan 增长速率未减半**，Ch12–Ch15 反而高于 Ch9–Ch12（4.0 / 章 vs 2.667 / 章）。
- 主要增长类别为 `background`（Ch15 时 28/33 个）。

根因分析：

1. **已有设定被正文提及后，不会刷新 `last_mentioned_chapter`**。`SettlementExtractor` 在提取 `new_settings` 时过滤掉已存在的 `setting_key`，导致 `apply_settlement._update_continuity_tracking` 中的 `update_last_mentioned` 分支无法执行。
2. **`setting_tracking` 与 `setting_snapshots` 生命周期不同步**。`SettingEvaporator` 只 archive `setting_snapshots`，`setting_tracking.status` 仍保持 `active`，继续被 ContinuityAuditor 计为 orphan。
3. **`SettingEvaporator` 时间衰减过慢**。固定分母 50 章导致 Ch20 之前 background 设定几乎不可能被蒸发。
4. **已回收的 continuity_auditor human_mark 不会自动 resolve**，Writer 可能反复看到同一批“必须回收”的设定。

---

## 2. 目标

建立“检测回收/呼应 → 刷新 tracking → 自动 resolve human_mark → 减少虚假 orphan”的闭环。

---

## 3. 具体改动

### 3.1 正文 setting 提及扫描（不依赖 LLM）

- **文件**: `src/songyan/agents/settlement_extractor/_apply.py`
- **新增**: `_detect_setting_references(content: str, active_settings: list[dict]) -> dict[str, str]`
- 使用 `setting_name` 对正文做子串匹配；若命中项后紧跟另一个中文字符（如「天剑宗」中的「天剑」），则视为更长词的一部分并跳过。
- 在 `apply_settlement` 事务中，对命中的 setting 调用 `setting_tracking_repo.update_last_mentioned(..., chapter_number)`。

### 3.2 SettlementExtractor 显式输出 `recycled_settings`

- **文件**: `prompts/cards/settlement_extractor/1.0.2.yaml`
- **新增 JSON 字段**:

```json
{
  "recycled_settings": ["xuanhuan.lin.xxx"]
}
```

- 与 3.1 的扫描结果合并，作为刷新 `last_mentioned` 和 resolve human_mark 的证据。

### 3.3 自动 resolve 已回收的 continuity_auditor human_mark

- **文件**: `src/songyan/agents/settlement_extractor/_apply.py`
- 在 apply 事务中，若 `human_mark.source == "continuity_auditor"` 且 `target_key` 被检测到在正文中出现，则调用 `HumanMarkRepository.resolve(mark_id, chapter_number)`。

### 3.4 `setting_tracking` 生命周期与 snapshots 同步

- **文件**: `src/songyan/db/settlement_repo.py`
- 当 `SettingSnapshotRepository.archive_stale()` / `archive_by_confidence()` 修改 `setting_snapshots.lifecycle_status` 时，同步将对应 `setting_tracking.status` 置为 `dormant` / `archived`（保留记录，但退出 orphan 统计）。

### 3.5 按 category 调整 SettingEvaporator 时间衰减

- **文件**: `src/songyan/agents/setting_evaporator/__init__.py`
- 将固定分母 50 改为按 category：
  - `background`: 25
  - `technical`: 30
  - `historical`: 20
  - `recurring`: 80
  - `critical`: 100

### 3.6 CreativeDirector 回收列表按 orphan 优先级排序

- **文件**: `src/songyan/agents/creative_director/__init__.py`
- `_load_active_settings_to_recycle` 新增 `min_silent_chapters=2` 过滤，仅展示已沉寂至少 2 章的 active 设定；同类别内按 `last_mentioned_chapter` 升序排列，让最久未提及的设定优先被 Writer 看到。

---

## 4. 验收标准

### 4.1 代码与测试

- [x] `ruff check src/ tests/` 通过。
- [x] 全量 `pytest tests/` 通过，且新增 Task 137 相关测试：
  - [x] 正文提及 setting 后 `setting_tracking.last_mentioned_chapter` 被刷新。
  - [x] `recycled_settings` 提取字段被正确解析并入库。
  - [x] continuity_auditor human_mark 在目标 setting 被回收后 `resolved_at` 更新。
  - [x] `setting_snapshots` archive 后对应 `setting_tracking.status` 同步变更。
  - [x] SettingEvaporator 按 category 使用不同衰减分母。

### 4.2 实跑验证

- [ ] 在 enforce 模式下重新实跑 Ch1–Ch20（可复用 Task 136 脚本）。
- [ ] Ch12–Ch15 orphan 平均增长/章 ≤ Ch9–Ch12 平均增长/章的一半。
- [ ] Ch15 `orphaned_settings` 中 `background` 数量不再单调上升（相对 Ch12 减少或持平）。
- [ ] Ch12/Ch15 health score ≥ 3.0。
- [ ] Multi-scene ratio ≥ 90%，Settlement 记录率 ≥ 95%。

### 4.3 文档

- [ ] 更新 `docs/STATUS.md`、`tasks/V5-README.md`、`README.md`、`docs/INDEX.md`。
- [ ] 将本文件归档为 `tasks/137-setting-recycling-closed-loop-DONE.md`。

---

## 5. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| 正文扫描误匹配导致错误刷新 | 让本应为 orphan 的设定被“伪回收” | 要求匹配词长度 ≥3 且为完整词边界；结合 LLM 显式 `recycled_settings` 交叉验证 |
| SettingEvaporator 分母变小导致重要设定被 archive | 关键伏笔丢失 | critical/recurring 仍使用较大分母；archive 仅改 `status`，记录保留，可随时恢复 |
| human_mark 自动 resolve 后，下章又变 orphan | resolve 条件过宽 | 要求 setting 被提及且为“有意义的剧情参与”，由 source_quote 过滤短/无意义匹配 |

---

## 6. 依赖关系

```
Task 135 设定回收与 continuity health 治理 ──┐
Task 136 V5.2 enforce Ch1–Ch20 验证 ──────────┼──► Task 137 设定回收闭环与 tracking 刷新机制
```

---

## 7. 交付物

- `tasks/137-setting-recycling-closed-loop-DONE.md`
- `src/songyan/agents/settlement_extractor/_apply.py` 改动
- `prompts/cards/settlement_extractor/1.0.2.yaml` 改动
- `src/songyan/db/lifecycle_cleaners.py` / `src/songyan/agents/setting_evaporator/__init__.py` 改动
- `src/songyan/agents/creative_director/__init__.py` 改动
- 新增/补强测试文件
- `docs/reports/task-137-v52-enforce-ch1-ch20-rerun-report.md`（实跑后生成）
