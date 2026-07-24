# Task 191: Ch200 harness 准备

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 工具链准备 / harness 参数化 / dry-run 验收
> **优先级**: P0（192-194 实跑前置）
> **状态**: ✅ 完成（DONE：`tasks/191-ch200-harness-preparation-DONE.md`）
> **来源**: `tasks/V10-README.md` Task 191

---

## 任务边界

本任务只准备 Ch200 分段爬坡工具链，不启动真实 Ch101-Ch200 生成，不改变五门判定函数，不改变 CED/T9 口径。

允许修改或新增 harness 脚本、报告路径约定、参数解析、dry-run 检查、文档和测试。禁止在本任务中进行长窗口 LLM 实跑。

---

## 背景

V8/V9 的 Ch100 爬坡复用了 `scripts/run_172b_ch100_climb.py`，固定 `.tmp/task172b_<template>_ch100.db` 路径，并在段边界执行 five-gate、segment audit、metrics/T9。

V10 需要推进 Ch200，不能直接把 `--to 200` 硬塞进旧脚本。必须先确认：

- 是否复用旧脚本并参数化，还是新建 `run_v10_ch200_climb.py`；
- Ch100 起点如何接续；
- Ch125 / Ch150 / Ch175 / Ch200 checkpoint 如何落盘；
- 成本预算、wrapper marker、resume、isolate 语义是否明确；
- 外部 `DATABASE_URL` 是否会污染 harness DB；
- 终判报告路径和 `.tmp` 证据命名是否统一。

---

## 前置输入

| 前置 | 用途 |
|------|------|
| Task 189 | 提供 sci-fi Ch200 baseline/checkpoint 对照表 |
| Task 190 | 提供 xuanhuan/wuxia/urban 的 Ch100 起点准入结论 |
| `scripts/run_172b_ch100_climb.py` | V8/V9 Ch100 爬坡 harness 参考实现 |
| `scripts/five_gate_check.py` | 正式五门工具 |
| `scripts/segment_audit.py` | 正式段审计工具 |
| `scripts/run_with_timeout.ps1` | Windows 防卡 wrapper |

若 189 或 190 未完成，本任务可以先写代码/文档草案，但不得宣称 Ch200 harness 已准入真实实跑。

---

## 设计要求

### A. 路径约定

建议使用 V10 专用固定路径，避免覆盖 V8/V9 证据：

| 类型 | 建议路径 |
|------|----------|
| DB | `.tmp/task_v10_<genre>_ch200.db` |
| project info | `.tmp/task_v10_<genre>_project.json` |
| segment log | `.tmp/task_v10_<genre>_segments.jsonl` |
| five-gate | `.tmp/v10_<genre>_seg<checkpoint>_five_gate.json` |
| segment audit | `.tmp/v10_<genre>_seg<checkpoint>_audit.json` |
| metrics | `.tmp/v10_<genre>_seg<checkpoint>_metrics.md` |
| final report | `.tmp/v10_<genre>_ch200_final.json` |

旧 `.tmp/task172b_<genre>_ch100.db` 不得被覆盖；如需续跑，必须复制或明确从 Task 190 判定的 clean source 初始化新 Ch200 DB。

### B. 参数约定

harness 至少支持：

```powershell
python scripts/<ch200_harness>.py --init --genre <genre>
python scripts/<ch200_harness>.py --init-from-source --genre <genre> --source-db <clean_ch100.db> --source-project-id <project_id>
python scripts/<ch200_harness>.py --to 125 --genre <genre>
python scripts/<ch200_harness>.py --to 150 --genre <genre>
python scripts/<ch200_harness>.py --to 175 --genre <genre>
python scripts/<ch200_harness>.py --to 200 --genre <genre>
python scripts/<ch200_harness>.py --status --genre <genre>
python scripts/<ch200_harness>.py --audit --genre <genre> --up-to 150 --baseline tasks/189-scifi-ch200-baseline.json
python scripts/<ch200_harness>.py --dry-run --genre <genre>
```

`--audit` 对非 sci-fi Ch125+ checkpoint 必须显式传入 `tasks/189-scifi-ch200-baseline.json`，不得依赖 `scripts/five_gate_check.py` 的默认 baseline（默认值仍是包内 Ch100 baseline，不能作为 Ch200 对照口径）。

