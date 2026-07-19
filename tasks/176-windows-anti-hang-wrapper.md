# Task 176: Windows 防卡 wrapper 工具化

> **阶段**: V9.1 长跑可靠性
> **类型**: 基础设施（工具化既有协议）
> **优先级**: P1——V9.1 收尾项；173 已修复挂死根因，本 Task 是兜底安全网与协议工具化，不是挂死修复的替代品
> **依赖**: 173 完成（挂死根因已修，wrapper 语义从"唯一对策"降级为"安全网"）
> **状态**: ◻ 规划中
> **来源**: V5 Windows 测试进程防卡协议（`archive/v5/context-docs/AGENTS-full-20260621.md` §160-221，文档协议未工具化）；历史 wrapper `archive/v5/scripts/run_task117.ps1`（单任务硬编码）；2026-07-19 D2 实跑挂死 50+ 分钟才被人为发现（`tasks/173-interpreter-exit-hang-fix.md` 执行记录）；`tasks/V9-README.md` Task 176 行

---

## 背景

- **协议只有文档没有工具**：V5 防卡协议（PowerShell Job + 硬超时 + 标准判定标记）自 2026-06 起是书面纪律，每次长跑/全量测试靠手工重写一次性 wrapper；唯一的历史脚本 `archive/v5/scripts/run_task117.ps1` 硬编码单章命令与 300s 超时，不可复用。
- **协议的工具缺口在 D2 实证过一次**：2026-07-19 scifi end10 进程在结果落盘后挂死，**50+ 分钟无人察觉**（彼时 173 真修未落地）。硬超时 wrapper 会把这种未知挂死收敛到超时上界内自动暴露并清理现场。173 修复了已知根因（sqlite checkpointer 泄漏），但**未来新泄漏源无法先验排除**——wrapper 是无人值守长跑的保险丝。
- **历史 wrapper 的两个缺陷**（本 Task 修正）：① `Stop-Job` 只停 Job 的 PowerShell 宿主，**不杀孙进程**（python.exe 子进程树存活）；② 无"摘要已过 + teardown 卡住"的细分标记实现。

## 目标

1. 提供通用工具 `scripts/run_with_timeout.ps1`：任意命令 + 硬超时 + 标准判定标记 + 超时进程树清理 + 日志落盘。
2. 实现 V5 协议的四档标准标记（含 `PASS_WITH_TEARDOWN_TIMEOUT` 细分），pytest 场景自动识别通过摘要。
3. 自检测试矩阵全过 + 一次真实短窗口实跑验收（V9-README 176 验收要点）。
4. 文档指向更新：README FAQ 与 AGENTS.md 的防卡条目从"查阅归档协议"改为"使用本工具"。

---

## 技术方案

### 1. 命令行界面

