# Task 176: Windows 防卡 wrapper 工具化

> **阶段**: V9.1 长跑可靠性
> **类型**: 基础设施（工具化既有协议）
> **优先级**: P1——V9.1 收尾项；173/175 已修复并实跑验证已知挂死/失控成本路径，本 Task 是兜底安全网与协议工具化，不是挂死修复或成本熔断的替代品
> **依赖**: 173/174/175 已完成（挂死根因、应用日志、成本熔断均已闭环；wrapper 语义从"前置救火"降级为"无人值守保险丝"）
> **状态**: ✅ 完成（wrapper 落地 + 自检 11/11 + 双 review 修复 + 实跑验收通过；旧脚本已标注弃用；DONE: `archive/v9/176-windows-anti-hang-wrapper-DONE.md`）
> **来源**: V5 Windows 测试进程防卡协议（`archive/v5/context-docs/AGENTS-full-20260621.md` §160-221，文档协议未工具化）；历史 wrapper `archive/v5/scripts/run_task117.ps1`（单任务硬编码）；2026-07-19 D2 实跑挂死 50+ 分钟才被人为发现（`archive/v9/173-interpreter-exit-hang-fix.md` 执行记录）；`tasks/V9-README.md` Task 176 行

---

## 背景

- **协议只有文档没有通用工具**：V5 防卡协议（PowerShell Job + 硬超时 + 标准判定标记）自 2026-06 起是书面纪律，每次长跑/全量测试靠手工重写一次性 wrapper；历史脚本 `archive/v5/scripts/run_task117.ps1` 硬编码单章命令与 300s 超时，不可复用。
- **当前活跃脚本仍是专用形态**：`scripts/run_songyan_chapter.ps1` 已有日志、`WRAPPER_RESULT`、`project_pipeline.end` 检测和业务完成后超时判断，但它仍硬绑定 `songyan run` 参数，不是任意命令 wrapper；且超时清理用 `Stop-Process` 主 PID，未显式验证整棵子进程树。
- **协议的工具缺口在 175 D2 实证过一次**：2026-07-19 scifi end10 进程在结果落盘后挂死，**50+ 分钟无人察觉**（彼时 173 真修未落地）。硬超时 wrapper 会把这种未知挂死收敛到超时上界内自动暴露并清理现场。173 已确证并修复已知根因（sqlite checkpointer 泄漏），但**未来新泄漏源无法先验排除**——wrapper 是无人值守长跑的保险丝。
- **历史/现有 wrapper 的两个缺陷**（本 Task 修正）：① 清理边界不稳，可能只杀 wrapper 宿主或主 PID，**不保证杀孙进程**；② pytest 摘要已过但 teardown 卡住的细分标记没有通用实现。

## 目标

1. 提供通用工具 `scripts/run_with_timeout.ps1`：任意命令 + 硬超时 + 标准判定标记 + 超时进程树清理 + 日志落盘。
2. 实现 V5 协议的四档标准标记（含 `PASS_WITH_TEARDOWN_TIMEOUT` 细分），但 pass marker 必须显式启用或自动限定在 pytest 命令，禁止任意命令随便打印 `73 passed` 后被误判 PASS。
3. 提供 `-SelfTest` 自检模式，自动跑本地无 API 矩阵（含进程树清理、参数转义、误判防护），并落盘证据。
4. 泛化/替代现有 `scripts/run_songyan_chapter.ps1`：保留旧脚本为 thin wrapper 或明确弃用路径，统一 `WRAPPER_RESULT` 语义。
5. 文档指向更新：README FAQ 与 AGENTS.md 的防卡条目从"查阅归档协议"改为"使用本工具"。

---

## 技术方案

### 1. 命令行界面

