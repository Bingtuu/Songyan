<#
run_with_timeout.ps1 - generic Windows anti-hang wrapper (Task 176, V9.1)

Purpose
    Tool-ifies the V5 Windows anti-hang protocol (PowerShell + hard timeout +
    standard verdict markers) for ANY command, not just `songyan run`.
    It is the unattended-run fuse: bounds unknown hangs to -TimeoutSec, cleans
    up the whole child process tree, and writes machine-readable verdicts.

Usage
    powershell -File scripts\run_with_timeout.ps1 -TimeoutSec 3600 python -m pytest tests/ -q
    powershell -File scripts\run_with_timeout.ps1 -TimeoutSec 7200 -Tag 172b-urban `
        -SuccessMarkerRegex "project_pipeline\.end" python scripts\run_172b_ch100_climb.py --to 100
    powershell -File scripts\run_with_timeout.ps1 -SelfTest
    # A `--` separator between options and command is accepted (stripped by
    # this script) and works both via -File and inside a PowerShell session:
    & .\scripts\run_with_timeout.ps1 -TimeoutSec 3600 -- python -m pytest tests/ -q

Options (space-separated values, case-insensitive names)
    -TimeoutSec <int>        Hard timeout in seconds (default 3600). On expiry the
                             whole child process tree is killed -> TIMEOUT verdict.
    -TeardownGraceSec <int>  Grace period (default 120) after an ENABLED pass
                             marker is seen; if the process still has not exited,
                             the tree is killed -> PASS_WITH_TEARDOWN_TIMEOUT.
    -Tag <string>            Log file name fragment (default: run-<timestamp>).
    -LogDir <string>         Log directory (default logs\wrapper, auto-created).
    -DetectPytestSummary     Enable pytest pass-summary detection. AUTO-ENABLED
                             when the wrapped command shape is `python -m pytest`
                             (python / py / full path / venv python). For any
                             other command shape it stays OFF, so a random
                             command printing "73 passed" is never misjudged.
    -SuccessMarkerRegex <s>  Extra business completion marker (default empty =
                             disabled), matched per output line.
    -SelfTest                Run the built-in 9-case local self-test matrix and
                             write evidence to .tmp\176_selftest\ .
    [--] <command> [args...] The wrapped command: everything after the first
                             non-option token (or after the optional `--`
                             sentinel) is passed through VERBATIM - child args
                             like -c, -q, -m, --to are never stolen by wrapper
                             option parsing (this script has no param() block;
                             see the note above the main section for why).

Verdict markers (stdout WRAPPER_RESULT=... and meta file field)
    PASS_NORMAL_EXIT               exit 0   command exited normally with code 0
    PASS_WITH_TEARDOWN_TIMEOUT     exit 0   enabled pass marker seen, process did
                                            not exit within grace -> tree killed.
                                            Also emits ACTION_REQUIRED=investigate_teardown_hang
    FAIL_NONZERO_EXIT              exit = original code   (launch failure: code 1
                                            + launch_error meta field)
    TIMEOUT_WITHOUT_PASS_SUMMARY   exit 124 hard timeout, no pass summary seen

Relation to Task 173
    After the 173 fix, a healthy run exits within seconds of flushing results
    (measured ~2.5s); the 120s default grace is far above that. Therefore
    PASS_WITH_TEARDOWN_TIMEOUT should be near-zero post-173: if it fires in a
    real run, treat it as a NEW hang lead, record it, and report it - do not
    swallow it as a green light.

Implementation notes
    - Start-Process -PassThru starts the command directly (no cmd.exe /c), with
      stdout/stderr redirected to <LogDir>\<Tag>-<timestamp>.out.log/.err.log.
    - Quote-Argument / Join-CommandArguments handle spaces, quotes and
      semicolons for PS 5.1 argument passing.
    - Console tee uses shared-read (FileShare.ReadWrite) + offset incremental
      tail; no Get-Content -Wait, no full re-dump of the logs.
    - Kill order: taskkill /PID <pid> /T /F first (kills the whole tree,
      including grandchildren); Stop-Process -Force on the root is only a
      fallback, followed by a child sweep (ParentProcessId = root, taskkill /T
      per child) so fallback-path orphans are not left behind. Only the PID
      tree started by THIS wrapper is ever touched.
    - PID-reuse guard: the child's start time is recorded at launch
      ($proc.StartTime, CIM CreationDate fallback) and verified against the
      live process's CreationDate (1s tolerance) before any kill; mismatch
      refuses the kill and reports tree_kill_status=not_attempted.
    - Cleanup honesty in meta: root_killed=true/false and
      tree_kill_status=full/partial/failed/not_attempted (full = root dead and
      no surviving children). deadline_hit=grace|hard records which deadline
      fired for PASS_WITH_TEARDOWN_TIMEOUT. After killing, PIDs are re-checked
      via Get-CimInstance Win32_Process.
    - The main loop is wrapped in try/catch/finally: on a wrapper-internal
      error the child tree is best-effort killed, the result fails closed
      (FAIL_NONZERO_EXIT/1 + wrapper_error meta field), the Win32 handle is
      always closed, and the meta file is always written.
    - Compatible with Windows PowerShell 5.1 (developed/tested on 5.1.26100).
      Source is ASCII-only so PS 5.1 parses it safely without a BOM; meta files
      are written with -Encoding ascii (no BOM).
    - Exit code: PS 5.1's Start-Process object returns $null for ExitCode and
      Handle when streams are redirected, and .NET Framework's Process.ExitCode
      only works on the Process instance that started the process. Therefore
      the wrapper opens its own Win32 handle via OpenProcess (right after
      start) and reads the real exit code with GetExitCodeProcess. If the
      handle cannot be opened (process already gone), the wrapper fails closed:
      WRAPPER_RESULT=FAIL_NONZERO_EXIT, exit 1, meta exit_code_unavailable=true.
#>

# NOTE: no param() block, on purpose. The PowerShell parameter binder is
# unsafe for a pass-through command wrapper:
#   (a) under `powershell.exe -File`, the `--` sentinel is rejected by the
#       binder as an "ambiguous empty parameter name" before the script runs;
#   (b) parameter-name PREFIX matching steals child arguments: `-c` would
#       bind to a -Command parameter, `-v` to -Verbose, `-s`/`-d` are
#       ambiguous, `--to` can bind to -TimeoutSec, etc.
# Parsing $args manually (below, in the main section) is the only robust way
# to accept arbitrary wrapped commands identically from `powershell -File`
# and in-process (& / -Command) invocations. Empirically, both modes deliver
# every token raw into $args (in-process, `--` is consumed by the parser as
# the end-of-parameters marker; under -File it arrives literally and is
# stripped by this script).

$Script:WrapperVersion = "1.1.0"

# Win32 helpers: raw handle for liveness / real exit code (see header note).
if (-not ('WrapperNative' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class WrapperNative {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr OpenProcess(uint dwDesiredAccess, bool bInheritHandle, int dwProcessId);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool GetExitCodeProcess(IntPtr hProcess, out uint lpExitCode);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool CloseHandle(IntPtr hObject);
}
'@
}
$Script:SynchronizeOrQueryLimited = 0x00101000  # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION

# ---------------------------------------------------------------- helpers ---

function Quote-Argument {
    # Windows/MSVCRT command-line quoting for a single argument.
    param([AllowNull()][AllowEmptyString()][string]$Arg)
    if ([string]::IsNullOrEmpty($Arg)) { return '""' }
    if ($Arg -notmatch '[ \t"]') { return $Arg }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('"')
    $backslashes = 0
    foreach ($ch in $Arg.ToCharArray()) {
        if ($ch -eq '\') { $backslashes++; continue }
        if ($ch -eq '"') {
            [void]$sb.Append('\' * ($backslashes * 2 + 1))
            [void]$sb.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            [void]$sb.Append('\' * $backslashes)
            $backslashes = 0
        }
        [void]$sb.Append($ch)
    }
    if ($backslashes -gt 0) { [void]$sb.Append('\' * ($backslashes * 2)) }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Join-CommandArguments {
    param([string[]]$ArgList)
    $quoted = foreach ($a in $ArgList) { Quote-Argument $a }
    return ($quoted -join ' ')
}

function Test-PytestCommandShape {
    # Wide match: python / python3.x / py / full path / venv python, then `-m pytest`.
    param([string[]]$CmdLine)
    if ($CmdLine.Count -lt 3) { return $false }
    $leaf = [System.IO.Path]::GetFileName($CmdLine[0])
    if ($leaf -notmatch '^(python[\d.]*|py)(\.exe)?$') { return $false }
    return ($CmdLine[1] -eq '-m' -and $CmdLine[2] -eq 'pytest')
}

function Test-PassMarkerLine {
    param([string]$Line, [bool]$PytestEnabled, [string]$BusinessRegex)
    if ($PytestEnabled -and $Line -match '\d+ passed' -and $Line -notmatch 'failed|error|errors') {
        return 'pytest'
    }
    if (-not [string]::IsNullOrEmpty($BusinessRegex) -and $Line -match $BusinessRegex) {
        return 'business'
    }
    return $null
}

function New-TailState {
    param([string]$Path)
    return @{
        Path       = $Path
        Offset     = [long]0
        Decoder    = [System.Text.Encoding]::UTF8.GetDecoder()
        LineBuffer = ""
    }
}

function Read-Tail {
    # Shared-read incremental tail: reads only bytes appended since the last
    # call, tees them to the console, and returns newly COMPLETED lines.
    param([hashtable]$State, [switch]$Tee)
    $newLines = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path $State.Path)) { return $newLines }
    $fs = $null
    try {
        try {
            $fs = New-Object System.IO.FileStream($State.Path,
                [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
                ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete))
        } catch {
            # Transient sharing/IO hiccup: skip this poll cycle, retry next time.
            return $newLines
        }
        if ($fs.Length -lt $State.Offset) {
            # File was truncated/recreated: restart from the beginning.
            $State.Offset = [long]0
            $State.LineBuffer = ""
            $State.Decoder = [System.Text.Encoding]::UTF8.GetDecoder()
        }
        if ($fs.Length -gt $State.Offset) {
            [void]$fs.Seek($State.Offset, [System.IO.SeekOrigin]::Begin)
            $buffer = New-Object byte[] 65536
            $text = ""
            while ($true) {
                $read = $fs.Read($buffer, 0, $buffer.Length)
                if ($read -le 0) { break }
                $State.Offset += $read
                $charCount = $State.Decoder.GetCharCount($buffer, 0, $read, $false)
                $chars = New-Object char[] $charCount
                [void]$State.Decoder.GetChars($buffer, 0, $read, $chars, 0, $false)
                $text += New-Object string($chars, 0, $charCount)
            }
            if ($text.Length -gt 0) {
                if ($Tee) { Write-Host -NoNewline $text }
                $State.LineBuffer += $text
                while (($idx = $State.LineBuffer.IndexOf("`n")) -ge 0) {
                    $newLines.Add($State.LineBuffer.Substring(0, $idx).TrimEnd("`r"))
                    $State.LineBuffer = $State.LineBuffer.Substring($idx + 1)
                }
            }
        }
    } finally {
        if ($null -ne $fs) { $fs.Close() }
    }
    return $newLines
}