```powershell
# 通用形式：-- 之后为被包装命令（原样透传）
scripts/run_with_timeout.ps1 -TimeoutSec 3600 [-TeardownGraceSec 120] [-Tag myrun] [-LogDir logs\wrapper] -- python -m pytest tests/ -q
scripts/run_with_timeout.ps1 -TimeoutSec 7200 -Tag 172b-urban -- python scripts/run_172b_ch100_climb.py --to 100
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `-TimeoutSec` | 3600 | 硬超时（秒）。超时即杀进程树并判 TIMEOUT |
| `-TeardownGraceSec` | 120 | 宽限期：检测到 pytest 完整通过摘要后，再等进程自然退出的秒数；超出判 `PASS_WITH_TEARDOWN_TIMEOUT` 并杀树 |
| `-Tag` | 时间戳 | 日志文件名片段 |
| `-LogDir` | `logs\wrapper` | 输出日志目录（自动创建） |
| `--` 后参数 | 必填 | 被包装命令与参数（透传执行，不经 cmd 字符串拼接，避免引号转义问题） |

### 2. 执行模型

- `Start-Process -PassThru` 直接启动目标命令（记录 PID），stdout/stderr 分别重定向到 `<LogDir>/<Tag>-<timestamp>.out.log / .err.log`，同时 tee 到 console（用 `Get-Content -Wait` 或周期性读取，保持可见性）。
  - **为什么用 `Start-Process` 而非 V5 协议字面的 `Start-Job`**：语义相同（独立进程 + 硬超时 + 输出捕获），但 `Start-Process -PassThru` 直接返回被包装命令的 PID，超时时的进程树清理（`taskkill /T`）精确可控；`Start-Job` 多一层 PowerShell 宿主，孙进程树更深、清理边界更模糊。这是历史 wrapper 不杀孙进程缺陷的直接修正。
- 主循环轮询（每 2-5s）：进程是否退出 / 是否超 `-TimeoutSec` / out.log 尾部是否出现 pytest 完整通过摘要（正则 `\d+ passed` 且该行不含 `failed|error`）。
- **退出**：读取进程退出码 → 判定标记输出。
- **超硬超时**：先尝试 `Stop-Process` 主 PID，再 `taskkill /PID <pid> /T /F` **杀整棵进程树**（修历史 wrapper 不杀孙进程的缺陷）；只杀本 wrapper 启动的 PID 树，不碰无关进程（V5 协议 §7）。
- **超宽限期**（摘要已过但进程不退出）：同上杀树，标记 `PASS_WITH_TEARDOWN_TIMEOUT`，退出码 0（按 V5 §5 语义：断言通过，teardown 卡住不算失败）。

### 3. 标准判定标记（输出到 stdout 与 meta 文件）

| 标记 | 含义 | 退出码 |
|---|---|---|
| `WRAPPER_RESULT=PASS_NORMAL_EXIT` | 命令成功且进程正常退出（pytest 场景含断言通过） | 0 |
| `WRAPPER_RESULT=PASS_WITH_TEARDOWN_TIMEOUT` | pytest 完整通过摘要已见，进程超宽限期未退出（断言通过，teardown 卡住） | 0 |
| `WRAPPER_RESULT=FAIL_NONZERO_EXIT` | 命令非零退出（对应 V5 协议的 `PYTEST_NONZERO_OR_UNKNOWN`，通用化命名） | 原退出码 |
| `WRAPPER_RESULT=TIMEOUT_WITHOUT_PASS_SUMMARY` | 硬超时且未见通过摘要（与 V5 协议标记同名） | 124 |

meta 文件记录：命令行、PID、起止时间、退出码、标记——与 V5 协议 §4 的字段对齐。

### 4. 与 173/176 的关系（文档中写清，避免语义回退）

173 修复后正常路径进程应在结果落盘后数秒内自然退出（实证 2.5s）；wrapper 的宽限期默认值 120s 远高于此。**`PASS_WITH_TEARDOWN_TIMEOUT` 在 173 之后应近似零触发**；若实跑中再次出现该标记，视为新的挂死线索，必须记录并上报（不得默默通过）——在 wrapper 输出中加一行引导语。

## 验证

### 自检测试矩阵（脚本自检模式或手动逐项，全部为本地无 API 命令）

| # | 场景 | 命令（示例） | 预期标记 |
|---|---|---|---|
| 1 | 快速成功 | `-- python -c "print('ok')"` | `PASS_NORMAL_EXIT`，退出码 0 |
| 2 | 快速失败 | `-- python -c "import sys; sys.exit(3)"` | `FAIL_NONZERO_EXIT`，退出码 3 |
| 3 | 硬超时杀树 | `-TimeoutSec 5 -- python -c "import subprocess,time; subprocess.Popen(['python','-c','import time; time.sleep(300)']); time.sleep(300)"` | `TIMEOUT_WITHOUT_PASS_SUMMARY`，退出码 124；**父子两棵 python 均被杀死**（`Get-Process` 复核） |
| 4 | 摘要已过 + 挂死 | `-TeardownGraceSec 3 -- python -c "print('73 passed'); import time; time.sleep(300)"`（或落一个小脚本打印 `73 passed` 后 sleep） | `PASS_WITH_TEARDOWN_TIMEOUT`，退出码 0；进程树被杀 |
| 5 | pytest 真跑（快子集） | `-- python -m pytest tests/test_173_pipeline_cleanup.py -q` | `PASS_NORMAL_EXIT` |

### 实跑验收（V9-README 176 验收要点）

- 用 wrapper 跑一次 scifi `--end 1` 短窗口实跑（`-- python scripts/run_172a7_genre_validation.py --templates scifi --end 1`）：进程自然退出、`PASS_NORMAL_EXIT`、成本遥测行落库正常（与 175 兼容）。
- 全量 `python -m pytest tests/ -q` 与 `ruff check src/ tests/` 绿（本 Task 不动 src/，仅新增脚本与文档，预期零回归）。

## 出口标准

1. `scripts/run_with_timeout.ps1` 落地，四档标记 + 进程树清理 + 日志落盘；
2. 自检测试矩阵 5 项全过（进程树复核证据落盘）；
3. scifi `--end 1` 实跑验收通过；
4. README FAQ 与 AGENTS.md 防卡条目更新指向本工具；V9-README 176 行翻正；
5. 本 Task 执行记录补录本文档。

## 撞墙路由

| 风险 | 触发信号 | 处理 |
|---|---|---|
| 进程树清理误伤 | 自检 #3 发现无关 python 进程被杀 | 严格只杀 `Start-Process -PassThru` 返回 PID 的 `taskkill /T` 树；复核父链 |
| PowerShell 版本差异 | `Start-Process -Wait` 与 `-PassThru` 组合行为差异（PS 5.1 vs 7+） | 显式检测 `$PSVersionTable.PSVersion`，文档声明支持范围；优先兼容 5.1 |
| tee 输出与文件竞争 | `Get-Content -Wait` 锁住 out.log 导致被包装命令写失败 | 改用共享读（`Get-Content -Wait -ReadCount 0` 或周期 `Get-Content -Tail`） |
| pytest 摘要误判 | 输出含 "1 failed, 73 passed" 被误判通过 | 正则要求摘要行不含 `failed|error`；宁可判 UNKNOWN 不误判 PASS |

## Out of Scope

- Git Bash 版 wrapper（Windows 主路径是 PowerShell；Git Bash 用户可 `powershell -File scripts/run_with_timeout.ps1 -- ...` 调用）；
- CI 集成（归 Task 181 统一设计）；
- 远程/分布式执行；
- 修改 V5 协议文本本身（归档文档不动，本 Task 是工具化其实现）。
