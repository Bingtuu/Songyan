# Task 114b: Phase 1 重跑 Ch102-Ch110

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **依赖**: Task 114a (Settlement 事实源契约修复) 已完成
> **预计工作量**: 1-2 天

---

## Goal

在 Task 114a 修复了 Settlement 事实源契约缺陷（`old_value` 代码回填、`quote_filter` 角色名校验、run logger 多维度判定、后处理触发收紧）后，先通过 Ch103 单点回放验证修复有效性，再重跑 Phase 1 全量 Ch102-Ch110，确认修复在 Ch101 之外的章节同样有效，无新的 settlement/convergence 阻断，为 Task 114c 长跑奠定稳定基线。

## Context

Task 114 Phase 1 首次执行（`run-5105e24b`）时：
- Ch102 成功完成
- Ch103 在 `settlement_review` 阶段因 `old_value` mismatch 和 `quote_filter` 内部 ID 误杀触发阻断
- Ch104-Ch110 未继续执行

Task 114a 已完成以下修复：
1. **P0**: `SettlementExtractor._validate.py` - `old_value` 由代码从 DB 事实源回填，不再依赖 LLM 精确复现
2. **P0**: `SettlementExtractor._quote_filter.py` - 使用角色名替代内部 `character_id` 做关键词校验
3. **P1**: `_run_logger.py` - `settlement_success` 多维度联合判定，严禁仅依赖单一标志位
4. **P1**: `_nodes.py` - 收紧后处理触发条件，仅在本次 settlement + accept 事务成功后触发

并新增 6 个 Ch103 回归测试，全量回归 1665 passed。

## 执行顺序（必须按序）

### 1. Ch103 单点回放验证（优先）

**目标**: 确认 `run-5105e24b` 暴露的 settlement `old_value` mismatch 不再阻断，且 accepted、settlement、summary 三者一致。

```bash
songyan run --project-id proj-e74ef1e4 --chapters 103-103 --mode-id webnovel_intense --auto-confirm
```

**验收标准**:
- [ ] Ch103 完成 `accepted` 状态
- [ ] `settlement_success=true`，无 `old_value` mismatch 错误
- [ ] `quote_filter` 日志显示使用角色名而非内部 ID
- [ ] `summary_success=true`
- [ ] 无事实源污染（`accepted_version_id` 不指向 abandoned）

### 2. Phase 1 全量重跑 Ch102-Ch110

**目标**: 确认 Task 113 的收敛回滚修复和 Task 114a 的 settlement 修复在 Ch101 之外的章节同样有效，无新的 settlement/convergence 阻断。

```bash
songyan run --project-id proj-e74ef1e4 --chapters 102-110 --mode-id webnovel_intense --auto-confirm
```

**验收标准**:
- [ ] Ch102-Ch110 完成率 >= 80%
- [ ] QG 通过率 >= 60%
- [ ] 每章 `budget_used <= 1.0`
- [ ] 无连续 2 章 `settlement_success=false`
- [ ] 无 `old_value` mismatch 复发
- [ ] 无 `quote_filter` 大量清空 CharacterUpdate quote

### 3. 强制检查清单（每步完成后执行）

| 检查项 | Ch103 回放 | Phase 1 全量 |
|--------|:----------:|:------------:|
| JSONL `success` 字段状态正常 | ⬜ | ⬜ |
| `accepted_version_id` 无指向 abandoned | ⬜ | ⬜ |
| 每章 settlement + summary 已写入 | ⬜ | ⬜ |
| `budget_used` 趋势稳定，无异常突增 | ⬜ | ⬜ |
| 无残留 python/songyan 进程 | ⬜ | ⬜ |
| 无熔断条件触发 | ⬜ | ⬜ |

## 熔断条件（任一触发即停机）