环境变量继续兼容：

| 变量 | 用途 |
|------|------|
| `TEMPLATE_ID` | 可作为 `--genre` fallback，但显式参数优先 |
| `RUN_ID` | run trace id |
| `CHECKPOINTER_MODE=sqlite` | 长跑持久化 |
| `SONGYAN_RUN_COST_BUDGET` | run 级预算熔断 |
| `SONGYAN_FORCE_EXIT=1` | 长跑 wrapper 场景兜底 |

### C. Ch100 source → Ch200 DB 初始化语义

Task 191 必须冻结初始化策略，避免后续 192-194 各自手工复制 DB。推荐语义：

#### C1. Task 190 verdict gate

Task 191 必须先读取 Task 190 的准入判定，再决定是否允许初始化 Ch200 DB：

| Task 190 判定 | Ch200 初始化策略 |
|---------------|------------------|
| `CONTINUE_READY` | 允许 `--init-from-source`。当前仅 urban 属于此类，可直接以 Ch100 accepted head 作为 Ch200 起点。 |
| `BLOCKED_DIRTY_SAMPLE` | 禁止直接初始化；必须先完成定点 clean 并重跑 T9=0，再把该体裁提升为可用 source。当前 wuxia 属于此类，需先清理 Ch28 省略号占位段。 |
| `REBUILD_REQUIRED` | 禁止初始化；必须恢复原始 Ch100 DB 或 clean rerun 到 Ch100 后再进入 Ch200。当前 xuanhuan 属于此类。 |
| `BLOCKED_MISSING_SOURCE` | 禁止初始化；必须补齐 DB / project_id / run_id 后重新盘点。 |

不得因为 five-gate 或 segment audit PASS 就绕过 T9=0；T9 是 V10 硬红线。

#### C2. Source / target 复制语义

| 项 | 要求 |
|----|------|
| source DB | 只能来自 Task 190 判定为 `CONTINUE_READY` 的 clean Ch100 DB，或完成 clean/rebuild 后经 Task 190 同口径复核为可用的 Ch100 DB |
| target DB | 写入 `.tmp/task_v10_<genre>_ch200.db`，不得覆盖 source DB |
| project_id | 默认保留 source project_id，除非任务书明确要求 clone；若 clone，必须记录旧/新 project_id 映射 |
| run_id | V10 Ch200 必须创建新的 run trace id，不能复用 Ch100 终判 run_id |
| chapter heads | Ch1-Ch100 accepted head 必须原样保留；Ch101 起由 Ch200 run 追加 |
| project_runs / cost | Ch200 run 成本和状态必须独立记录，不污染 Ch100 run |
| segment log | `.tmp/task_v10_<genre>_segments.jsonl` 从 Ch100 source inventory 写入初始化记录，再追加 Ch125/150/175/200 |
| source inventory | `.tmp/190_ch100_source_inventory.json` 只作本地工作副本；canonical 事实源为 `tasks/190-ch100-terminal-source-inventory-DONE.md`。若 `.tmp` inventory 缺失，dry-run 必须提示重建本地副本或要求显式传入 source 参数，不得静默读取默认库或猜测路径。 |

`--dry-run --init-from-source` 必须打印上述决策，不写 target DB。

### D. 成本与 wrapper 纪律

真实长跑必须通过 wrapper：

```powershell
powershell -File scripts/run_with_timeout.ps1 -TimeoutSec <sec> -SuccessMarkerRegex "WRAPPER_RESULT=PASS_NORMAL_EXIT|accepted.*<n>/<n>" -- python scripts/<ch200_harness>.py --to <checkpoint> --genre <genre>
```

Task 191 只需验证 wrapper 命令结构和 dry-run marker，不跑真实 Ch200。

### E. 审计集成

harness 在段边界应能生成：

1. five-gate JSON；
2. segment audit JSON；
3. metrics/T9 Markdown；
4. segment JSONL 记录；
5. human-readable summary。

审计工具的判定函数不得在本任务改动。如需扩展 I/O 或 baseline 读取路径，必须有双体裁/历史样本回归。

---

## 工作内容