function Get-TailRemainder {
    # Final partial line (no trailing newline) after the process ended.
    param([hashtable]$State)
    $rem = $State.LineBuffer
    $State.LineBuffer = ""
    return $rem
}

function Test-ProcessAlive {
    param([int]$ProcessId)
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    return ($null -ne $p)
}

function Stop-ProcessTree {
    # Kill the tree rooted at the PID this wrapper started.
    #   1. PID-reuse guard: if the live process's CreationDate does not match
    #      the recorded child start time (1s tolerance), REFUSE to kill and
    #      report not_attempted - never kill a possibly-recycled PID.
    #   2. taskkill /T /F first (kills the whole tree incl. grandchildren).
    #   3. Fallback: Stop-Process -Force on the root, then sweep any surviving
    #      children (ParentProcessId = root) with taskkill /T per child, so
    #      fallback-path orphans are not silently left behind.
    # Returns RootKilled + Status (full/partial/failed/not_attempted) so the
    # meta file tells the truth about how complete the cleanup was:
    #   full          root dead AND no surviving children
    #   partial       root dead BUT some children survived
    #   failed        kill attempted, root still alive
    #   not_attempted no kill happened (already gone / PID-reuse refusal)
    # NOTE: PowerShell variable names are case-insensitive, so a local named
    # $detail would collide with the [ref]$Detail parameter (a [ref]-typed
    # variable writes through on assignment). The local must stay named $info.
    param([int]$ProcessId, [datetime]$ExpectedStartTime, [ref]$Detail)
    $info = ""
    $rootKilled = $false
    $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if ($null -ne $cim -and $ExpectedStartTime -ne [datetime]::MinValue) {
        $skew = [math]::Abs(($cim.CreationDate - $ExpectedStartTime).TotalSeconds)
        if ($skew -gt 1) {
            $info = "REFUSED: pid $ProcessId CreationDate=$($cim.CreationDate.ToString('o')) expected=$($ExpectedStartTime.ToString('o')) skew=$([math]::Round($skew, 2))s; possible PID reuse, not killing"
            $Detail.Value = $info
            return [PSCustomObject]@{ RootKilled = $false; Status = 'not_attempted' }
        }
    }
    if ($null -eq $cim) {
        $info = "root pid $ProcessId already gone before kill"
        $rootKilled = $true
    } else {
        $taskkillOut = & taskkill /PID $ProcessId /T /F 2>&1
        $taskkillExit = $LASTEXITCODE
        if ($taskkillExit -eq 0) {
            $info = "taskkill /PID $ProcessId /T /F ok"
        } else {
            $info = "taskkill exit=$taskkillExit ($($taskkillOut -join ' ')); fallback Stop-Process root"
            try {
                Stop-Process -Id $ProcessId -Force -ErrorAction Stop
                $info += "; Stop-Process ok"
            } catch {
                $info += "; Stop-Process failed: $($_.Exception.Message)"
            }
        }
        for ($i = 0; $i -lt 10; $i++) {
            if (-not (Test-ProcessAlive $ProcessId)) { $rootKilled = $true; break }
            Start-Sleep -Seconds 1
        }
        $info += "; root_pid_alive=$(-not $rootKilled)"
    }
    # Child sweep: any process still claiming this PID as parent (fallback-path
    # orphans or taskkill races). Kill each child's own subtree, then re-check.
    $survivors = @()
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        $cid = [int]$child.ProcessId
        & taskkill /PID $cid /T /F 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            try { Stop-Process -Id $cid -Force -ErrorAction Stop } catch { }
        }
        Start-Sleep -Milliseconds 500
        if (Test-ProcessAlive $cid) { $survivors += $cid }
    }
    if ($children.Count -gt 0) {
        $info += "; child_sweep=$($children.Count) found survivors=[$($survivors -join ',')]"
    }
    $status = 'failed'
    if ($rootKilled) {
        if ($survivors.Count -eq 0) { $status = 'full' } else { $status = 'partial' }
    }
    $Detail.Value = $info
    return [PSCustomObject]@{ RootKilled = $rootKilled; Status = $status }
}

