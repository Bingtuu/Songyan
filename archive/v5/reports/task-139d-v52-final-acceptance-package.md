# Task 139d — V5.2 最终验收包

> **状态**: 已验收
> **关联任务**: 139a / 139b / 139c / 139d / 139e / 139f / 139g / 139h / 140
> **目标**: 默认启用 `enforce` gate_mode，获得 Ch1-Ch150 enforce 模式完整证据，交付 V5.2 收口文档。

---

## 1. 验收结论

| 项 | 结果 |
|----|------|
| CLI 默认 gate_mode | `enforce`（已切换） |
| Ch1-Ch50 enforce 验证 | `run-813a9ed7` 50/50 accept，无 AutoHalt |
| Ch51-Ch82 enforce 验证 | `run-c68a1384` Ch51-Ch79 / Ch81-Ch82 accept；Ch80 因 revision 后字数膨胀 + ending_hook=0 失败 |
| Ch80 修复后重跑 | `run-7b45c17d` accept，生成 `v-80-12-e017e643`，4094 字，overall=0.9281 |
| Ch83-Ch150 enforce 验证 | `run-df933dbf` 68/68 accept，无 AutoHalt |
| Ch1-Ch150 最终统计 | **150/150 accept**，`failed=[]`，无 AutoHalt |
| continuity 最终读数 | health=8.5，orphaned_settings=20，forgotten_items=3，state_mismatches=0，overdue_foreshadowings=0 |
| 全量 pytest | `2036 passed, 1 xfailed, 2 warnings`（`bash-yydyhyu5` PowerShell wrapper） |
| ruff | `ruff check src/ tests/` 通过 |

**最终结论**: V5.2 通过。CLI 默认 gate_mode 已成功切换为 `enforce`，并在跨项目 Ch1-Ch150 验证中获得 150/150 accept 的完整证据，无 AutoHalt、无 gate 误触发。

---

## 2. 验证运行详情

### 2.1 运行组合

| 范围 | Run ID | 状态 | 备注 |
|------|--------|------|------|
| Ch1-Ch50 | `run-813a9ed7` | completed | 50/50 accept |
| Ch51-Ch82 | `run-c68a1384` | partial | Ch83 为续跑起点；Ch80 失败 |
| Ch80 修复后重跑 | `run-7b45c17d` | completed | `v-80-12-e017e643` accepted |
| Ch83-Ch150 | `run-df933dbf` | completed | 68/68 accept |

验证数据库：`.tmp/task139b_enforce_ch1_ch50_rerun2.db`  
项目 ID：`6dde3f9083f54725b867a6100cefc7eb`

### 2.2 最终指标提取命令

```powershell
python scripts/extract_139d_final_metrics.py .tmp/task139b_enforce_ch1_ch50_rerun2.db 6dde3f9083f54725b867a6100cefc7eb run-df933dbf
```

关键输出：

```json
{
  "project_id": "6dde3f9083f54725b867a6100cefc7eb",
  "run_id": "run-df933dbf",
  "total_chapters": 150,
  "accepted_count": 150,
  "not_accepted": [],
  "failed_chapters": [],
  "run_status": "completed",
  "continuity_report": {
    "checked_up_to_chapter": 150,
    "overall_health_score": 8.5,
    "orphaned_settings": 20,
    "forgotten_items": 3,
    "state_mismatches": 0,
    "overdue_foreshadowings": 0
  }
}
```

> 注：`orphaned_settings` 与 `forgotten_items` 为终章附近正常衰减项，均无 P1 critical 断裂；`state_mismatches=0` 与 `overdue_foreshadowings=0` 说明状态一致性与伏笔回收无异常。

---

## 3. 变更摘要

### 3.1 默认 gate_mode 切换为 enforce（Task 139d）

- `src/songyan/cli/commands/run.py`: `--gate-mode` 默认值从 `"observe"` 改为 `"enforce"`。
- `cli_help.txt`: 帮助文本同步更新。
- `tests/test_130_gate_mode.py`: 23 项 gate 测试同步，全部通过。

### 3.2 enforce 门禁配置最终审计（Task 139a）

- 复核 `GateConfig` 阈值与 `_gates.py` 触发逻辑。
- 在 `run-813a9ed7` 历史数据上离线模拟：Ch1-Ch50 零 gate 触发。

### 3.3 enforce 模式 Ch1-Ch50 验证（Task 139b）

- `run-813a9ed7`: 50/50 accept，`failed=[]`，无 AutoHalt。
- 证明默认 enforce 在项目开局期不会误触发。

### 3.4 enforce 模式 Ch51-Ch150 长窗口验证（Task 139c）

- `run-c68a1384`: Ch51-Ch82 中 Ch80 因 revision 字数膨胀失败，其余 accept。
- `run-7b45c17d`: Ch80 修复后重跑成功 accept。
- `run-df933dbf`: Ch83-Ch150 68/68 accept，无 AutoHalt。

### 3.5 rewrite_node / revision_router mandatory reference 修复（Task 139e/139f）

- 修复 rewrite 节点丢失 mandatory reference 约束的问题。
- 修复 revision_router 回滚路径绕过 mandatory reference 检测的问题。

### 3.6 settlement LLM 超时修复（Task 139g）

- `src/songyan/llm/client.py`: `call_llm` / `get_llm` / `_get_llm_cached` 新增 `timeout` 参数；累计超时改为 `timeout * max_retries + 30`。
- `src/songyan/agents/settlement_extractor/__init__.py`: settlement 调用使用 `timeout=120, max_retries=2`，避免 210s 熔断。

### 3.7 Ch80 revision 字数膨胀修复（Task 139h）

- `src/songyan/agents/revision_handler/_segmented_revision.py`: 当 `enforce_word_count` 因无 scene header 失败时，使用 `hard_truncate_at_boundary` 兜底到 1.20x。
- 新增 `tests/test_088_revision_word_limit.py::test_no_scene_headers_hard_truncated`。

---

## 4. 测试与 lint

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 相关 revision 测试 | `pytest tests/test_088_revision_word_limit.py tests/test_079_segmented_revision.py tests/test_revision_handler.py tests/test_revision_handler_patch.py tests/test_task138n_mandatory_reference_revision.py -q` | 122 passed |
| lint | `ruff check src/ tests/` | 通过 |
| 全量 pytest | `pytest tests/ -q` | 2036 passed, 1 xfailed, 2 warnings |

---

## 5. 风险与遗留

| 风险 | 状态 |
|------|------|
| enforce 开局期误触发 | 已解除：139b Ch1-Ch50 零 gate 触发 |
| 长窗口 budget 压力导致 ContextEmergency | 已解除：Ch1-Ch150 全程未出现 context emergency |
| Ch80 修复后仍无法 accept | 已解除：`run-7b45c17d` accept，overall=0.9281 |
| V5.2 遗留任务状态 | 已移交 Task 140 执行清理 |

---

## 6. 下一步

1. **Task 140：V5.2 遗留任务状态清理**：将 Task 137/138g 等已覆盖遗留项标记为关闭/已覆盖，归档历史任务状态，同步 `tasks/V5-README.md`、`docs/INDEX.md`、`docs/STATUS.md`。
2. **V6/V7 规划预研**：叙事骨架 MVP、长篇质量度量、可靠长跑底盘，见 `docs/v6-plan.md` 与 `docs/v7-vision.md`。
3. **持续回归**：后续改动继续执行 `pytest tests/ -q` + `ruff check src/ tests/`。
