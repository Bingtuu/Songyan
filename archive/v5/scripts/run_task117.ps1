param(
    [string]$ProjectId = "proj-e74ef1e4",
    [string]$Chapter = "115",
    [string]$ModeId = "webnovel_intense",
    [string]$Tag = "ch115"
)

$start = Get-Date
$timestamp = $start.ToString("yyyyMMdd-HHmmss")
$logDir = "c:\Vibe Project\Songyan\logs\task117"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$outFile = "$logDir\songyan-117-$Tag-$timestamp.out.log"
$errFile = "$logDir\songyan-117-$Tag-$timestamp.err.log"
$metaFile = "$logDir\songyan-117-$Tag-$timestamp.meta.txt"

$cmd = "songyan run --project-id $ProjectId --chapters $Chapter-$Chapter --mode-id $ModeId --auto-confirm"

$job = Start-Job -ScriptBlock {
    param($cmd, $outFile, $errFile, $metaFile, $logDir)
    Set-Location 'c:\Vibe Project\Songyan'
    $startTime = Get-Date
    "$startTime | START" | Out-File -FilePath $metaFile -Encoding UTF8
    "$cmd" | Out-File -FilePath $metaFile -Append -Encoding UTF8

    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -NoNewWindow -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile -Wait

    $endTime = Get-Date
    "$endTime | END (exit code: $($proc.ExitCode))" | Out-File -FilePath $metaFile -Append -Encoding UTF8
    "$($endTime - $startTime) | DURATION" | Out-File -FilePath $metaFile -Append -Encoding UTF8

    Write-Output "PROCESS_EXIT=$($proc.ExitCode)"
    exit $proc.ExitCode
} -ArgumentList $cmd, $outFile, $errFile, $metaFile, $logDir

$done = Wait-Job $job -Timeout 300
$output = Receive-Job $job -Keep
$text = ($output | Out-String)
Remove-Job $job -Force

$text | Out-File -FilePath "$logDir\songyan-117-$Tag-$timestamp.result.txt" -Encoding UTF8

if ($done -eq $null) {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force
    Write-Output "WRAPPER_RESULT=TIMEOUT_AFTER_300S"
    Write-Output $text
    exit 124
}

if ($text -match "PROCESS_EXIT=0") {
    Write-Output "WRAPPER_RESULT=PASS"
    exit 0
} elseif ($text -match "PROCESS_EXIT=1") {
    Write-Output "WRAPPER_RESULT=FAIL"
    exit 1
} else {
    Write-Output "WRAPPER_RESULT=UNKNOWN_EXIT"
    Write-Output $text
    exit 1
}