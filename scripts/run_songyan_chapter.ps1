# run_songyan_chapter.ps1 - hardened PowerShell wrapper
#
# Features:
# - Checks business completion marker project_pipeline.end, not only exit code.
# - Writes explicit WRAPPER_RESULT result codes.
# - Uses standardized log paths: logs/task<N>/songyan-<task>-<tag>-<timestamp>.*
# - Avoids non-ASCII strings so Windows PowerShell 5 can parse UTF-8 files safely.
#
# Usage:
#   .\scripts\run_songyan_chapter.ps1 -ProjectId "proj-e74ef1e4" -Chapters "115-115" -ModeId "webnovel_intense" -Tag "ch115" -TimeoutSec 300
#
param(
    [string]$ProjectId = "proj-e74ef1e4",
    [string]$Chapters = "1-1",
    [string]$ModeId = "webnovel_intense",
    [string]$Tag = "default",
    [string]$TaskName = "task119",
    [int]$TimeoutSec = 300,
    [int]$BusinessDoneGraceSec = 30,
    [switch]$SimulateTimeout
)

$start = Get-Date
$timestamp = $start.ToString("yyyyMMdd-HHmmss")

$logDir = "c:\Vibe Project\Songyan\logs\$TaskName"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$outFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.out.log"
$errFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.err.log"
$metaFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.meta.txt"
$resultFile = "$logDir\songyan-$TaskName-$Tag-$timestamp.result.txt"

$argList = @(
    "run",
    "--project-id", $ProjectId,
    "--chapters", $Chapters,
    "--mode-id", $ModeId,
    "--auto-confirm"
)
$cmd = "songyan " + ($argList -join " ")

"$start | START" | Out-File -FilePath $metaFile -Encoding UTF8
"$cmd" | Out-File -FilePath $metaFile -Append -Encoding UTF8

function Write-Result {
    param([string]$Result, [string]$Detail = "")
    $content = "WRAPPER_RESULT=$Result`n"
    if ($Detail) { $content += "DETAIL=$Detail`n" }
    $content += "TIMESTAMP=$(Get-Date -Format 'yyyyMMdd-HHmmss')`n"
    $content | Out-File -FilePath $resultFile -Encoding UTF8
}

$procStart = Get-Date
"$procStart | PROCESS_START" | Out-File -FilePath $metaFile -Append -Encoding UTF8

$exitCode = -1
$timedOut = $false
$businessDoneTimeout = $false
$businessDoneAt = $null