1. 决定复用旧脚本还是新增 V10 Ch200 脚本，并在任务记录中说明理由。
2. 实现或规划 `--init / --init-from-source / --to / --status / --audit / --dry-run`。
3. 固定 V10 `.tmp` 路径，不覆盖 V8/V9 证据。
4. 接入 Task 189 baseline 和 Task 190 source inventory。
5. 写 dry-run 测试或最小命令验证，确认无需 LLM 即可检查路径、参数、报告目标。
6. 明确处理 Task 190 三态准入：urban 可初始化，wuxia 需 pre-clean，xuanhuan 需恢复/重建。
7. 补 README/任务文档中的使用命令。

---

## 验收判据

1. Ch200 harness 的命令、路径、参数、环境变量和报告命名全部冻结。
2. `--dry-run` 可在无 LLM 调用下输出将使用的 DB、project source、checkpoint、report paths、budget env。
3. `--init-from-source --dry-run` 明确展示 source DB、target DB、project_id 保留/clone 策略、run_id 策略、segment log 初始化策略。
4. `--status` 可读取现有 V10 Ch200 DB/project info；DB 不存在时给出明确下一步。
5. `--audit --up-to <checkpoint>` 可调用正式 five-gate / segment audit / metrics 路径，或在 dry-run 中展示将调用命令。
6. 明确禁止外部 `DATABASE_URL` 污染 harness DB；metrics/audit 临时设置后必须清理环境变量。
7. 非 sci-fi Ch200 five-gate 调用必须显式传入 Task 189 生成的 Ch200 baseline，不得使用包内默认 Ch100 baseline。
8. 不启动真实 Ch101-Ch200 生成。
9. `--init-from-source --dry-run` 必须拒绝 xuanhuan 当前 source（REBUILD_REQUIRED）和 wuxia 当前 source（BLOCKED_DIRTY_SAMPLE），并允许 urban source。
10. `.tmp/190_ch100_source_inventory.json` 缺失时，dry-run 必须给出明确下一步；不得把 `.tmp` 文件作为唯一不可替代的 canonical 输入。
11. 有聚焦测试或脚本 dry-run 证据；`git diff --check` 通过。
12. harness 或质量工具调用路径如有改动，必须执行 scifi 短窗口回归；若影响 Ch200 baseline / five-gate / segment audit 口径，还必须重放 Task 189 的 Ch125/150/175/200 baseline。
13. 产出 `tasks/191-ch200-harness-preparation-DONE.md`，并更新 `tasks/V10-README.md`。

---

## 不做

- 不生成 Ch101。
- 不修改五门判定函数。
- 不改变 T9/CED 口径。
- 不调 profile。
- 不把优秀度信号接入 harness 终判。
- 不删除或覆盖 V8/V9 `.tmp` 证据。

---

## 风险与路由

| 风险 | 路由 |
|------|------|
| 旧 harness 与 Ch200 需求耦合过深 | 新建 V10 harness，复用公共 helper，不强行兼容 |
| Ch100 source inventory 不完整 | harness 只能 dry-run，不准入真实实跑 |
| `.tmp` source inventory 在 fresh checkout 缺失 | 以 `tasks/190-ch100-terminal-source-inventory-DONE.md` 为 canonical；dry-run 提示重建本地 `.tmp` 副本或要求显式 source 参数 |
| baseline 文件格式未冻结 | 依赖 Task 189；audit 命令必须显式传入 `tasks/189-scifi-ch200-baseline.json` |
| `--baseline` 遗漏导致使用包内 Ch100 baseline | dry-run 和聚焦测试必须检查 five-gate 命令行包含 Task 189 baseline |
| source DB 复制后 run 账本混乱 | `--init-from-source` 必须新建 V10 run trace，segment log 写初始化记录 |
| wrapper marker 不可靠 | 先补 wrapper success marker 参数或文档，不启动长跑 |
| `DATABASE_URL` 污染 DB | harness 内显式忽略或覆盖，audit/metrics 后清理 |

---

## 后续依赖

Task 191 完成后，Task 192/193/194 才能写最终执行命令并启动 Ch200 分段爬坡。若 191 产出新 harness，三个体裁任务必须统一使用该 harness，不再各自手写临时脚本。