```powershell
# 通用形式：-- 是本脚本约定的 sentinel（脚本自行剥离），不是 PowerShell 原生 POSIX 语义
scripts/run_with_timeout.ps1 -TimeoutSec 3600 -DetectPytestSummary -- python -m pytest tests/ -q
scripts/run_with_timeout.ps1 -TimeoutSec 7200 -Tag 172b-urban -SuccessMarkerRegex "project_pipeline\.end.*final_status=completed" -- python scripts/run_172b_ch100_climb.py --to 100
scripts/run_with_timeout.ps1 -SelfTest
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `-TimeoutSec` | 3600 | 硬超时（秒）。超时即杀进程树并判 TIMEOUT |
| `-TeardownGraceSec` | 120 | 宽限期：检测到 pytest 完整通过摘要后，再等进程自然退出的秒数；超出判 `PASS_WITH_TEARDOWN_TIMEOUT` 并杀树 |
| `-Tag` | 时间戳 | 日志文件名片段 |
| `-LogDir` | `logs\wrapper` | 输出日志目录（自动创建） |
| `-DetectPytestSummary` | 自动（仅命令形态为 `python -m pytest` 时默认启用） | 启用 pytest 完整通过摘要识别；非 pytest 命令默认禁用，防误判 |
| `-SuccessMarkerRegex` | 空 | 额外业务完成标记；长跑场景必须带成功语义，例如 `project_pipeline\.end.*final_status=completed`，可用于 teardown timeout 后判 `PASS_WITH_TEARDOWN_TIMEOUT` |
| `-SelfTest` | false | 不执行外部命令，改为运行本脚本自检矩阵 |
| `--` 后参数 | 必填（`-SelfTest` 除外） | 被包装命令与参数；用 `[Parameter(ValueFromRemainingArguments=$true)] [string[]]$Command` 接收，若首项为 `--` 则脚本剥离 |

PowerShell 5.1 注意：`--` 不是 shell 级 stop-parsing；本脚本只是把它当普通参数 sentinel。`Start-Process` 在 5.1 下最终仍需要拼接 `Arguments` 字符串，因此必须实现 `Join-CommandArguments` / `Quote-Argument` helper，并用自检覆盖空格、引号、反斜杠等参数。默认不经 `cmd.exe /c`，除非用户显式把 `cmd.exe` 作为被包装命令。

### 2. 执行模型

- `Start-Process -PassThru` 直接启动目标命令（记录 PID），stdout/stderr 分别重定向到 `<LogDir>/<Tag>-<timestamp>.out.log / .err.log`，同时 tee 到 console。
  - **为什么用 `Start-Process` 而非 V5 协议字面的 `Start-Job`**：语义相同（独立进程 + 硬超时 + 输出捕获），但 `Start-Process -PassThru` 直接返回被包装命令的 PID，超时时的进程树清理（`taskkill /T`）精确可控；`Start-Job` 多一层 PowerShell 宿主，孙进程树更深、清理边界更模糊。这是历史 wrapper 不杀孙进程缺陷的直接修正。
- tee 输出实现不得用会长期占锁的 `Get-Content -Wait` 作为首选；用周期性共享读 + offset 增量读取 out/err log，避免重复打印整份长日志，也避免与被包装命令写文件竞争。
- 主循环轮询（每 2-5s）：进程是否退出 / 是否超 `-TimeoutSec` / out+err 增量文本是否出现启用的 pass marker。
  - pytest 摘要检测只在 `-DetectPytestSummary` 启用时生效；正则要求单行包含 `\d+ passed` 且该行不含 `failed|error|errors`。
  - 非 pytest 命令默认不因 `\d+ passed` 判 PASS；业务命令必须显式传 `-SuccessMarkerRegex`。
- **退出**：读取进程退出码 → 判定标记输出。
- **超硬超时**：优先执行 `taskkill /PID <pid> /T /F` **杀整棵进程树**；失败后才 fallback `Stop-Process -Id <pid> -Force`。禁止先杀父进程再 taskkill，否则可能让子进程脱离 PID 树，复现“孙进程残留”。清理后用 `Get-CimInstance Win32_Process` / marker PID 复核子进程已退出；只杀本 wrapper 启动的 PID 树，不碰无关进程（V5 协议 §7）。
- **超宽限期**（摘要已过但进程不退出）：同上杀树，标记 `PASS_WITH_TEARDOWN_TIMEOUT`，退出码 0（按 V5 §5 语义：断言通过，teardown 卡住不算失败）。

### 3. 标准判定标记（输出到 stdout 与 meta 文件）

| 标记 | 含义 | 退出码 |
|---|---|---|
| `WRAPPER_RESULT=PASS_NORMAL_EXIT` | 命令成功且进程正常退出（pytest 场景含断言通过） | 0 |
| `WRAPPER_RESULT=PASS_WITH_TEARDOWN_TIMEOUT` | pytest 完整通过摘要已见，进程超宽限期未退出（断言通过，teardown 卡住） | 0 |
| `WRAPPER_RESULT=FAIL_NONZERO_EXIT` | 命令非零退出（对应 V5 协议的 `PYTEST_NONZERO_OR_UNKNOWN`，通用化命名） | 原退出码 |
| `WRAPPER_RESULT=TIMEOUT_WITHOUT_PASS_SUMMARY` | 硬超时且未见通过摘要（与 V5 协议标记同名） | 124 |

meta 文件记录：命令行、PID、起止时间、退出码、标记——与 V5 协议 §4 的字段对齐。

meta/result 必填字段：`wrapper_version`、`command_line`、`child_pid`、`start_time`、`end_time`、`duration_sec`、`timeout_sec`、`teardown_grace_sec`、`pass_marker_type`（`pytest|business|none`）、`pass_marker_seen_at`、`killed_process_tree=true/false`、`exit_code`、`WRAPPER_RESULT`。`PASS_WITH_TEARDOWN_TIMEOUT` 额外输出 `ACTION_REQUIRED=investigate_teardown_hang`，避免被 CI/人工当成完全绿灯吞掉。

### 4. 与 173/176 的关系（文档中写清，避免语义回退）

173 修复后正常路径进程应在结果落盘后数秒内自然退出（实证 2.5s）；wrapper 的宽限期默认值 120s 远高于此。**`PASS_WITH_TEARDOWN_TIMEOUT` 在 173 之后应近似零触发**；若实跑中再次出现该标记，视为新的挂死线索，必须记录并上报（不得默默通过）——在 wrapper 输出中加一行引导语。

## 验证

### 自检测试矩阵（`-SelfTest` 自动逐项执行，全部为本地无 API 命令）

| # | 场景 | 命令（示例） | 预期标记 |
|---|---|---|---|
| 1 | 快速成功 | `-- python -c "print('ok')"` | `PASS_NORMAL_EXIT`，退出码 0 |
| 2 | 快速失败 | `-- python -c "import sys; sys.exit(3)"` | `FAIL_NONZERO_EXIT`，退出码 3 |
| 3 | 硬超时杀树 | `-TimeoutSec 5 -- python -c "import subprocess,time,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(300)']); print('CHILD_PID='+str(p.pid), flush=True); time.sleep(300)"` | `TIMEOUT_WITHOUT_PASS_SUMMARY`，退出码 124；meta 记录 child PID；父子 python 均被杀死（PID 复核） |
| 4 | 非 pytest 误判防护 | `-TimeoutSec 5 -- python -c "print('73 passed', flush=True); import time; time.sleep(300)"` | 未启用 pass marker，必须 `TIMEOUT_WITHOUT_PASS_SUMMARY`，防止任意命令打印 `passed` 被误判 |
| 5 | 摘要已过 + 挂死 | `-TimeoutSec 10 -TeardownGraceSec 3 -DetectPytestSummary -- python -c "print('73 passed', flush=True); import time; time.sleep(300)"` | `PASS_WITH_TEARDOWN_TIMEOUT`，退出码 0；进程树被杀；meta 含 `ACTION_REQUIRED=investigate_teardown_hang` |
| 6 | 参数转义 | `-- python -c "import sys; print(sys.argv[1:])" "a b" "\"q\"" "semi;colon"` | `PASS_NORMAL_EXIT`；out.log 中 argv 与期望一致 |
| 7 | pytest 真跑（快子集） | `-DetectPytestSummary -- python -m pytest tests/test_173_pipeline_cleanup.py -q` | `PASS_NORMAL_EXIT` |

### 实跑验收（V9-README 176 验收要点）

- 用 wrapper 跑一次 scifi `--end 1` 短窗口实跑（建议 `SONGYAN_RUN_COST_BUDGET=2`，`-- python scripts/run_172a7_genre_validation.py --templates scifi --end 1`）：进程自然退出、`PASS_NORMAL_EXIT`、成本遥测行落库正常（与 175 兼容）。
- 全量 `python -m pytest tests/ -q` 与 `ruff check src/ tests/` 绿（本 Task 不动 src/，仅新增脚本与文档，预期零回归）。

## 出口标准

1. `scripts/run_with_timeout.ps1` 落地，四档标记 + 进程树清理 + 日志落盘；
2. `-SelfTest` 自检矩阵 7 项全过（进程树复核证据落盘）；
3. scifi `--end 1` 实跑验收通过；
4. `scripts/run_songyan_chapter.ps1` 改为 thin wrapper 调用 `run_with_timeout.ps1`，或在 README/脚本头明确弃用并指向新工具，避免双语义长期并存；
5. README FAQ 与 AGENTS.md 防卡条目更新指向本工具；V9-README 176 行翻正；
6. 本 Task 执行记录补录本文档。

## 执行记录（2026-07-19）

### 实现

- `scripts/run_with_timeout.ps1`（wrapper_version 1.1.0，PS 5.1 兼容，纯 ASCII）：四档标记 + meta 13 字段（review 后扩展为 `root_killed`/`tree_kill_status`/`deadline_hit` 等诚实语义）+ 硬超时先 `taskkill /T /F` 后 `Stop-Process` fallback + child sweep + `Get-CimInstance` 复核 + PID 复用守卫（CreationDate 校验）+ `-DetectPytestSummary`（pytest 形态宽匹配自动启用，summary 必须含 `in <duration>`，允许 `xfailed`）+ `-SuccessMarkerRegex` 业务标记 + `-SelfTest` 自检模式 + offset 增量 tee + P/Invoke 退出码获取（PS 5.1 重定向下 `ExitCode` 为 null 的实证坑）。
- **参数接收偏离**（review 实证成立）：不用 `[Parameter(ValueFromRemainingArguments=$true)]`，改手工解析 `$args`——PS 5.1 绑定器在 `-File` 模式拒绝 `--`、参数名前缀匹配偷子命令参数（`-c`→`-Command`、`-v`→`-Verbose`、`--to`→`-TimeoutSec`）。脚本头注释已写明。
- `scripts/run_songyan_chapter.ps1` 头部标注 **DEPRECATED**（含三档 WARN 语义 delta 与迁移指引），指向新工具；历史任务（121b）引用保留可用。

### Review 与修复

- 规格符合性 review：✅ 通过（手工 `$args` 偏离由 reviewer 独立复现三个绑定器问题后判定成立）。
- 代码质量 review：With fixes——修复 4 项 Important（`killed_process_tree` 在 fallback 撒谎 → 拆 `root_killed`/`tree_kill_status` + child sweep；business marker 与 auto-enable 自检盲区 → 自检 7→9 项；grace/hard deadline 判定失真 → `deadline_hit` + 分支文案；PID 复用窗口 → CreationDate 守卫）+ 4 项 Minor（meta 去 BOM 改 ascii、主循环 try/catch/finally 保 meta、超时参数正整数校验、`-Tag` 路径净化）。
- 二次 code review follow-up：修复 3 项 P1 + 1 项 P2（旧脚本迁移示例改为匹配 `final_status=completed`；pytest pass marker 限定最终 summary 格式，防 live output 误触发；允许 `xfailed` 的通过摘要；SelfTest case9 清目录并新增 case10/case11），自检扩展到 11 项。

### 验证

| 项 | 结果 |
|---|---|
| `-SelfTest` 自检矩阵 | **11/11 ALL_PASS**（PS 5.1.26100；含真实杀树复核、误判防护、teardown 宽限、参数转义、business marker、auto-enable 端到端、pytest live-output 防误判、`xfailed` 摘要）证据 `.tmp/176_selftest/` |
| 无误杀 | 多轮真实杀树期间，用户 2 个无关 python 长跑进程全程存活 |
| 实跑验收（`SONGYAN_RUN_COST_BUDGET=2`，wrapper 跑 scifi `--end 1`） | **PASS_NORMAL_EXIT**，exit 0；1/1 accepted、T9=0、overdue=0、budget 0.9575；usage 遥测 12 行全部 `token_source='response'`（175 兼容）；meta 字段正确（`root_killed=false`、`tree_kill_status=not_attempted`） |
| 全量 `python -m pytest tests/ -q` | 2882 passed, 2 skipped, 1 xfailed（本 Task 零 src 改动） |
| 文档 | README FAQ、AGENTS.md 防卡条目已指向本工具 |

### 已知限制（不阻塞）

- `case3_tree_evidence.txt` 为自检产物仍带 BOM（meta 契约文件已去 BOM）；非 UTF-8 子进程输出的 tee 可读性（ASCII marker 不受影响）；wrap `.bat/.cmd` 时 cmd 元字符复活（头部已声明）；`--` 作为命令首参的极端情况不可表达（注释已注明）。

---

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 进程树清理误伤 | 自检 #3 发现无关 python 进程被杀 | 严格只杀 `Start-Process -PassThru` 返回 PID 的 `taskkill /T` 树；复核父链 |
| PowerShell 版本差异 | 参数转义或 `Start-Process` 行为在 PS 5.1 / 7+ 不一致 | 显式检测 `$PSVersionTable.PSVersion`，文档声明支持范围；自检在当前版本必须全绿；优先兼容 5.1 |
| 参数透传破坏 | 自检 #6 argv 不一致 | 修 `Quote-Argument` / `Join-CommandArguments`；禁止用 `cmd.exe /c` 包一整串命令作为默认实现 |
| tee 输出与文件竞争 | wrapper 读日志导致被包装命令写失败或 console 重复刷全量日志 | 改用共享读 + offset 增量 tail；避免 `Get-Content -Wait` 长持有句柄 |
| pytest 摘要误判 | 输出含 "1 failed, 73 passed" 或非 pytest 命令打印 "73 passed" 被误判通过 | pytest 摘要只在 `-DetectPytestSummary`/pytest 命令启用；正则要求摘要行不含 `failed|error|errors`；宁可判 TIMEOUT/UNKNOWN 不误判 PASS |

## Out of Scope

- Git Bash 版 wrapper（Windows 主路径是 PowerShell；Git Bash 用户可 `powershell -File scripts/run_with_timeout.ps1 -- ...` 调用）；
- CI 集成（归 Task 181 统一设计）；
- 远程/分布式执行；
- 修改 V5 协议文本本身（归档文档不动，本 Task 是工具化其实现）。