if ($SimulateTimeout) {
    "SIMULATED_TIMEOUT for testing" | Out-File -FilePath $outFile -Encoding UTF8
    $timedOut = $true
} else {
    $proc = Start-Process -FilePath "songyan" -ArgumentList $argList `
        -NoNewWindow -PassThru -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile

    "PROCESS_ID=$($proc.Id)" | Out-File -FilePath $metaFile -Append -Encoding UTF8

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ($true) {
        if ($proc.HasExited) {
            $exitCode = $proc.ExitCode
            break
        }

        $currentText = if (Test-Path $outFile) { Get-Content -Raw $outFile } else { "" }
        if ($businessDoneAt -eq $null -and $currentText -match "project_pipeline\.end") {
            $businessDoneAt = Get-Date
            "BUSINESS_DONE_DETECTED=$businessDoneAt" |
                Out-File -FilePath $metaFile -Append -Encoding UTF8
        }

        if ($businessDoneAt -ne $null) {
            $elapsedAfterDone = ((Get-Date) - $businessDoneAt).TotalSeconds
            if ($elapsedAfterDone -ge $BusinessDoneGraceSec) {
                $timedOut = $true
                $businessDoneTimeout = $true
                try {
                    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                    "PROCESS_KILLED_AFTER_BUSINESS_DONE" |
                        Out-File -FilePath $metaFile -Append -Encoding UTF8
                } catch {
                    "PROCESS_KILL_FAILED=$($_.Exception.Message)" |
                        Out-File -FilePath $metaFile -Append -Encoding UTF8
                }
                break
            }
        }

        if ((Get-Date) -ge $deadline) {
            $timedOut = $true
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                "PROCESS_KILLED_AFTER_TIMEOUT" |
                    Out-File -FilePath $metaFile -Append -Encoding UTF8
            } catch {
                "PROCESS_KILL_FAILED=$($_.Exception.Message)" |
                    Out-File -FilePath $metaFile -Append -Encoding UTF8
            }
            break
        }

        Start-Sleep -Seconds 2
    }
}

$procEnd = Get-Date
"$procEnd | PROCESS_END (exit code: $exitCode timeout: $timedOut)" | Out-File -FilePath $metaFile -Append -Encoding UTF8
"$($procEnd - $procStart) | DURATION_SEC" | Out-File -FilePath $metaFile -Append -Encoding UTF8

$outText = if (Test-Path $outFile) { Get-Content -Raw $outFile } else { "" }
$errText = if (Test-Path $errFile) { Get-Content -Raw $errFile } else { "" }
$text = "$outText`n$errText"
$text | Out-File -FilePath "$logDir\songyan-$TaskName-$Tag-$timestamp.output.txt" -Encoding UTF8

$pipelineEndFound = $text -match "project_pipeline\.end"
$finalStatusMatch = $text -match "final_status=(\w+)"
$finalStatus = if ($finalStatusMatch) { $matches[1] } else { "unknown" }

if ($timedOut) {
    if ($pipelineEndFound) {
        if ($finalStatus -ne "completed") {
            $detail = "exit=${exitCode} pipeline_end=found final_status=${finalStatus} business_done_timeout=${businessDoneTimeout}"
            Write-Output "WRAPPER_RESULT=WARN_BUSINESS_DONE_WITH_ERROR"
            Write-Output "PIPELINE_END_FOUND=true"
            Write-Result "WARN_BUSINESS_DONE_WITH_ERROR" $detail
            exit 1
        }
        Write-Output "WRAPPER_RESULT=PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT"
        Write-Output "TIMEOUT_BUT_PIPELINE_END_FOUND=true"
        Write-Output "NOTE=Business completed but wrapper timed out after ${TimeoutSec}s"
        Write-Result "PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT" "pipeline_end_found=true timeout=${TimeoutSec}s business_done_timeout=${businessDoneTimeout}"
        exit 0
    }
    Write-Output "WRAPPER_RESULT=FAIL_TIMEOUT"
    Write-Output "TIMEOUT_BUT_PIPELINE_END_FOUND=false"
    Write-Result "FAIL_TIMEOUT" "pipeline_end_found=false timeout=${TimeoutSec}s"
    exit 124
}

if ($exitCode -eq 0 -and $pipelineEndFound) {
    $detail = "exit=0 pipeline_end=found final_status=${finalStatus}"
    Write-Output "WRAPPER_RESULT=PASS_NORMAL_EXIT"
    Write-Output "PIPELINE_END_FOUND=true"
    Write-Result "PASS_NORMAL_EXIT" $detail
    Write-Output $text
    exit 0
}

if ($pipelineEndFound -and $exitCode -ne 0) {
    $detail = "exit=${exitCode} pipeline_end=found final_status=${finalStatus}"
    Write-Output "WRAPPER_RESULT=WARN_BUSINESS_DONE_WITH_ERROR"
    Write-Output "PIPELINE_END_FOUND=true"
    Write-Result "WARN_BUSINESS_DONE_WITH_ERROR" $detail
    Write-Output $text
    exit $exitCode
}

if ($exitCode -eq 0 -and -not $pipelineEndFound) {
    Write-Output "WRAPPER_RESULT=WARN_NO_PIPELINE_END"
    Write-Output "PIPELINE_END_FOUND=false"
    Write-Result "WARN_NO_PIPELINE_END" "exit=0 pipeline_end=not_found"
    Write-Output $text
    exit 0
}

Write-Output "WRAPPER_RESULT=FAIL_NONZERO_EXIT"
Write-Output "PIPELINE_END_FOUND=$pipelineEndFound"
Write-Output "EXIT_CODE=$exitCode"
Write-Result "FAIL_NONZERO_EXIT" "exit=${exitCode} pipeline_end=$pipelineEndFound final_status=${finalStatus}"
Write-Output $text
exit $exitCode
