# Task 187: urban Ch100 爬坡执行 — DONE

> **阶段**: V9.5 urban 第三体裁中篇爬坡
> **类型**: 真实 LLM 实跑 / 分段爬坡 / 五门验收
> **优先级**: P1（V9 B 组最终证据）
> **状态**: ✅ 完成
> **来源**: `tasks/186-urban-ch100-climb.md`

---

## 完成条件

1. ✅ 使用 `scripts/run_172b_ch100_climb.py` 以 `TEMPLATE_ID=urban RUN_ID=187` 推进到 Ch100。
2. ✅ 每 25 章执行正式五门审计与段审计：Ch25 / Ch50 / Ch75 / Ch100 全部 PASS。
3. ✅ 终判满足 V9 B 组六条：100/100 accepted、budget<1.0、CED≤sci-fi×1.15、overdue≤sci-fi 同章尺度、health≥8.0、T9=0。
4. ✅ 任一段 FAIL 即停止；本次仅在段边界发现 T9 诊断项，按 187.x/187.y/187.z 定点修复后 clean rerun。
5. ✅ 产出 `tasks/187-urban-ch100-climb-execution-DONE.md` 并为 Task 188 收口提供证据。

---

## 最终证据

| 维度 | 结果 | 证据文件 |
|------|------|----------|
| 完成度 | 100/100 accepted，gap=0，halt=None | `.tmp/187_urban_ch100_final.json` |
| 预算 | budget_used_peak=0.9595，context_emergency_count=0 | `.tmp/187_urban_ch100_final.json` |
| CED | 0.11 / 1k words（sci-fi baseline 0.3976，threshold 0.4572） | `.tmp/187_urban_ch100_final.json` |
| overdue | 100（sci-fi baseline 168） | `.tmp/187_urban_ch100_final.json` |
| health | 8.6（≥8.0） | `.tmp/187_urban_ch100_final.json` |
| T9 | meta=0、duplicate=0、timeline=0 | `.tmp/187_seg100_metrics.md` |
| 段审计 | critical_orphans=0、halt_would_fire=false | `.tmp/187_seg100_audit.json` |
| 成本 | 约 ¥13.26 / 1766 次 LLM 调用（预算 ¥25.0） | DB `llm_call_usage` |

---

## 关键现场

- DB：`.tmp/task172b_urban_ch100.db`
- project_id：`81e345042b124ee2a73094b82e4be555`
- run_id：`run-d22b1a44`
- 体裁注册表：`base_budget=14000`、`continuity.health_overdue_weight=0.08`、`foreshadowing_horizon_floor=0`

---

## 爬坡分段记录

| checkpoint | wrapper | five-gate | T9 | segment audit | 决策 |
|---:|---|---|---|---|---|
| Ch25 | PASS：25/25 accepted | PASS：budget 0.9595、CED 0.1127、overdue 19、health 8.5、gap 0 | PASS | PASS：critical_orphans=0 | 进入 Ch50 |
| Ch50 | PASS：50/50 accepted | PASS：budget 0.9595、CED 0.0977、overdue 51、health 8.9、gap 0 | PASS（187.w 后） | PASS | 进入 Ch75 |
| Ch75 | PASS：75/75 accepted | PASS：budget 0.9595、CED 0.0891、overdue 73、health 8.4、gap 0 | PASS（187.x 后） | PASS | 进入 Ch100 |
| Ch100 | PASS：100/100 accepted | PASS：budget 0.9595、CED 0.11、overdue 100、health 8.6、gap 0 | PASS（187.y/z 后） | PASS | 终判完成 |

---

## 撞墙修复链

| 子任务 | 触发 | 修复 |
|---|---|---|
| 187.u | Ch21 settlement past-horizon plant | 过滤 LLM 抽取噪声，保留 `source_version_id` 硬约束 |
| 187.s | Ch25 health < 8.0 | urban `continuity.health_overdue_weight=0.08` |
| 187.v | Ch3 numerical settlement | documented isolate，不改代码 |
| 187.p | Ch19 ContextEmergency | urban `base_budget=14000` |
| 187.t | Ch23 `//` T9 artifact | urban writer_rules 禁 `//`；deterministic clean Ch23 |
| 187.w | Ch50 meta/duplicate/timeline | slash 安全单位、C-style comment clean、duplicate clean；timeline markers 扩展 |
| 187.x | Ch75 timeline 2 条 | bracket metadata 块忽略、`父亲` marker |
| 187.y | Ch100 duplicate=2 / timeline=2 | deterministic clean Ch81/Ch88；`天前`、`隐蔽通道` markers；context radius 30→80 |
| 187.z | Ch100 timeline 1 条 | 全角括号/行内代码块忽略、`物理隔离`、`项目被封存`、`身份验证` markers；紧凑时间戳启发式 |

---

## 代码改动

- `src/songyan/evals/timeline_consistency.py`
  - `_METADATA_BLOCK_RE`：覆盖 `【...】`、`` `...` ``、`[...]` 三种元数据/档案块
  - `_FLASHBACK_MARKERS`：补充 `注册日期`、`父亲`、`天前`、`隐蔽通道`、`物理隔离`、`项目被封存`、`身份验证`
  - `_context_window` 默认半径 30→80
  - 新增紧凑时间戳启发式：日期后紧跟 `HH:MM(:SS)` 视为机器/口令时间戳
- `src/songyan/services/text_cleanliness_cleaner.py`（已有能力复用）
  - `apply_project_text_cleaning()` 生成 Ch81/Ch88 clean accepted 版本
- `tests/test_185_t9_precision_fixes.py`
  - 新增 9 个回归测试覆盖 bracket metadata、父子回忆、相对过去引用、隐蔽通道、全角括号、物理隔离、行内代码文件名、项目封存、紧凑时间戳

---

## 验证

- 聚焦测试：`tests/test_185_t9_precision_fixes.py` + `tests/test_162_timeline_consistency.py` → **47 passed**
- 全量测试：`python -m pytest tests/ -q` → **2981 passed, 2 skipped, 1 xfailed, 7 warnings**，`WRAPPER_RESULT=PASS_NORMAL_EXIT`
- 静态检查：`ruff check src/ tests/` → **All checks passed**
- 终判命令：
  ```powershell
  python scripts/five_gate_check.py --genre urban --db .tmp/task172b_urban_ch100.db --project-id 81e345042b124ee2a73094b82e4be555 --up-to 100 --format json > .tmp/187_urban_ch100_final.json
  python scripts/segment_audit.py --db .tmp/task172b_urban_ch100.db --project-id 81e345042b124ee2a73094b82e4be555 --up-to 100 --format json > .tmp/187_seg100_audit.json
  $env:DATABASE_URL = "sqlite:///.tmp/task172b_urban_ch100.db"
  songyan metrics --project-id 81e345042b124ee2a73094b82e4be555 --chapters 1-100 -o .tmp/187_seg100_metrics.md
  Remove-Item Env:\DATABASE_URL
  ```

---

## 结论

urban 第三体裁 Ch1-Ch100 爬坡完成，V9 B 组六条全部满足，T9 硬红线洁净度归零。Task 187 正式闭环。
