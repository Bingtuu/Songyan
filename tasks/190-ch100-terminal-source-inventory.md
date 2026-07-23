# Task 190: Ch100 终点事实源盘点

> **阶段**: V10.1 Ch200 口径与工具
> **类型**: 只读盘点 / 事实源审计 / continuation 准入
> **优先级**: P0（决定 192-194 是续跑还是重建起点）
> **状态**: ◻ 规划中
> **来源**: `tasks/V10-README.md` Task 190

---

## 任务边界

本任务只判断 xuanhuan / wuxia / urban 三个体裁的 Ch100 终点是否可作为 Ch200 起点，不启动 Ch101，不修改 DB，不改 profile，不做修复。

若发现某个体裁的 Ch100 事实源不可复用，本任务只登记原因和建议路线；后续由对应体裁 Ch200 任务或独立后缀任务处理。

---

## 背景

V8/V9 已完成三个非 sci-fi 体裁 Ch100：

- xuanhuan Ch100：V8 172b 完成，five-gate PASS。
- wuxia Ch100：V8 172c clean rerun 完成，five-gate PASS。
- urban Ch100：V9 Task 187 完成，100/100 accepted，five-gate PASS，segment audit PASS，T9=0。

V10 要从 Ch100 推进到 Ch200，但不能默认所有历史 DB 都可直接续跑。必须先确认：

- DB 是否在工作区；
- project_id / run_id 是否明确；
- accepted head 是否是 clean 终判版本；
- T9 是否为 0；
- segment audit 是否 PASS；
- profile registry 与 DB override 是否符合当时终判口径；
- 是否存在诊断 DB、修复前 DB、重复副本混淆风险。

---

## 盘点对象

| 体裁 | 历史入口 | 预期事实源 |
|------|----------|------------|
| xuanhuan | `archive/v8/tasks/172b-xuanhuan-ch100-climb.md`、`archive/v8/reports/172b-xuanhuan-ch100-climb.md` | `.tmp/task172b_xuanhuan_ch100.db` 或归档报告登记 DB |
| wuxia | `archive/v8/tasks/172c-wuxia-ch100-clean-rerun-DONE.md`、`archive/v8/reports/172c-wuxia-ch100-climb.md` | `.tmp/task172b_wuxia_ch100.db` 或归档报告登记 DB |
| urban | `archive/v9/187-urban-ch100-climb-execution-DONE.md`、`archive/v9/reports/187-urban-ch100-climb.md` | `.tmp/task172b_urban_ch100.db` |

实际路径以盘点结果为准，不得根据文件名猜测即判定可续跑。

---

## 工作内容

### A. 文件与元信息盘点

对每个体裁记录：

| 字段 | 说明 |
|------|------|
| db_path | 实际 DB 路径 |
| project_id | 项目 ID |
| run_id | 终判 run ID |
| template_id / genre | 体裁 |
| accepted_count | accepted 章节数 |
| accepted_range | 是否覆盖 Ch1-Ch100 |
| latest_clean_marker | 是否有 deterministic clean / precision fix 后版本 |
| profile_source | registry / DB override / effective |
| final_report | 对应 DONE / report / `.tmp` 文件 |

### B. 只读审计

对每个候选 DB 执行只读审计：

```powershell
python scripts/five_gate_check.py --genre <genre> --db <db> --project-id <project_id> --up-to 100 --format json
python scripts/segment_audit.py --db <db> --project-id <project_id> --up-to 100 --format json
```

T9/metrics 复算：

```powershell
$env:DATABASE_URL = "sqlite:///<db>"
songyan metrics --project-id <project_id> --chapters 1-100 -o .tmp/190_<genre>_ch100_metrics.md
Remove-Item Env:\DATABASE_URL
```

profile effective 值也必须绑定目标 DB 查询，不能在清理 `DATABASE_URL` 后读默认库：

