# Task 149: 录入侧降级（超额 critical 转候选，非硬丢弃）— DONE

> **Phase**: V6 阶段 B（末端治理）
> **状态**: ✅ 完成
> **完成日期**: 2026-07-02
> **关联文档**: `archive/v6/tasks/149-input-side-demotion.md`、`tasks/V6-README.md`、`docs/STATUS.md`

---

## 完成内容

### 149a — 数据模型 + 仓储支持候选态

- `setting_tracking.status` 已支持新值 `candidate`。
  - 表结构本身使用 `TEXT DEFAULT 'active'`，无 CHECK 约束，新增 `candidate` 无需迁移变更。
- `SettingTrackingRepository.create(..., status='active')` 新增 `status` 参数，可显式传入 `'candidate'`。
- 新增 `SettingTrackingRepository.promote_to_active(tracking_id, chapter, source_version_id)`：
  - 将 `status` 从 `candidate` 改回 `active`；
  - 更新 `last_mentioned_chapter` 为回升章号；
  - 更新 `source_version_id` 为回升版本，保持可追溯。
- **口径守约**：
  - `find_orphaned` 现有 SQL 硬编码 `status = 'active'`，`candidate` 天然排除，未新增过滤。
  - `new_settings_by_chapter` 无 status 过滤，`candidate` 仍计入 T7 写入侧。

### 149b — 录入路由与回升触发

- 新增 `src/songyan/workflows/_input_side_governance.py`：
  - `demote_overflow_new_settings(..., critical_cap=3)`：
    - settlement 后执行，查询本章新登记且 `category='critical'` 的 `active` 设定；
    - 保留前 `critical_cap` 条，其余降级为 `candidate`；
    - 选择优先级：`source_quote` 非空者优先，同优先级保持 settlement 原始顺序。
  - `promote_candidate_settings_after_settlement(...)`：
    - 汇总本章 settlement 全部文本证据（new_settings、character_updates、foreshadowing_updates、hooks、open_threads）；
    - 对项目下所有 `candidate` 设定，按 `setting_key` / `setting_name` / `description` 先精确匹配、再子串匹配；
    - 命中者调用 `promote_to_active` 回升，并写回当前章/版本。
- 在 `src/songyan/workflows/_nodes.py` settlement 后处理第 7 步接入：
  - 位于 `update_plot_threads_after_settlement` 之后；
  - 非阻塞，捕获 `SongyanError` / `RuntimeError` / `OSError` / `ConnectionError` / `sqlite3.Error`，失败仅记录 warning，不中断 run。

---

## 文件变更

| 文件 | 变更 |
|------|------|
| `src/songyan/db/continuity_repo.py` | `create` 支持 `status` 参数；新增 `promote_to_active` |
| `src/songyan/workflows/_input_side_governance.py` | 新增：降级 + 回升服务 |
| `src/songyan/workflows/_nodes.py` | settlement_extractor_node 第 7 步接入两个新函数 |
| `tests/test_149_input_side_demotion.py` | 新增 8 个单测 |
| `archive/v6/tasks/149-input-side-demotion-DONE.md` | 本文件 |
| `tasks/V6-README.md` | Task 149 状态改为 ✅ 完成 |
| `docs/STATUS.md` | 更新当前阶段与下一步规划 |

---

## 测试

```powershell
python -m pytest tests/test_149_input_side_demotion.py -v
```

结果：

```
8 passed in 2.45s
```

覆盖：

- 候选写入且默认不进 orphan 分母
- `promote_to_active` 更新 status / last_mentioned_chapter / source_version_id
- 5 条 critical / cap=3 超额降级，证据完整度优先
- cap 内（2 条 / cap=3）不降级
- `new_settings_by_chapter` 仍统计 candidate critical（T7 守约）
- 候选设定在后续章证据命中后回升为 active
- 无证据时不误回升
- 无骨架项目同样工作

```powershell
ruff check src/ tests/
```

结果：`All checks passed!`

---

## 阈值决定

- `critical_cap = 3`（首版）。
- 依据：`archive/v6/tasks/149-input-side-demotion.md` 阈值初版规定；后续在 Layer 3 用 138k/138n 数据校准，若复算发现被降级 critical 占同窗口新增 critical 总数超过 15%（T6c 子句），再上调 cap 或回调产生侧约束。

## T7 口径决定

- `new_settings_by_chapter` / `collect_new_critical_rate` **不**排除 `candidate`。
- T7 = 写入侧全部 critical（含已被降级的 `candidate`），避免用"降级"粉饰产生速率。
- orphan 分母仅统计 `status = 'active'`，`candidate` 天然排除。
- T6c 归因时单独看"被降级为 candidate 的 critical 数 ≤ 同窗口新增 critical 总数的 15%"。

---

## 约束遵守

- 未修改 `SettlementExtractor` 证据校验规则。
- 未新增 LLM 调用或 Agent。
- 未在 `setting_tracking.status` 加 CHECK 约束。
- 所有函数带类型标注，使用 structlog 日志。
- 无骨架/无大纲项目可回退旧行为（候选机制不依赖 PlotThread / StoryOutline）。

---

## 后续工作

- Layer 3 复算：用 `.tmp/task138k_ch1_ch30_rehearsal_20260629.db` 验证 orphan 斜率下降且被降级 critical ≤ 15%，并入 `docs/reports/`。
- 进入 Task 150：`_infer_setting_category` 收紧（双命中 + 去硬编码主角名）。

---

## 复审修复（2026-07-02，阶段 B 交付复审）

复审发现**同章 demote→promote 相互抵消**的 P1 阻断缺陷并修复：

- **#1（阻断）同章降级被当章回升抵消**——`_nodes.py` settlement 后处理按「先 `demote_overflow_new_settings` 再 `promote_candidate_settings_after_settlement`」顺序、**用同一个 settlement 对象**执行。被降级的恰是本章 new_setting，其 `setting_name`/`description` 必然出现在本章 promote 证据里 → 当章立即回升，降级归零。复现脚本证实：5 条 critical、cap=3、降级 2 条后当章 promote 全部回升，最终 candidate=0，Task 149 目标在真实管线里完全失效（此前单测把 demote/promote 分开测，未覆盖组合）。
  - **修复**：`promote_candidate_settings_after_settlement` 只回升**往期**遗留候选（`introduced_in_chapter < chapter_number`），本章刚降级的候选不参与当章回升。
  - **回归测试**：`TestSameChapterDemotePromoteInteraction`（本章降级不被当章回升 + 往期候选仍可回升）2 个新用例。
- **#4（清理）证据函数重名分叉**——本模块原 `_settlement_evidence_text` 与 `_thread_economy._settlement_evidence_text` **同名但口径不同**（前者含 `source_quote`）。已改名为 `_promotion_evidence_text` 并加注释说明差异，避免后续误用。
- 验证：`pytest tests/test_149_input_side_demotion.py`（10 passed）+ 149-152 全部（含新用例）；权威单进程全量 `pytest tests/ -q` → **2144 passed, 2 skipped, 1 xfailed**（exit 0，无回归）；`ruff check` 改动文件通过。另见 152-DONE 复审段 #5（settlement 后处理性能回归修复）。
