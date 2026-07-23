# Task 139h — V5.2 Ch80 revision 字数膨胀修复

## 状态
- **状态**: 代码修复完成，等待 Ch83–Ch150 后台跑完后重跑 Ch80 验证
- **负责人**: Kimi Code CLI
- **创建于**: 2026-07-01

## 背景

在 Task 139c（Ch51–Ch150 enforce 长窗口验证）中，Ch80 是唯一未能 accept 的章节：

- 初稿 `v-80-1`: 3817 字 / 目标 3200，ratio 1.19，ending_hook=0
- 修订 `rev-80-2`: 4182 字，ratio 1.31
- 修订 `rev-80-3`: 4276 字，ratio 1.34

Quality Gate 失败原因：

1. `length_ok=False`（ratio 1.34 > 1.20，length score 0.32）
2. `ending_hook=0`（但 momentum score 0.7 仍满足 `momentum_present` 阈值）

主要阻塞项是字数超标。

## 根因分析

Writer 1.1.0 使用**空行分场景**，正文中没有 `### Scene N` 场景标题。`songyan.utils.truncation.enforce_word_count` 依赖 `SCENE_PATTERN` 找到场景头才能按场景边界截断，因此返回 `no_scene_headers_found` 且**不截断**。

Writer 主入口在生成后自有硬截断兜底（`hard_truncate_at_boundary` 到 1.20x）。但 RevisionHandler 的 `_enforce_revision_word_count` 只调用 `enforce_word_count`，没有同样的兜底路径。结果：

- 初稿被 Writer 截断到约 1.19x（通过）
- Revision 修复 narrative_pacing / dialogue_distinctness 等问题时把章节写长
- `_enforce_revision_word_count` 无法截断，字数膨胀到 1.34x
- Quality Gate 因 length_ok=False 拒绝

## 修复内容

### 代码改动

**文件**: `src/songyan/agents/revision_handler/_segmented_revision.py`

在 `_enforce_revision_word_count` 的 `current > upper` 分支中，当 `enforce_word_count` 返回以下原因时，追加 `hard_truncate_at_boundary` 兜底：

- `no_scene_headers_found`
- `_disallowed_by_scene_structure`
- `_no_scenes_found`

逻辑与 Writer 一致：截断到 `target_word_count * 1.20`，并保留 `min_preserve_ratio=0.85` 的保留率守卫（保留率过低则回退原始 draft）。

### 测试改动

**文件**: `tests/test_088_revision_word_limit.py`

- 新增 `test_no_scene_headers_hard_truncated`：模拟 Writer 1.1.0 无 scene header 正文，验证 revision 超标时能被硬截断到 1.20x 以内。
- 删除旧的 `_test_single_scene_no_truncate`（下划线前缀，pytest 不运行），因其预期行为与修复目标冲突。

## 验证

```powershell
python -m pytest tests/test_088_revision_word_limit.py -v
ruff check src/ tests/
```

- `test_088_revision_word_limit.py`: 7 passed
- 相关 revision 测试（test_079_segmented_revision.py, test_revision_handler.py, test_revision_handler_patch.py, test_task138n_mandatory_reference_revision.py）: 122 passed in 14.65s
- `ruff check src/ tests/`: All checks passed
- 全量 pytest: 因后台 Ch83–Ch150 任务占用资源导致进程卡在第 14%（teardown/资源释放卡住），已按 Windows 测试进程防卡协议使用 PowerShell Job + 硬超时 wrapper 运行相关测试并通过

## 后续步骤

1. 等待 `bash-czk4qg4d`（Ch83–Ch150 enforce 续跑）完成。
2. 使用当前代码重跑 Ch80：
   ```powershell
   $env:DATABASE_URL="sqlite:///.tmp/task139b_enforce_ch1_ch50_rerun2.db"
   $env:PROJECT_ID="6dde3f9083f54725b867a6100cefc7eb"
   $env:GATE_MODE="enforce"
   $env:START_CHAPTER="80"
   $env:END_CHAPTER="80"
   python scripts/run_139c_enforce_ch51_ch150.py
   ```
3. 若 Ch80 accept，生成 Task 139d 最终验收包。
4. 若仍因 `ending_hook=0` 导致 QG 失败（虽然 Ch81 在 ending_hook=0 且 ratio=1.20 时被接受），再评估是否追加 ending_hook 强化prompt/后处理。

## 影响范围

- 仅影响 RevisionHandler 在 Writer 1.1.0 无 scene header 内容上的字数兜底行为。
- 已运行中的后台进程 `bash-czk4qg4d` 在启动时加载旧代码，不受本次改动影响；本次修复将在重跑 Ch80 时生效。