| 熔断条件 | 判定标准 | 停机后动作 |
|----------|----------|-----------|
| **Convergence + Settlement 双失败** | 任意一章 `convergence_failed=true` 且 `skip_settlement=true` | 停止后续章节，分析是否为 Task 113 同类问题 |
| **Settlement 事实源失败复发** | 任意一章出现 `old_value` mismatch、quote_filter 大量清空 CharacterUpdate quote、或 `settlement.validation_failed` | 停止后续章节，回到 Task 114a 修复 |
| **连续 Settlement 失败** | 连续 2 章 `settlement_success=false`（不含明确且预期的人审状态） | 同上，检查是否为系统性 settlement 阻断 |
| **硬超时** | 单段运行时间超过 4 小时（14400 秒） | 按 AGENTS.md 防卡协议判定 |
| **事实源污染** | 出现 `accepted_version_id` 指向 abandoned 版本、或 accepted 后无 settlement/summary 且非明确 skip | 立即停止，拆分 P0 修复任务 |
| **Budget 硬门禁突破** | 任意一章 `budget_used > 1.0` 且未触发 ContextEmergency 阻断 | 记录并分析，若连续出现则停机 |

## Windows 防卡协议（强制）

所有长跑命令必须使用 PowerShell Job + 硬超时包装，stdout/stderr 落盘到 `logs/task114/`：

```powershell
# 示例：Ch103 单点回放
$logPrefix = "songyan-ch103-replay-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$outLog = "logs/task114/$logPrefix.out.log"
$errLog = "logs/task114/$logPrefix.err.log"
$metaLog = "logs/task114/$logPrefix.meta.txt"

$job = Start-Job -ScriptBlock {
    param($outLog, $errLog)
    Set-Location 'c:\Vibe Project\Songyan'
    $ErrorActionPreference = 'Continue'
    & songyan run --project-id proj-e74ef1e4 --chapters 103-103 --mode-id webnovel_intense --auto-confirm > $outLog 2> $errLog
    Write-Output "SONGYAN_PROCESS_EXIT=$LASTEXITCODE"
    exit $LASTEXITCODE
} -ArgumentList $outLog, $errLog

# 硬超时 4 小时
$timeoutSeconds = 14400
$done = Wait-Job $job -Timeout $timeoutSeconds
$output = Receive-Job $job -Keep
$text = ($output | Out-String)
Write-Output $text

# 记录元数据
@"
Command: songyan run --project-id proj-e74ef1e4 --chapters 103-103 --mode-id webnovel_intense --auto-confirm
StartTime: $(Get-Date -Format 'o')
TimeoutSeconds: $timeoutSeconds
Completed: $($done -ne $null)
"@ | Out-File -FilePath $metaLog -Encoding utf8

if ($done -eq $null) {
    Stop-Job $job
    Start-Sleep -Seconds 2
    $more = Receive-Job $job
    if ($more) {
        Write-Output ($more | Out-String)
        $text += ($more | Out-String)
    }
    Remove-Job $job -Force
    # 检查 JSONL 是否显示完成
    $jsonlPath = Get-ChildItem logs/chapter_runs/*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($jsonlPath -and (Get-Content $jsonlPath.FullName | Select-String '"success":')) {
        Write-Output "WRAPPER_RESULT=TIMEOUT_AFTER_COMPLETION"
        exit 0
    }
    Write-Output "WRAPPER_RESULT=HARD_TIMEOUT"
    exit 1
}

Remove-Job $job -Force
Write-Output "WRAPPER_RESULT=COMPLETED"
exit 0
```

## 验收标准

| 指标 | 目标 |
|------|------|
| Ch103 回放 | accepted、settlement、summary 一致，无 `old_value` mismatch |
| Ch102-Ch110 完成率 | >= 80% |
| QG 通过率 | >= 60% |
| `budget_used` | 每章 <= 1.0 |
| 熔断触发 | 0 次（允许 1 次诊断后修复） |
| 事实源污染 | 0 个 |
| `settlement_success=false` 连续次数 | < 2 |

## 出口条件

Ch102-Ch110 完成率达标，无连续 settlement 阻断，无 accepted 指向 abandoned，方可进入 Task 114c。

## 参考文档

- `tasks/114a-settlement-fact-source-contract-fix-DONE.md` — Task 114a 修复完成文档
- `archive/v5/plans/114-ch101-ch150-streaming-validation.md` — Task 114 umbrella 历史规划稿
- `logs/chapter_runs/run-5105e24b.jsonl` — Ch103 失败基线
- `AGENTS.md` —