```powershell
$env:DATABASE_URL = "sqlite:///<db>"
songyan profile show --genre <genre> --json > .tmp/190_<genre>_profile_view.json
songyan profile diff --genre <genre> --json > .tmp/190_<genre>_profile_diff.json
Remove-Item Env:\DATABASE_URL
```

如担心 CLI 会迁移或写库，可直接用只读 SQLite 查询 `genre_runtime_profiles` 并与 registry 记录对照；无论使用哪种方式，必须在任务记录中写明 DB 绑定方式。全程只读，不写 override。

### C. 准入判定

每个体裁输出一种结论：

| 判定 | 含义 |
|------|------|
| `CONTINUE_READY` | 可作为 Ch200 起点；Task 192/193/194 可从 Ch101 开始 |
| `REBUILD_REQUIRED` | 不可续跑，需 clean rerun 到 Ch100 或恢复正确 DB |
| `BLOCKED_MISSING_SOURCE` | 缺少 DB / project_id / run_id，无法判定 |
| `BLOCKED_DIRTY_SAMPLE` | 只有诊断 DB 或修复前样本，不可作终判起点 |

---

## 产物

| 文件 | 内容 |
|------|------|
| `.tmp/190_ch100_source_inventory.json` | 三体裁统一盘点表与准入结论 |
| `.tmp/190_<genre>_ch100_five_gate.json` | 每体裁 Ch100 五门复算 |
| `.tmp/190_<genre>_ch100_segment_audit.json` | 每体裁 Ch100 段审计 |
| `.tmp/190_<genre>_ch100_metrics.md` | 每体裁 T9 / metrics 报告 |
| `.tmp/190_<genre>_profile_view.json` | 目标 DB 下 registry / DB override / effective profile 视图 |
| `.tmp/190_<genre>_profile_diff.json` | 目标 DB 下 DB override 差异 |
| `tasks/190-ch100-terminal-source-inventory-DONE.md` | 总结论与后续任务输入 |

---

## 验收判据

1. xuanhuan / wuxia / urban 三个体裁均有明确的准入结论。
2. 每个 `CONTINUE_READY` 体裁必须满足：100/100 accepted、gap=0、five-gate PASS、segment audit PASS、T9=0。
3. 每个不可续跑体裁必须说明原因，并给出后续路线：恢复 DB、重建 Ch100、或转诊断。
4. 盘点全程只读，不调用 `init_schema()`，不写 profile override，不生成新章节。
5. 输出 JSON 清单可被 Task 191/192/193/194 直接引用。
6. profile view/diff 必须明确绑定对应候选 DB；不得使用默认 `DATABASE_URL` 结果替代。
7. 更新 `tasks/V10-README.md` 的 Task 190 状态和后续依赖说明。

---

## 不做

- 不启动 Ch101。
- 不修正文。
- 不做 deterministic clean。
- 不调整 `GenreRuntimeProfile`。
- 不改变 harness 固定路径。
- 不把缺失 DB 的体裁临时排除出 V10。

---

## 风险与路由

| 风险 | 路由 |
|------|------|
| 同一体裁存在多个 Ch100 DB | 以 DONE 文档登记的终判 DB 为准；无法确认则 `BLOCKED_MISSING_SOURCE` |
| T9 复算与历史报告不一致 | 冻结 DB，查 accepted head 是否为 clean 版本；不得解释性豁免 |
| profile effective 值与历史口径不一致 | 先确认 profile 查询绑定了目标 DB；确认后登记差异，交后续任务判断是否需 registry/DB override 修复 |
| profile CLI 读到默认库 | 该结果作废；用目标 DB 环境变量或只读 SQL 重跑 |
| `.tmp` 证据缺失但报告完整 | 不直接判 ready；先确认 DB/project_id/run_id 可重放 |

---

## 后续依赖

Task 191 的 harness 输入、Task 192/193/194 的起点策略，均以本任务输出的 `CONTINUE_READY` / `REBUILD_REQUIRED` 判定为准。