# ------------------------------------------------------------------ core ---

function Invoke-WrappedCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Cmd,
        [int]$TimeoutSec = 3600,
        [int]$TeardownGraceSec = 120,
        [string]$Tag = "",
        [string]$LogDir = "logs\wrapper",
        [bool]$PytestSummaryEnabled = $false,
        [string]$BusinessMarkerRegex = ""
    )

    $startTime = Get-Date
    $timestamp = $startTime.ToString("yyyyMMdd-HHmmssfff")
    if ([string]::IsNullOrWhiteSpace($Tag)) { $Tag = "run-$timestamp" }
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    $outLog = Join-Path $LogDir "$Tag-$timestamp.out.log"
    $errLog = Join-Path $LogDir "$Tag-$timestamp.err.log"
    $metaFile = Join-Path $LogDir "$Tag-$timestamp.meta.txt"

    $exe = $Cmd[0]
    $cmdArgs = @()
    if ($Cmd.Count -gt 1) { $cmdArgs = $Cmd[1..($Cmd.Count - 1)] }
    $argString = Join-CommandArguments $cmdArgs
    $commandLine = Quote-Argument $exe
    if ($argString) { $commandLine = "$commandLine $argString" }

    $markerType = "none"
    if ($PytestSummaryEnabled) { $markerType = "pytest" }
    elseif (-not [string]::IsNullOrEmpty($BusinessMarkerRegex)) { $markerType = "business" }

    $childPid = $null
    $killResult = $null
    $killDetail = ""
    $launchError = ""
    $wrapperError = ""
    $passMarkerSeenAt = $null
    $deadlineHit = ""
    $result = ""
    $exitCode = 0
    $endTime = $null
    $nativeHandle = [IntPtr]::Zero
    $exitCodeUnavailable = $false
    $expectedStartTime = [datetime]::MinValue

    $proc = $null
    try {
        $proc = Start-Process -FilePath $exe -ArgumentList $argString -NoNewWindow -PassThru `
            -RedirectStandardOutput $outLog -RedirectStandardError $errLog -ErrorAction Stop
    } catch {
        $launchError = $_.Exception.Message
    }

    if ($null -eq $proc) {
        # Launch failure: no four-marker case covers this; report FAIL with code 1.
        $endTime = Get-Date
        $result = "FAIL_NONZERO_EXIT"
        $exitCode = 1
    } else {
        $childPid = $proc.Id
        # PS 5.1 quirk: the Start-Process object reports $null ExitCode/Handle when
        # streams are redirected. Open our own Win32 handle for the real exit code.
        $nativeHandle = [WrapperNative]::OpenProcess($Script:SynchronizeOrQueryLimited, $false, $childPid)
        # PID-reuse guard input: remember who our child is. $proc.StartTime can
        # also be unavailable under redirection; fall back to CIM CreationDate.
        $childStartTime = $null
        try { $childStartTime = $proc.StartTime } catch { $childStartTime = $null }
        if ($null -eq $childStartTime) {
            $cimStart = Get-CimInstance Win32_Process -Filter "ProcessId=$childPid" -ErrorAction SilentlyContinue
            if ($null -ne $cimStart) { $childStartTime = $cimStart.CreationDate }
        }
        if ($null -ne $childStartTime) { $expectedStartTime = $childStartTime }
        Write-Host "[wrapper] child_pid=$childPid timeout=${TimeoutSec}s grace=${TeardownGraceSec}s marker=$markerType"
        Write-Host "[wrapper] out=$outLog"

        $hardDeadline = $startTime.AddSeconds($TimeoutSec)
        $graceDeadline = $null
        $outTail = New-TailState $outLog
        $errTail = New-TailState $errLog
        $timedOut = $false
        $teardownTimeout = $false

        try {
            while ($true) {
                $newLines = @(Read-Tail $outTail -Tee) + @(Read-Tail $errTail -Tee)
                foreach ($line in $newLines) {
                    if ($null -eq $passMarkerSeenAt) {
                        $hit = Test-PassMarkerLine -Line $line -PytestEnabled $PytestSummaryEnabled -BusinessRegex $BusinessMarkerRegex
                        if ($null -ne $hit) {
                            $passMarkerSeenAt = Get-Date
                            $graceDeadline = $passMarkerSeenAt.AddSeconds($TeardownGraceSec)
                            Write-Host "[wrapper] pass marker detected ($hit) at $($passMarkerSeenAt.ToString('HH:mm:ss')); grace ${TeardownGraceSec}s"
                        }
                    }
                }

                if ($proc.HasExited) { break }

                $now = Get-Date
                if ($null -ne $graceDeadline) {
                    # Marker seen: kill at min(grace, hard) and record WHICH
                    # deadline fired so verdict/meta/NOTE tell the truth.
                    if ($now -ge $graceDeadline -or $now -ge $hardDeadline) {
                        $teardownTimeout = $true
                        if ($graceDeadline -le $hardDeadline) { $deadlineHit = 'grace' } else { $deadlineHit = 'hard' }
                        Write-Host "[wrapper] pass marker seen but process still alive (deadline_hit=$deadlineHit); killing tree $childPid"
                        $killResult = Stop-ProcessTree -ProcessId $childPid -ExpectedStartTime $expectedStartTime -Detail ([ref]$killDetail)
                        break
                    }
                } elseif ($now -ge $hardDeadline) {
                    $timedOut = $true
                    Write-Host "[wrapper] hard timeout ${TimeoutSec}s reached; killing tree $childPid"
                    $killResult = Stop-ProcessTree -ProcessId $childPid -ExpectedStartTime $expectedStartTime -Detail ([ref]$killDetail)
                    break
                }
                Start-Sleep -Seconds 2
            }

            # Final drain (flush anything written between the last poll and exit).
            Start-Sleep -Milliseconds 300
            $finalLines = @(Read-Tail $outTail -Tee) + @(Read-Tail $errTail -Tee)
            $remOut = Get-TailRemainder $outTail
            $remErr = Get-TailRemainder $errTail
            foreach ($line in ($finalLines + @($remOut) + @($remErr))) {
                if ([string]::IsNullOrEmpty($line)) { continue }
                if ($null -eq $passMarkerSeenAt -and $null -eq $killResult) {
                    $hit = Test-PassMarkerLine -Line $line -PytestEnabled $PytestSummaryEnabled -BusinessRegex $BusinessMarkerRegex
                    if ($null -ne $hit) { $passMarkerSeenAt = Get-Date }
                }
            }

            $endTime = Get-Date
            if ($teardownTimeout) {
                $result = "PASS_WITH_TEARDOWN_TIMEOUT"
                $exitCode = 0
            } elseif ($timedOut) {
                $result = "TIMEOUT_WITHOUT_PASS_SUMMARY"
                $exitCode = 124
            } else {
                $nativeExit = [uint32]0
                $gotExit = $false
                if ($nativeHandle -ne [IntPtr]::Zero) {
                    $gotExit = [WrapperNative]::GetExitCodeProcess($nativeHandle, [ref]$nativeExit)
                }
                if ($gotExit -and $nativeExit -ne 259) {
                    # 259 = STILL_ACTIVE; here the process has exited, so the code is final.
                    $exitCode = [int]$nativeExit
                    if ($exitCode -eq 0) { $result = "PASS_NORMAL_EXIT" } else { $result = "FAIL_NONZERO_EXIT" }
                } else {
                    # Handle lost the start race: fail closed, never guess PASS.
                    $exitCodeUnavailable = $true
                    $exitCode = 1
                    $result = "FAIL_NONZERO_EXIT"
                    Write-Host "[wrapper] WARNING: real exit code unavailable (handle lost); failing closed"
                }
            }
        } catch {
            # Wrapper-internal error: never leave the fuse open. Best-effort kill
            # the child tree, then fail closed. Meta is still written below.
            $wrapperError = $_.Exception.Message
            $endTime = Get-Date
            try {
                if (-not $proc.HasExited) {
                    Write-Host "[wrapper] internal error ($wrapperError); best-effort kill of tree $childPid"
                    $killResult = Stop-ProcessTree -ProcessId $childPid -ExpectedStartTime $expectedStartTime -Detail ([ref]$killDetail)
                }
            } catch { }
            $result = "FAIL_NONZERO_EXIT"
            $exitCode = 1
        } finally {
            if ($nativeHandle -ne [IntPtr]::Zero) {
                [void][WrapperNative]::CloseHandle($nativeHandle)
                $nativeHandle = [IntPtr]::Zero
            }
        }
    }

    $meta = [ordered]@{
        wrapper_version     = $Script:WrapperVersion
        tag                 = $Tag
        command_line        = $commandLine
        child_pid           = $(if ($null -ne $childPid) { "$childPid" } else { "" })
        start_time          = $startTime.ToString("o")
        end_time            = $endTime.ToString("o")
        duration_sec        = [math]::Round(($endTime - $startTime).TotalSeconds, 2)
        timeout_sec         = $TimeoutSec
        teardown_grace_sec  = $TeardownGraceSec
        pass_marker_type    = $markerType
        pass_marker_seen_at = $(if ($null -ne $passMarkerSeenAt) { $passMarkerSeenAt.ToString("o") } else { "" })
        root_killed         = $(if ($null -ne $killResult -and $killResult.RootKilled) { "true" } else { "false" })
        tree_kill_status    = $(if ($null -ne $killResult) { $killResult.Status } else { "not_attempted" })
        deadline_hit        = $deadlineHit
        exit_code           = $exitCode
        WRAPPER_RESULT      = $result
        out_log             = $outLog
        err_log             = $errLog
    }
    if ($killDetail) { $meta["kill_detail"] = $killDetail }
    if ($launchError) { $meta["launch_error"] = $launchError }
    if ($wrapperError) { $meta["wrapper_error"] = $wrapperError }
    if ($exitCodeUnavailable) { $meta["exit_code_unavailable"] = "true" }
    if ($result -eq "PASS_WITH_TEARDOWN_TIMEOUT") {
        $meta["ACTION_REQUIRED"] = "investigate_teardown_hang"
    }
    ($meta.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`r`n" |
        Out-File -FilePath $metaFile -Encoding ascii

    return [PSCustomObject]@{
        Result              = $result
        ExitCode            = $exitCode
        ChildPid            = $childPid
        RootKilled          = ($null -ne $killResult -and $killResult.RootKilled)
        TreeKillStatus      = $(if ($null -ne $killResult) { $killResult.Status } else { "not_attempted" })
        DeadlineHit         = $deadlineHit
        KillDetail          = $killDetail
        PassMarkerType      = $markerType
        PassMarkerSeenAt    = $passMarkerSeenAt
        MetaFile            = $metaFile
        OutLog              = $outLog
        ErrLog              = $errLog
        LaunchError         = $launchError
        WrapperError        = $wrapperError
        ExitCodeUnavailable = $exitCodeUnavailable
    }
}

# -------------------------------------------------------------- self-test ---

function Invoke-SelfTest {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $root = Join-Path $repoRoot ".tmp\176_selftest"
    if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }

    $caseLines = New-Object System.Collections.Generic.List[string]
    $allPass = $true

    Push-Location $repoRoot
    try {
        # CASE 1: quick success -> PASS_NORMAL_EXIT, exit 0
        $r1 = Invoke-WrappedCommand -Cmd @('python', '-c', "print('ok')") `
            -TimeoutSec 60 -Tag 'case1' -LogDir (Join-Path $root 'case1')
        $outText1 = if (Test-Path $r1.OutLog) { Get-Content $r1.OutLog -Raw } else { "" }
        $p1 = ($r1.Result -eq 'PASS_NORMAL_EXIT' -and $r1.ExitCode -eq 0 -and $outText1 -match 'ok')
        $caseLines.Add("CASE 1 quick_success: $(if ($p1) {'PASS'} else {'FAIL'}) | result=$($r1.Result) exit=$($r1.ExitCode) meta=$($r1.MetaFile)")
        if (-not $p1) { $allPass = $false }

        # CASE 2: quick failure exit 3 -> FAIL_NONZERO_EXIT, exit 3
        $r2 = Invoke-WrappedCommand -Cmd @('python', '-c', 'import sys; sys.exit(3)') `
            -TimeoutSec 60 -Tag 'case2' -LogDir (Join-Path $root 'case2')
        $p2 = ($r2.Result -eq 'FAIL_NONZERO_EXIT' -and $r2.ExitCode -eq 3)
        $caseLines.Add("CASE 2 quick_failure: $(if ($p2) {'PASS'} else {'FAIL'}) | result=$($r2.Result) exit=$($r2.ExitCode) meta=$($r2.MetaFile)")
        if (-not $p2) { $allPass = $false }

        # CASE 3: hard timeout kills the whole tree (parent + spawned child)
        $inner3 = "import subprocess,time,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(300)']); print('CHILD_PID='+str(p.pid), flush=True); time.sleep(300)"
        $r3 = Invoke-WrappedCommand -Cmd @('python', '-c', $inner3) `
            -TimeoutSec 5 -Tag 'case3' -LogDir (Join-Path $root 'case3')
        $outText3 = if (Test-Path $r3.OutLog) { Get-Content $r3.OutLog -Raw } else { "" }
        $childPid3 = $null
        if ($outText3 -match 'CHILD_PID=(\d+)') { $childPid3 = [int]$matches[1] }
        $parentAlive3 = Test-ProcessAlive $r3.ChildPid
        $childAlive3 = if ($null -ne $childPid3) { Test-ProcessAlive $childPid3 } else { $true }
        $p3 = ($r3.Result -eq 'TIMEOUT_WITHOUT_PASS_SUMMARY' -and $r3.ExitCode -eq 124 `
                -and $null -ne $childPid3 -and (-not $parentAlive3) -and (-not $childAlive3) `
                -and $r3.RootKilled -and $r3.TreeKillStatus -eq 'full')
        $treeEvidence = @(
            "parent_pid=$($r3.ChildPid)"
            "child_pid=$childPid3"
            "parent_alive_after_kill=$parentAlive3"
            "child_alive_after_kill=$childAlive3"
            "root_killed=$($r3.RootKilled)"
            "tree_kill_status=$($r3.TreeKillStatus)"
            "kill_detail=$($r3.KillDetail)"
            "WRAPPER_RESULT=$($r3.Result)"
        ) -join "`r`n"
        $treeEvidence | Out-File -FilePath (Join-Path $root 'case3_tree_evidence.txt') -Encoding UTF8
        $caseLines.Add("CASE 3 timeout_kills_tree: $(if ($p3) {'PASS'} else {'FAIL'}) | result=$($r3.Result) exit=$($r3.ExitCode) parent_pid=$($r3.ChildPid) child_pid=$childPid3 parent_alive=$parentAlive3 child_alive=$childAlive3 tree_kill_status=$($r3.TreeKillStatus) evidence=$(Join-Path $root 'case3_tree_evidence.txt')")
        if (-not $p3) { $allPass = $false }

        # CASE 4: non-pytest command printing "73 passed" must NOT be misjudged
        $inner4 = "print('73 passed', flush=True); import time; time.sleep(300)"
        $r4 = Invoke-WrappedCommand -Cmd @('python', '-c', $inner4) `
            -TimeoutSec 5 -Tag 'case4' -LogDir (Join-Path $root 'case4')
        $p4 = ($r4.Result -eq 'TIMEOUT_WITHOUT_PASS_SUMMARY' -and $r4.ExitCode -eq 124 -and $r4.PassMarkerType -eq 'none')
        $caseLines.Add("CASE 4 non_pytest_no_misjudge: $(if ($p4) {'PASS'} else {'FAIL'}) | result=$($r4.Result) exit=$($r4.ExitCode) marker_type=$($r4.PassMarkerType) meta=$($r4.MetaFile)")
        if (-not $p4) { $allPass = $false }

        # CASE 5: pass summary seen, then hang -> PASS_WITH_TEARDOWN_TIMEOUT
        $r5 = Invoke-WrappedCommand -Cmd @('python', '-c', $inner4) `
            -TimeoutSec 10 -TeardownGraceSec 3 -Tag 'case5' -LogDir (Join-Path $root 'case5') `
            -PytestSummaryEnabled $true
        $metaText5 = if (Test-Path $r5.MetaFile) { Get-Content $r5.MetaFile -Raw } else { "" }
        $p5 = ($r5.Result -eq 'PASS_WITH_TEARDOWN_TIMEOUT' -and $r5.ExitCode -eq 0 `
                -and $r5.RootKilled -and $r5.TreeKillStatus -eq 'full' -and $r5.DeadlineHit -eq 'grace' `
                -and $metaText5 -match 'ACTION_REQUIRED=investigate_teardown_hang' `
                -and $metaText5 -match 'deadline_hit=grace' `
                -and $r5.PassMarkerType -eq 'pytest' -and $null -ne $r5.PassMarkerSeenAt `
                -and (-not (Test-ProcessAlive $r5.ChildPid)))
        $caseLines.Add("CASE 5 teardown_timeout: $(if ($p5) {'PASS'} else {'FAIL'}) | result=$($r5.Result) exit=$($r5.ExitCode) root_killed=$($r5.RootKilled) tree=$($r5.TreeKillStatus) deadline_hit=$($r5.DeadlineHit) marker_seen_at=$($r5.PassMarkerSeenAt) meta=$($r5.MetaFile)")
        if (-not $p5) { $allPass = $false }

        # CASE 6: argument quoting (space / quotes / semicolon)
        $r6 = Invoke-WrappedCommand -Cmd @('python', '-c', 'import sys; print(sys.argv[1:])', 'a b', '"q"', 'semi;colon') `
            -TimeoutSec 60 -Tag 'case6' -LogDir (Join-Path $root 'case6')
        $expected6 = "['a b', '" + '"q"' + "', 'semi;colon']"
        $outText6 = if (Test-Path $r6.OutLog) { Get-Content $r6.OutLog -Raw } else { "" }
        $p6 = ($r6.Result -eq 'PASS_NORMAL_EXIT' -and $outText6 -match [regex]::Escape($expected6))
        $caseLines.Add("CASE 6 argument_quoting: $(if ($p6) {'PASS'} else {'FAIL'}) | result=$($r6.Result) expected=$expected6 out=$($r6.OutLog)")
        if (-not $p6) { $allPass = $false }

        # CASE 7: real pytest subset -> PASS_NORMAL_EXIT
        $r7 = Invoke-WrappedCommand -Cmd @('python', '-m', 'pytest', 'tests/test_173_pipeline_cleanup.py', '-q') `
            -TimeoutSec 300 -Tag 'case7' -LogDir (Join-Path $root 'case7') -PytestSummaryEnabled $true
        $p7 = ($r7.Result -eq 'PASS_NORMAL_EXIT' -and $r7.ExitCode -eq 0)
        $caseLines.Add("CASE 7 pytest_subset: $(if ($p7) {'PASS'} else {'FAIL'}) | result=$($r7.Result) exit=$($r7.ExitCode) meta=$($r7.MetaFile)")
        if (-not $p7) { $allPass = $false }

        # CASE 8: business success marker (SuccessMarkerRegex) -> PASS_WITH_TEARDOWN_TIMEOUT
        $inner8 = "print('FAKE_BUSINESS_DONE', flush=True); import time; time.sleep(300)"
        $r8 = Invoke-WrappedCommand -Cmd @('python', '-c', $inner8) `
            -TimeoutSec 10 -TeardownGraceSec 3 -Tag 'case8' -LogDir (Join-Path $root 'case8') `
            -BusinessMarkerRegex 'FAKE_BUSINESS_DONE'
        $metaText8 = if (Test-Path $r8.MetaFile) { Get-Content $r8.MetaFile -Raw } else { "" }
        $p8 = ($r8.Result -eq 'PASS_WITH_TEARDOWN_TIMEOUT' -and $r8.ExitCode -eq 0 `
                -and $r8.PassMarkerType -eq 'business' -and $r8.RootKilled `
                -and $r8.DeadlineHit -eq 'grace' `
                -and $metaText8 -match 'ACTION_REQUIRED=investigate_teardown_hang' `
                -and (-not (Test-ProcessAlive $r8.ChildPid)))
        $caseLines.Add("CASE 8 business_marker_teardown: $(if ($p8) {'PASS'} else {'FAIL'}) | result=$($r8.Result) exit=$($r8.ExitCode) marker_type=$($r8.PassMarkerType) tree=$($r8.TreeKillStatus) deadline_hit=$($r8.DeadlineHit) meta=$($r8.MetaFile)")
        if (-not $p8) { $allPass = $false }

        # CASE 9: real main-path invocation; pytest shape must AUTO-ENABLE summary
        # detection without -DetectPytestSummary. Runs the script as a child
        # powershell process so the true main path (arg parsing + auto-enable +
        # exit code) is exercised end to end.
        $case9Dir = Join-Path $root 'case9'
        $scriptPath = Join-Path $PSScriptRoot 'run_with_timeout.ps1'
        $out9 = & powershell.exe -NoProfile -File $scriptPath -Tag case9 -LogDir $case9Dir python -m pytest tests/test_173_pipeline_cleanup.py -q 2>&1 | Out-String
        $rc9 = $LASTEXITCODE
        $meta9File = Get-ChildItem $case9Dir -Filter 'case9-*.meta.txt' -ErrorAction SilentlyContinue | Select-Object -First 1
        $meta9 = if ($meta9File) { Get-Content $meta9File.FullName -Raw } else { "" }
        $meta9Path = if ($meta9File) { $meta9File.FullName } else { "" }
        $p9 = ($rc9 -eq 0 -and $out9 -match 'WRAPPER_RESULT=PASS_NORMAL_EXIT' `
                -and $meta9 -match 'pass_marker_type=pytest' -and $meta9 -match 'pass_marker_seen_at=\S+')
        $caseLines.Add("CASE 9 pytest_auto_enable_main_path: $(if ($p9) {'PASS'} else {'FAIL'}) | exit=$rc9 marker_auto=$(if ($meta9 -match 'pass_marker_type=pytest') {'pytest'} else {'missing'}) meta=$meta9Path")
        if (-not $p9) { $allPass = $false }
    } finally {
        Pop-Location
    }

    foreach ($l in $caseLines) { Write-Host $l }
    $overall = if ($allPass) { 'ALL_PASS' } else { 'FAIL' }
    Write-Host "SELFTEST_RESULT=$overall"

    $summary = @(
        "selftest_time=$(Get-Date -Format 'o')"
        "ps_version=$($PSVersionTable.PSVersion.ToString())"
        "os=$([System.Environment]::OSVersion.VersionString)"
        "wrapper_version=$($Script:WrapperVersion)"
    ) + $caseLines.ToArray() + @("SELFTEST_RESULT=$overall")
    ($summary -join "`r`n") | Out-File -FilePath (Join-Path $root 'selftest_summary.txt') -Encoding UTF8
    Write-Host "[selftest] evidence root: $root"

    return $allPass
}

# ------------------------------------------------------------------ main ---

function Show-Usage {
    Write-Host @"
Usage:
  powershell -File scripts\run_with_timeout.ps1 [options] [--] <command> [args...]
  & .\scripts\run_with_timeout.ps1 [options] [--] <command> [args...]
Options (space-separated values; names are case-insensitive):
  -TimeoutSec <int>         hard timeout seconds (default 3600)
  -TeardownGraceSec <int>   grace after enabled pass marker (default 120)
  -Tag <string>             log name fragment (default run-<timestamp>)
  -LogDir <string>          log directory (default logs\wrapper)
  -DetectPytestSummary      force pytest summary detection (auto for python -m pytest)
  -SuccessMarkerRegex <s>   business completion marker regex (default disabled)
  -SelfTest                 run the built-in 9-case self-test matrix
Everything after the first non-option token (or after `--`) is the wrapped
command, passed through verbatim: -c, -q, -m, --to, ... all stay intact.
"@
}

$optTimeoutSec = 3600
$optTeardownGraceSec = 120
$optTag = ""
$optLogDir = "logs\wrapper"
$optDetectPytest = $false
$optSuccessMarkerRegex = ""
$optSelfTest = $false

$idx = 0
$cmdStart = -1
$parseError = ""
while ($idx -lt $args.Count) {
    $tok = [string]$args[$idx]
    if ($tok -eq '--') { $cmdStart = $idx + 1; break }
    if (-not $tok.StartsWith('-')) { $cmdStart = $idx; break }
    $consumed = 0
    switch -regex ($tok) {
        '^-TimeoutSec$' {
            $consumed = 2
            $v = $null
            if ($idx + 1 -lt $args.Count) { $v = $args[$idx + 1] -as [int] }
            if ($null -ne $v -and $v -gt 0) { $optTimeoutSec = $v } else { $parseError = "-TimeoutSec requires a positive integer value" }
        }
        '^-TeardownGraceSec$' {
            $consumed = 2
            $v = $null
            if ($idx + 1 -lt $args.Count) { $v = $args[$idx + 1] -as [int] }
            if ($null -ne $v -and $v -gt 0) { $optTeardownGraceSec = $v } else { $parseError = "-TeardownGraceSec requires a positive integer value" }
        }
        '^-Tag$' {
            $consumed = 2
            if ($idx + 1 -lt $args.Count) {
                $v = [string]$args[$idx + 1]
                if ($v -match '[\\/]') { $parseError = "-Tag must not contain '\' or '/' (log path escape guard)" } else { $optTag = $v }
            } else { $parseError = "-Tag requires a value" }
        }
        '^-LogDir$' {
            $consumed = 2
            if ($idx + 1 -lt $args.Count) { $optLogDir = [string]$args[$idx + 1] } else { $parseError = "-LogDir requires a value" }
        }
        '^-SuccessMarkerRegex$' {
            $consumed = 2
            if ($idx + 1 -lt $args.Count) { $optSuccessMarkerRegex = [string]$args[$idx + 1] } else { $parseError = "-SuccessMarkerRegex requires a value" }
        }
        '^-DetectPytestSummary$' { $consumed = 1; $optDetectPytest = $true }
        '^-SelfTest$'            { $consumed = 1; $optSelfTest = $true }
        default                  { $parseError = "unknown option: $tok" }
    }
    if ($parseError) { break }
    $idx += $consumed
}

if ($parseError) {
    Write-Host "ERROR: $parseError"
    Show-Usage
    exit 2
}

if ($optSelfTest) {
    $selfTestOk = Invoke-SelfTest
    if ($selfTestOk -eq $true) { exit 0 } else { exit 1 }
}

$cmdList = @()
if ($cmdStart -ge 0 -and $cmdStart -lt $args.Count) {
    $cmdList = @($args[$cmdStart..($args.Count - 1)])
}
if ($cmdList.Count -eq 0) {
    Write-Output "WRAPPER_RESULT=FAIL_NONZERO_EXIT"
    Write-Output "ERROR=no command given. Usage: run_with_timeout.ps1 [options] [--] <command> [args...]  (or -SelfTest)"
    exit 2
}
# Defensive: if the command still starts with a literal `--`, strip it.
if ($cmdList.Count -gt 0 -and [string]$cmdList[0] -eq '--') {
    if ($cmdList.Count -eq 1) { $cmdList = @() } else { $cmdList = $cmdList[1..($cmdList.Count - 1)] }
}
if ($cmdList.Count -eq 0) {
    Write-Output "WRAPPER_RESULT=FAIL_NONZERO_EXIT"
    Write-Output "ERROR=no command given after --. Usage: run_with_timeout.ps1 [options] [--] <command> [args...]"
    exit 2
}

$pytestEnabled = $false
if ($optDetectPytest) {
    $pytestEnabled = $true
} elseif (Test-PytestCommandShape $cmdList) {
    $pytestEnabled = $true
    Write-Host "[wrapper] pytest summary detection auto-enabled (python -m pytest command shape)"
}

$r = Invoke-WrappedCommand -Cmd $cmdList -TimeoutSec $optTimeoutSec -TeardownGraceSec $optTeardownGraceSec `
    -Tag $optTag -LogDir $optLogDir -PytestSummaryEnabled $pytestEnabled -BusinessMarkerRegex $optSuccessMarkerRegex

Write-Output "WRAPPER_RESULT=$($r.Result)"
Write-Output "EXIT_CODE=$($r.ExitCode)"
if ($r.Result -eq 'PASS_WITH_TEARDOWN_TIMEOUT') {
    Write-Output "ACTION_REQUIRED=investigate_teardown_hang"
    if ($r.DeadlineHit -eq 'hard') {
        Write-Output "NOTE=Pass marker seen but the process reached the hard timeout (${optTimeoutSec}s) before the ${optTeardownGraceSec}s grace elapsed; tree killed at the HARD deadline. Post-173 this should be near-zero; treat as a NEW hang lead, record it, and report it (do not silently swallow)."
    } else {
        Write-Output "NOTE=Pass marker seen but the process did not exit within ${optTeardownGraceSec}s grace; tree killed at the grace deadline. Post-173 this should be near-zero; treat as a NEW hang lead, record it, and report it (do not silently swallow)."
    }
}
Write-Output "META_FILE=$($r.MetaFile)"

exit $r.ExitCode
