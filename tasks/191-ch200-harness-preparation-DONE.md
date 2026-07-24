# Task 191: Ch200 harness 准备 — DONE

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 工具链准备 / harness 参数化 / dry-run 验收
> **优先级**: P0（192-194 实跑前置）
> **状态**: ✅ 完成
> **日期**: 2026-07-24

---

## 任务边界

本任务只准备 Ch200 分段爬坡工具链，不启动真实 Ch101-Ch200 生成，不改变五门判定函数，不改变 CED/T9 口径。

---

## 产出

| 文件 | 内容 |
|------|------|
| `scripts/run_v10_ch200_climb.py` | V10 Ch200 harness 控制面：路径、准入、dry-run/status/audit/init-from-source/to |
| `tests/test_191_ch200_harness.py` | Task 191 聚焦测试 |
| `tasks/191-ch200-harness-preparation.md` | Task 191 任务书 |
| `tasks/191-ch200-harness-preparation-DONE.md` | 本完成报告 |

---

## 关键设计冻结

### 1. V10 专用路径

| 类型 | 路径 |
|------|------|
| DB | `.tmp/task_v10_<genre>_ch200.db` |
| project info | `.tmp/task_v10_<genre>_project.json` |
| segment log | `.tmp/task_v10_<genre>_segments.jsonl` |
| five-gate | `.tmp/v10_<genre>_seg<checkpoint>_five_gate.json` |
| segment audit | `.tmp/v10_<genre>_seg<checkpoint>_audit.json` |
| metrics | `.tmp/v10_<genre>_seg<checkpoint>_metrics.md` |
| final report | `.tmp/v10_<genre>_ch200_final.json` |

旧 `.tmp/task172b_<genre>_ch100.db` 不会被覆盖；`--init-from-source` 只复制 source DB 到 V10 目标路径。复制使用 SQLite backup API 生成一致快照，并在目标 DB 内创建新的 V10 `project_runs` 记录，避免复用 Ch100 run_id。

### 2. Task 190 三态准入

| 体裁 | Task 190 判定 | Task 191 行为 |
|------|---------------|---------------|
| xuanhuan | `REBUILD_REQUIRED` | 当前 source 禁止初始化；必须恢复/重建 Ch100 |
| wuxia | `BLOCKED_DIRTY_SAMPLE` | 当前 source 禁止初始化；必须先 Ch28 clean + T9=0 |
| urban | `CONTINUE_READY` | 允许 `--init-from-source` |

dry-run 已验证：urban allowed=true；wuxia/xuanhuan allowed=false。

`--init-from-source` 复制前还会只读校验 source DB：

- source DB / project_id 必须匹配 Task 190 inventory；
- `projects.genre_id` 必须等于 `--genre`；
- accepted head 必须完整覆盖 Ch1-Ch100 且 accepted version 可关联；
- T9 meta/artifact、重复段落、timeline 必须为 0。

### 3. Ch200 baseline 强绑定

非 sci-fi Ch125+ five-gate 命令必须显式传入：

```powershell
--baseline tasks/189-scifi-ch200-baseline.json
```

dry-run audit 会输出 five-gate 命令并包含该 baseline，避免落回包内 Ch100 baseline。

### 4. `.tmp` inventory 语义

`.tmp/190_ch100_source_inventory.json` 只作为本地工作副本。canonical 事实源为：

```text
tasks/190-ch100-terminal-source-inventory-DONE.md
```

当 `.tmp` inventory 缺失时，dry-run 会提示重建本地副本或显式传入 source 参数，不静默猜测路径。

---

## 命令能力

```powershell
python scripts/run_v10_ch200_climb.py --init --genre urban --dry-run
python scripts/run_v10_ch200_climb.py --init-from-source --genre urban --dry-run
python scripts/run_v10_ch200_climb.py --status --genre urban
python scripts/run_v10_ch200_climb.py --audit --genre urban --up-to 150 --dry-run
python scripts/run_v10_ch200_climb.py --to 125 --genre urban --dry-run
```

`--to` 的真实执行路径已接入 `run_project_pipeline(..., run_id=<v10_run_id>)`，但 Task 191 验收只跑 dry-run，不启动 Ch101。

---

## 验证证据

### 聚焦测试

```powershell
python -m pytest tests/test_191_ch200_harness.py -q
```

结果：`10 passed`。

覆盖点：

- `--init-from-source --dry-run` 应用 Task 190 verdict gate；
- urban 可初始化，wuxia/xuanhuan 被拒；
- 实际 init-from-source 只复制通过 clean Ch100 校验的临时 SQLite DB，并写 V10 metadata / V10 project_runs / segment init log；
- 非 Ch100 source DB 会被拒绝；
- 与 Task 190 inventory 不匹配的 source DB 会被拒绝；
- source project `genre_id` 与 `--genre` 不一致会被拒绝；
- T9 meta/artifact、重复段落或 timeline 不干净的 source 会被拒绝；
- `--audit --dry-run` five-gate 命令包含 Task 189 baseline；
- 真实 `--audit` 缺 project_id 时会在 harness 层早失败；
- `.tmp` inventory 缺失时报告 canonical DONE 和下一步。

### 相关工具回归

```powershell
python -m pytest tests/test_191_ch200_harness.py tests/test_182_five_gate_tools.py -q
ruff check scripts/run_v10_ch200_climb.py tests/test_191_ch200_harness.py
ruff check src/ tests/ scripts/run_v10_ch200_climb.py
git diff --check
```

结果：

- 聚焦 + 工具回归：`22 passed`
- ruff：`All checks passed!`
- `git diff --check`：通过

### 全量回归

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec 2400 -- python -m pytest tests/ -q
```

结果：`2993 passed, 2 skipped, 1 xfailed, 7 warnings`，`WRAPPER_RESULT=PASS_NORMAL_EXIT`。

---

## 未做

- 未启动 Ch101。
- 未进行非 sci-fi Ch200 长跑。
- 未修改 five-gate / segment audit / CED / T9 判定函数。
- 未执行 xuanhuan 重建或 wuxia Ch28 clean。

---

## 后续依赖

- Task 192：xuanhuan 必须先恢复或重建 clean Ch100 source。
- Task 193：wuxia 必须先 Ch28 clean，并重跑 T9=0 后再初始化 Ch200 DB。
- Task 194：urban 可使用本 harness 从 Ch100 source 初始化 V10 Ch200 DB，再按 Ch125/150/175/200 分段推进。
