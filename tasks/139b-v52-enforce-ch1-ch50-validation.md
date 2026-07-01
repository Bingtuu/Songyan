# Task 139b：V5.2 Enforce 模式 Ch1-Ch50 复跑验证

> **类型**: 实跑验证
> **状态**: ✅ 已完成（第二次重跑通过）
> **前置**: Task 139a 已完成；Task 139e 已修复 `rewrite_node` 丢失 mandatory reference 缺陷；Task 139f 已修复 `revision_router` 回滚 bypass mandatory reference 缺陷。
> **依赖**: `scripts/run_139b_enforce_ch1_ch50.py`、新 clean 项目、V5.2 主干默认配置 + 139e/139f 修复。
> **首次验证项目 ID**: `0b77411865fd4cd6a5543eaf6f211e6c`
> **首次验证 DB**: `.tmp/task139b_enforce_ch1_ch50.db`
> **首次后台任务 ID**: `bash-uj1c0w68`
> **首次启动时间**: 2026-06-30
> **首次结果**: Ch21 触发 `health_low_p1_halt`（critical orphan `scifi.main_deck.chen_luo_log`）
> **第一次重跑项目 ID**: `7229f28ee6f24fe685364bf9a1bc1f84`
> **第一次重跑 DB**: `.tmp/task139b_enforce_ch1_ch50_rerun.db`
> **第一次重跑后台任务 ID**: `bash-gzdafv5c`
> **第一次重跑结果**: Ch24 触发 `health_low_p1_halt`（critical orphan `alien_builder.remains.crystal_fragment`，revision_rebound 后 bypass）
> **第二次重跑项目 ID**: `6dde3f9083f54725b867a6100cefc7eb`
> **第二次重跑 DB**: `.tmp/task139b_enforce_ch1_ch50_rerun2.db`
> **第二次重跑后台任务 ID**: `bash-51dxohn9`
> **第二次重跑结果**: ✅ Ch1-Ch50 全部 `accepted`，`failed=[]`，无 `AutoHaltException`
> **第二次重跑结束时间**: 2026-06-30T22:51:38

## 背景

Task 129 曾在 enforce 模式下跑 Ch1-Ch50，但 Ch15 因 `quality_gate_fail_streak` 暂停，暴露的是 Writer 结构退化、SettlementExtractor 提取失败、orphaned settings 快速累积等底层缺陷。这些缺陷已由 Task 133/134/135 及 138n/138o 修复。现在需要用当前默认配置重新验证 enforce 模式能否跑完 Ch1-Ch50 而不误触发 AutoHalt。

## 目标

在 **新 clean 项目** 中以 `gate_mode="enforce"` 跑完 Ch1-Ch50，确认无 false positive gate 触发，为默认启用 enforce 模式提供 Ch1-Ch50 证据。

## 验收标准

- [ ] 新建项目并使用与 `run-a2bed648` / `run-01a32b97` 相同的 genre（scifi）和 mode（webnovel_intense）。
- [ ] 执行 `songyan run --gate-mode enforce`（或等价调用）从 Ch1 跑到 Ch50。
- [ ] Ch1-Ch50 全部 `accepted`，`failed=[]`，无 `AutoHaltException`。
- [ ] 所有 gate 触发次数为 0（或均为真实问题，且真实问题已被 revision 闭环解决）。
- [ ] settlement / QG 通过率 ≥ 95%（允许开局期少量 `degraded_accept`）。
- [ ] 生成报告 `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md`。
- [ ] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤（已执行）

1. **创建新项目**
   使用脚本在干净 DB 中新建项目：
   ```powershell
   $env:DATABASE_URL = "sqlite:///.tmp/task139b_enforce_ch1_ch50.db"
   python scripts/run_139b_enforce_ch1_ch50.py --init
   ```
   生成项目 ID：`0b77411865fd4cd6a5543eaf6f211e6c`。

2. **启动 enforce 模式运行**
   以后台任务方式启动：
   ```powershell
   $env:DATABASE_URL = "sqlite:///.tmp/task139b_enforce_ch1_ch50.db"
   $env:PROJECT_ID = "0b77411865fd4cd6a5543eaf6f211e6c"
   $env:GATE_MODE = "enforce"
   python scripts/run_139b_enforce_ch1_ch50.py
   ```
   后台任务 ID：`bash-uj1c0w68`。

3. **监控与记录**
   - 脚本每章记录 `quality_gate_passed`、`settlement_success`、`gate_triggers`、`context_emergency`、`health_score`；
   - 若触发 AutoHalt，脚本会捕获 `AutoHaltException` 并记录 halt 原因；
   - 运行日志写入 `logs/chapter_runs/<run_id>.jsonl`。

4. **失败处理（已发生）**
   - Ch21 触发 `health_low_p1_halt`；
   - 根因定位：`rewrite_node` 整章重写时未继承 mandatory references，导致 critical orphan `scifi.main_deck.chen_luo_log` 回收丢失；
   - 新建 **Task 139e** 修复 `rewrite_node`，修复后重跑。

5. **生成报告**
   - 脚本完成后自动生成 `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md`；
   - 汇总 50 章关键指标，并与 Task 129 `run-89d7a2d4` 做对比。

## 不做的事

- 不克隆旧项目（避免历史数据污染）；
- 不临时切换 Writer 版本（使用 manifest 默认版本）；
- 不修改 gate 配置（只验证）。

## 风险与 Fallback

- **风险**：Ch1-Ch10 开局期 QG false 仍可能触发 `quality_gate_fail_streak`。
  - Fallback：若发生，确认 Task 128 的 `degraded_accept` 标记是否正确生效；若未生效，修复后重跑。
- **风险**： enforce 模式暴露新缺陷导致暂停。
  - Fallback：记录问题，修复后重跑；V5.2 可继续延后 enforce 默认启用。
