# 210 · M1 代码验收 PASS

| 项 | 内容 |
|---|---|
| 状态 | DONE |
| 关联 | PRD 6.3–6.4 / S8；tech-m1 §6–7；W0 写半边 + W6 |
| 预估 | 验收记录（无新代码） |

## 目标

在 `main` 上确认 M1 步 1–5 与 tech-m1 §6–7 的代码验收通过，并留下可检索的归档，供 STATUS / HANDOFF 引用。不声称 V1.0 完成，不升包版本，不开 M2 / tech-m2 编码。

## 步骤

- [x] 核对 tip：`main` @ `69d7ece`（#41 步 5 合入之后）
- [x] 跑 tech-m1 §7 命令 + `tests/cli/test_w0_e2e.py`；对照 §6 项 1–10
- [x] 实测 CLI（都市灵异夹具 + 最小项目 `check`）
- [x] 同步 STATUS / HANDOFF / INDEX / AGENTS / tasks：下一闸门 = owner 决定是否起草/接受 tech-m2（本记录不写 M2 代码）

## 验收标准

- [x] 步 1–5 均已在 `main`（#35 / #36 / #38 / #39 / #41）
- [x] tech-m1 §6–7 代码项 PASS（见完成总结）；S1/S2 产品周期日志不在代码验收内
- [x] 无 pyproject 版本 bump；无 `workflows/` / `agents/settlement_extractor/` 相对 M0 tip 的行为漂移；五表 `rejected` 迁移已落地

## 完成总结（DONE 时填写）

在 `main` `69d7ece`（2026-11-04 Asia/Shanghai）上的代码验收证据：

### §7 验证命令

- `ruff check src/ tests/`：All checks passed
- plan / 圣经：`tests/db/test_plan_fact_cards.py` + `tests/db/test_dushi_lingyi_plan_facts.py` + `tests/plan_checks/test_plan_bible_runtime.py` → **42 passed**
- `tests/cli/test_workbench_commands.py` → **10 passed**
- `tests/cli/test_canon_write_commands.py` + `test_check_command.py` + `test_w0_e2e.py` → **25 passed**

### tech-m1 §6 对照（entity+attribute 硬门）

| # | 项 | 结果 | 证据 |
|---|----|:----:|------|
| 1 | 未 confirm 行不进圣经（S8） | PASS | `test_canon_edit_*_not_bible`；`test_rejected_cards_stay_out_of_the_bible`；W0 e2e |
| 2 | confirm 后进 `list_canon_*`；人写 attribute `source=human` | PASS | `test_canon_confirm_attribute_approves_list_canon_and_bible`；edit 强制 human |
| 3 | dismiss → `rejected`；不在 Canon / 默认 Pending | PASS | `test_canon_dismiss_*`；`TestRejectedApprovalStatus`；实测 show |
| 4 | 无持久 `accepted`；CLI `accept` 不写库 | PASS | `test_canon_accept_does_not_persist_status`；实测 accept |
| 5 | 写命令与 `check` 不调模型 | PASS | `canon_write.py` / `check.py` / `plan_fact_repo.py` 无 LLM 引用；路径无模型 |
| 6 | `apply_settlement` 目标表与开工前相同 | PASS | `git diff 80f4107..69d7ece -- src/songyan/agents/settlement_extractor src/songyan/workflows` 空 |
| 7 | `check`：正文=ChapterVersion.content；注入 extracts；计划行不变；不 invent；无 confirm | PASS | `test_check_*`；实测 COUNTS/ROWS_UNCHANGED |
| 8 | 无章/硬伤 exit 2；通过 exit 0；无「可以发表」 | PASS | `test_check_pass_exit_0_*`；`test_check_no_chapter_exits_2`；实测 0/2 |
| 9 | ruff + 既有 plan/workbench/CLI 测试 | PASS | 见上 §7 |
| 10 | 五表 rejected 迁移；无无关大改；无版本漂移 | PASS | migrations + `TestRejectedApprovalStatus`；`pyproject` 仍 `0.5.0` |

### 实测 CLI（无长 `run` / 无 LLM）

临时库 + 捆绑 `dushi-lingyi`（《末班铜牌》）：

- `canon show` / `today` / `today --json` → exit **0**；`next` = `可用 canon confirm 入典；生成不在本命令。`
- `canon edit` entity+attribute → exit **0**；Pending 可见；attribute 文案含 `source=human`
- `canon confirm` entity → exit **0**，Canon 可见；`canon dismiss` attribute → exit **0**，Pending/Canon 均不可见；DB `rejected` + `source=human`
- `canon accept` → exit **0**，不改变已 approved 状态（非持久）

最小项目 `check`（避免夹具 must-mention 干扰 exit 0）：

- `--chapter 1` + 匹配 extracts → exit **0**（无「可以发表」；提示另走 confirm）
- 不匹配 extracts → exit **2**（点名实体/键/圣经值/正文侧值）
- `--chapter 9` 无章 → exit **2**
- 三次 `check` 前后 plan 五行 counts **与整行内容均不变**

对完整 dushi 夹具 + 薄章正文的 `check` 因 must-mention/claims 硬伤 exit 2（夹具语义，非回归）；属性不一致报告字段在 mismatch 路径已点名。

遗留：owner 决定是否起草 / 书面接受 `docs/tech-m2.md` 之前，**不开 M2 编码**、不声称 V1.0 完成。本记录不改 `src/` / `tests/` 行为。
