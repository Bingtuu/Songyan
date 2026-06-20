# run_songyan_chapter.ps1 — Task 119: 加固版 PowerShell wrapper
#
# 特性:
# - 检查业务完成标记 `project_pipeline.end`（不仅检查 exit code）
# - 明确的 WRAPPER_RESULT 结果码
# - 标准化的日志路径: logs/task<N>/songyan-<task>-<tag>-<timestamp>.out.log
# - 支持模拟超时测试
#
# 用法:
#   .\scripts\run_songyan_chapter.ps1 -ProjectId "proj-e74ef1e4" -Chapters "115-115" -ModeId "webnovel_intense" -Tag "ch115" -TimeoutSec 300
#
param(
    [string]$ProjectId = "proj-e74ef1e4",
    [string]$Chapters = "1-1",
    [string]$ModeId = "webnovel_intense",
    [string]$Tag = "default",
    [string]$TaskName = "task119",
    [int]$TimeoutSec = 300,
    [switch]$SimulateTimeout  # 用于测试: 模拟超时场景
)

$start = Get-Date
$timestamp = $start.ToString("yyyyMMdd-HHmmss")

# 标准化日志路径: logs/task<N>/songyan-<task>-<tag>-<timestamp>.*
$logDir = "c:\Vibe Project\Songyan\logs\$TaskName"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$outFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.out.log"
$errFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.err.log"
$metaFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.meta.txt"
$resultFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.result.txt"

$cmd = "songyan run --project-id `"$ProjectId`" --chapters `"$Chapters`" --mode-id `"$ModeId`" --auto-confirm"

# 写 meta 信息
"$start | START" | Out-File -FilePath $metaFile -Encoding UTF8
"$cmd" | Out-File -FilePath $metaFile -Append -Encoding UTF8

# 内部函数: 写结果文件
function Write-Result {
    param([string]$Result, [string]$Detail = "")
    $content = "WRAPPER_RESULT=$Result`n"
    if ($Detail) { $content += "DETAIL=$Detail`n" }
    $content += "TIMESTAMP=$(Get-Date -Format 'yyyyMMdd-HHmmss')`n"
    $content | Out-File -FilePath $resultFile -Encoding UTF8
}

# 启动子进程
$job = Start-Job -ScriptBlock {
    param($cmd, $outFile, $errFile, $metaFile, $logDir, $SimulateTimeout)

    Set-Location 'c:\Vibe Project\Songyan'
    $procStart = Get-Date
    "$procStart | PROCESS_START" | Out-File -FilePath $metaFile -Append -Encoding UTF8

    if ($SimulateTimeout) {
        # 模拟超时: 睡 timeout+1 秒
        Start-Sleep -Seconds 2
        Write-Output "SIMULATED_TIMEOUT for testing"
        return 124
    }

    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd `
        -NoNewWindow -PassThru -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile -Wait

    $procEnd = Get-Date
    "$procEnd | PROCESS_END (exit code: $($proc.ExitCode))" | Out-File -FilePath $metaFile -Append -Encoding UTF8
    "$($procEnd - $procStart) | DURATION_SEC" | Out-File -FilePath $metaFile -Append -Encoding UTF8

    Write-Output "PROCESS_EXIT=$($proc.ExitCode)"
    exit $proc.ExitCode
} -ArgumentList $cmd, $outFile, $errFile, $metaFile, $logDir, $SimulateTimeout

# 等待 Job，超时则停止
$done = Wait-Job $job -Timeout $TimeoutSec
$output = Receive-Job $job -Keep
$text = ($output | Out-String)
Remove-Job $job -Force

# 写原始输出摘要
$text | Out-File -FilePath "$logDir\songyan-$TaskName-$Tag-$timestamp.output.txt" -Encoding UTF8

# 超时判定
if ($done -eq $null) {
    # 真实超时: Job 仍在运行
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force

    # 检查 stdout 是否已有 project_pipeline.end（业务实际已完成）
    $pipelineEndFound = $text -match "project_pipeline\.end"

    if ($pipelineEndFound) {
        Write-Output "WRAPPER_RESULT=PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT"
        Write-Output "TIMEOUT_BUT_PIPELINE_END_FOUND=true"
        Write-Output "NOTE=业务完成，但 PowerShell Job 在 ${TimeoutSec}s 内未退出"
        Write-Result "PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT" "pipeline_end_found=true timeout=${TimeoutSec}s"
    } else {
        Write-Output "WRAPPER_RESULT=FAIL_TIMEOUT"
        Write-Output "TIMEOUT_BUT_PIPELINE_END_FOUND=false"
        Write-Result "FAIL_TIMEOUT" "pipeline_end_found=false timeout=${TimeoutSec}s"
    }
    Write-Output $text
    exit 124
}

# Job 在超时内完成 — 分析结果
$exitMatch = $text -match "PROCESS_EXIT=(\d+)"
$exitCode = if ($exitMatch) { [int]$matches[1] } else { -1 }

$pipelineEndFound = $text -match "project_pipeline\.end"
$finalStatusMatch = $text -match "final_status=(\w+)"
$finalStatus = if ($finalStatusMatch) { $matches[1] } else { "unknown" }

# 正常退出且业务完成
if ($exitCode -eq 0 -and $pipelineEndFound) {
    $detail = "exit=0 pipeline_end=found final_status=${finalStatus}"
    Write-Output "WRAPPER_RESULT=PASS_NORMAL_EXIT"
    Write-Output "PIPELINE_END_FOUND=true"
    Write-Result "PASS_NORMAL_EXIT" $detail
    Write-Output $text
    exit 0
}

# 业务完成但 exit 非 0
if ($pipelineEndFound -and $exitCode -ne 0) {
    $detail = "exit=${exitCode} pipeline_end=found final_status=${finalStatus}"
    Write-Output "WRAPPER_RESULT=WARN_BUSINESS_DONE_WITH_ERROR"
    Write-Output "PIPELINE_END_FOUND=true"
    Write-Result "WARN_BUSINESS_DONE_WITH_ERROR" $detail
    Write-Output $text
    exit $exitCode
}

# 退出码 0 但无 project_pipeline.end
if ($exitCode -eq 0 -and -not $pipelineEndFound) {
    Write-Output "WRAPPER_RESULT=WARN_NO_PIPELINE_END"
    Write-Output "PIPELINE_END_FOUND=false"
    Write-Result "WARN_NO_PIPELINE_END" "exit=0 pipeline_end=not_found"
    Write-Output $text
    exit 0
}

# 其他非零退出码
Write-Output "WRAPPER_RESULT=FAIL_NONZERO_EXIT"
Write-Output "PIPELINE_END_FOUND=$pipelineEndFound"
Write-Output "EXIT_CODE=$exitCode"
Write-Result "FAIL_NONZERO_EXIT" "exit=${exitCode} pipeline_end=$pipelineEndFound final_status=${finalStatus}"
Write-Output $text
exit $exitCode
