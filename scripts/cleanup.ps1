# Task 097 预清理脚本 — 杀掉残留进程 + 释放锁

Write-Host "=== 清理残留进程 ==="
taskkill /F /IM python* 2>$null
Start-Sleep -Seconds 1
taskkill /F /IM git* 2>$null
Start-Sleep -Seconds 1

Write-Host "=== 释放 git 锁 ==="
Remove-Item "$PSScriptRoot\.git\index.lock" -Force -ErrorAction SilentlyContinue

Write-Host "=== 清理 DB WAL 残留 ==="
Remove-Item "$PSScriptRoot\evals\output\task_091_scifi_webnovel\*.db-wal" -Force -ErrorAction SilentlyContinue
Remove-Item "$PSScriptRoot\evals\output\task_091_scifi_webnovel\*.db-shm" -Force -ErrorAction SilentlyContinue

Write-Host "=== 完成 ==="
$python = (Get-Process -Name "python*" -ErrorAction SilentlyContinue).Count
$git = (Get-Process -Name "git*" -ErrorAction SilentlyContinue).Count
Write-Host "残留 — Python: $python, Git: $git"
