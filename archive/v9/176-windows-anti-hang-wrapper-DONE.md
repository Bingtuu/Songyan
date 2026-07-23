# Task 176 DONE: Windows 防卡 wrapper 工具化

> **完成时间**: 2026-07-19
> **阶段**: V9.1 长跑可靠性
> **状态**: ✅ 完成（wrapper 落地 + 自检 11/11 + 双 review 修复 + 实跑验收通过）
> **任务书**: `archive/v9/176-windows-anti-hang-wrapper.md`（含执行记录）

---

## 交付内容

- **`scripts/run_with_timeout.ps1`**（wrapper_version 1.1.0，PS 5.1 兼容，纯 ASCII）：任意命令 + 硬超时 + 四档标准判定标记（`PASS_NORMAL_EXIT` / `PASS_WITH_TEARDOWN_TIMEOUT`（含 `ACTION_REQUIRED=investigate_teardown_hang`）/ `FAIL_NONZERO_EXIT` / `TIMEOUT_WITHOUT_PASS_SUMMARY`）+ meta 诊断字段（含 `root_killed`/`tree_kill_status`/`deadline_hit` 诚实语义）+ 日志落盘。
- **进程树清理**：先 `taskkill /T /F` 后 `Stop-Process` fallback + child sweep + `Get-CimInstance` 复核 + PID 复用守卫（CreationDate 校验）；只杀本 wrapper 启动的 PID 树。
- **误判防护**：`-DetectPytestSummary` 仅 pytest 命令形态（宽匹配 python/py/全路径/venv）默认启用；业务命令必须显式 `-SuccessMarkerRegex`。
- **`-SelfTest` 自检模式**：11 项矩阵自动化并落盘证据（成功/失败/超时杀树复核/防误判/teardown 宽限/参数转义/pytest 子集/business marker/auto-enable 端到端/pytest live-output 防误判/`xfailed` 摘要）。
- **PS 5.1 实证坑处理**：P/Invoke 取退出码（重定向下 `ExitCode` 为 null）；手工 `$args` 解析替代 param()（绑定器拒绝 `--` + 前缀匹配偷参，review 独立复现判定偏离成立）。
- **旧脚本处置**：`scripts/run_songyan_chapter.ps1` 头部标注 DEPRECATED（含三档 WARN 语义 delta 与迁移指引）。
- **文档**：README FAQ、AGENTS.md 防卡条目指向本工具。

## 验证

| 命令 / 证据 | 结果 |
|---|---|
| `powershell -File scripts/run_with_timeout.ps1 -SelfTest` | **11/11 ALL_PASS**（PS 5.1.26100；真实杀树复核、误判防护、参数转义、business marker、auto-enable、pytest live-output 防误判、`xfailed` 摘要全覆盖），证据 `.tmp/176_selftest/` |
| 实跑验收（`SONGYAN_RUN_COST_BUDGET=2`，wrapper 跑 scifi `--end 1`） | **PASS_NORMAL_EXIT**，exit 0；1/1 accepted、T9=0、overdue=0、budget 0.9575；usage 遥测 12 行全部 `token_source='response'`（175 兼容） |
| 无误杀 | 多轮真实杀树期间，用户 2 个无关 python 长跑进程全程存活 |
| `python -m pytest tests/ -q` | 2882 passed, 2 skipped, 1 xfailed（本 Task 零 src 改动） |
| `ruff check src/ tests/` | All checks passed |

## 说明

- 与 173 的关系：`PASS_WITH_TEARDOWN_TIMEOUT` 在 173 真修后应近似零触发；一旦实跑中出现，`ACTION_REQUIRED=investigate_teardown_hang` 强制可见，不得默默通过。
- 已知限制：非 UTF-8 子进程输出的 tee 可读性（ASCII marker 不受影响）；wrap `.bat/.cmd` 时 cmd 元字符复活；`--` 作为命令首参的极端情况不可表达（均已在脚本头部声明）。
- Review 修复记录（4 Important + 4 Minor，二次 review follow-up 的 3 P1 + 1 P2）与参数接收偏离的完整论证见任务书执行记录。
