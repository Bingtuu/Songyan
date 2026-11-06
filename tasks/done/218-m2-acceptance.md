# 218 · M2 代码验收 PASS

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD §6.5–6.6 / §7.3 / S8；tech-m2 §6–7；W4 + W5 + 抽取提案 |
| 预估 | 验收记录（无新代码） |

## 目标

在 `main` 上确认 M2 步 1–6 与 tech-m2 §6–7 的代码验收通过，并留下可检索的归档，供 STATUS / HANDOFF 引用。不声称 V1.0 完成，不升包版本，不开 M3 / variant / continue 编码。

## 步骤

- [x] 核对 tip：`main` @ `f1c3093`（#53 步 6 合入之后）
- [x] 跑 tech-m2 §7 命令 + M2 CLI/DB 测试；对照 §6 项 1–10
- [x] 实测 CLI（都市灵异夹具：today / promise / confirm promise / `--hard` / check stale / extract→pending）
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks：下一闸门 = owner 决定是否起草/接受 tech-m3 或下一工作（本记录不写 M3 代码）

## 验收标准

- [x] 步 1–6 均已在 `main`（#44 / #46 / #48 / #50 / #52 / #53）
- [x] tech-m2 §6–7 代码项 PASS（见完成总结）；S3 产品周期数值不在代码验收内
- [x] 无 pyproject 版本 bump；无 hardness 列；无 variant / continue 注册；包仍 `0.5.0`

## 完成总结（DONE 时填写）

在 `main` `f1c3093`（2026-11-06 Asia/Shanghai）上的代码验收证据：

### §7 验证命令

- `ruff check src/ tests/`：All checks passed
- plan / 圣经：`tests/db/test_plan_fact_cards.py` + `tests/db/test_dushi_lingyi_plan_facts.py` + `tests/plan_checks/test_plan_bible_runtime.py` → **42 passed**
- `tests/cli/test_workbench_commands.py` + `test_canon_write_commands.py` + `test_check_command.py` → **34 passed**
- M2 专项：`test_workbench_promise_readonly.py` + `test_canon_confirm_promise.py` + `test_canon_confirm_hard_stale.py` + `test_check_stale_report.py` + `test_extract_pending_proposals.py` + `test_w0_e2e.py` + `tests/db/test_plan_attribute_source_extract.py` → **39 passed**

### tech-m2 §6 对照（硬门 + 清单 1–10）

| # | 项 | 结果 | 证据 |
|---|----|:----:|------|
| 硬门 | `today` planted/due/overdue 可读 | PASS | `test_today_counts_include_overdue_promise`；CLI 冒烟 |
| 硬门 | `canon show --kind promise` 开放列表 | PASS | `test_canon_show_kind_promise_lists_open_only`；CLI 冒烟 |
| 硬门 | `canon confirm promise` 人销账 + 追溯 | PASS | `test_confirm_promise_settles_and_backfills_trace`；CLI 冒烟 |
| 硬门 | `confirm attribute --hard` 窗口内 `content_stale` | PASS | `test_hard_attribute_marks_chapters_2_to_4_only`；CLI 冒烟 map `{2,3,4}=1,{1,5}=0` |
| 硬门 | `check` 报告 stale / 影响范围且不写库 | PASS | `test_check_reports_stale_range_*`；CLI 冒烟 `content_stale_chapters=[2,3,4]` 且 map 不变 |
| 硬门 | 抽取→pending→confirm；S8 | PASS | `test_apply_settlement_enqueues_pending_extract_not_canon`；`test_confirm_extract_enters_canon_source_stays_extract`；CLI 冒烟 |
| 1 | 硬属性 2–4 标脏；1/5 为 0 | PASS | `test_hard_attribute_marks_chapters_2_to_4_only` |
| 2 | 正文版本表既有行不被覆盖；无自动写作 | PASS | `test_hard_confirm_does_not_overwrite_chapter_version_content` |
| 3 | 软确认无旗标不标脏；`--mark-stale` 可标 | PASS | `test_soft_confirm_without_flags_does_not_mark_stale`；`test_soft_confirm_mark_stale_marks_window` |
| 4 | 插入 overdue 后 `today` 计数含它，非 Canon | PASS | `test_today_counts_include_overdue_promise`；`test_default_canon_show_does_not_leak_promises_as_canon` |
| 5 | 未经 confirm 不清 open；confirm 后 `resolved_*` | PASS | `test_without_confirm_open_set_unchanged`；`test_confirm_promise_settles_and_backfills_trace` |
| 6 | S3 只用 `foreshadowings`，无第二伏笔表 | PASS | `test_s3_uses_existing_foreshadowings_table_only`；冒烟 schema |
| 7 | 抽取 confirm 前不在 `list_canon_*`；S8=0 | PASS | extract pending 测试 + `test_plan_attribute_source_extract` |
| 8 | 旧结算表仍在；`untrusted_until_confirmed` | PASS | `test_settlement_tables_remain_untrusted_tag` |
| 9 | 无 hardness；无 variant/continue；包 `0.5.0` | PASS | 冒烟 PRAGMA / `cli --help` / `pyproject.toml` |
| 10 | ruff + 既有 plan/CLI + 本里程碑测试 | PASS | 见上 §7 |

### 实测 CLI（无长 `run` / 无 LLM）

临时库 + 捆绑 `dushi-lingyi`（《末班铜牌》）+ 章 1–5 accepted 版本 + open promises：

- `today` / `today --json` → exit **0**；`promise_planted/due/overdue`；`next` = `可用 canon confirm 入典或销账承诺；硬确认可用 --hard/--mark-stale；生成不在本命令。`
- `canon show --kind promise` → exit **0**；列出开放承诺
- `canon confirm promise` → exit **0**；`resolved` + `resolved_chapter` / `resolved_version_id`；today overdue 归零
- `canon confirm attribute --hard`（valid 2–4）→ exit **0**；`content_stale` 2/3/4=1，1/5=0；`chapter_versions.content` 不变
- 软确认无旗标 → ch1 不标脏
- `check --json` → 报告 `content_stale_chapters=[2,3,4]`；markdown 含 `受影响章：2–4（content_stale=1）`；不写库（夹具 must-mention 可使 exit 2，非回归）
- `apply_settlement` → pending `source=extract`；confirm 前不进 canon；confirm 后进 canon 且 source 仍 `extract`

遗留：owner 决定是否起草 / 书面接受 `docs/tech-m3.md`（或下一工作）之前，**不开 M3 / variant / continue 编码**、不声称 V1.0 完成。本记录不改 `src/` / `tests/` 行为。证据 tip = `f1c3093`（本验收文档 PR 合入后 tip 会变成合并提交）。
