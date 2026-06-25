"""Watchdog wrapper for Task 121q Ch1-Ch20 validation.

自动监控验证进程，崩溃后等待 10 秒并自动重启，
利用断点续跑机制从中断章节继续。

用法:
    python scripts/run_121q_with_watchdog.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_SCRIPT = Path(__file__).parent / "task_121q_ch1_ch20_validation.py"
_LOG_DIR = Path("logs/task121q")
_MAX_RESTARTS = 10
_RESTART_DELAY_SEC = 10


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> int:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    restart_count = 0

    while restart_count < _MAX_RESTARTS:
        restart_count += 1
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = _LOG_DIR / f"watchdog-run-{timestamp}.output.txt"
        err_path = _LOG_DIR / f"watchdog-run-{timestamp}.out.log"

        print(f"[{_now()}] Watchdog: starting validation (attempt {restart_count}/{_MAX_RESTARTS})")
        print(f"[{_now()}] stdout -> {out_path}")
        print(f"[{_now()}] stderr -> {err_path}")

        with open(out_path, "w", encoding="utf-8") as out_f, open(
            err_path, "w", encoding="utf-8"
        ) as err_f:
            proc = subprocess.Popen(
                [sys.executable, "-u", str(_SCRIPT)],
                stdout=out_f,
                stderr=err_f,
                cwd=Path(__file__).parent.parent,
            )
            returncode = proc.wait()

        print(f"[{_now()}] Watchdog: process exited with code {returncode}")

        if returncode == 0:
            print(f"[{_now()}] Watchdog: validation completed successfully.")
            return 0

        # 非零退出码：记录崩溃并准备重启
        crash_marker = _LOG_DIR / f"crash-restart-{timestamp}.marker"
        crash_marker.write_text(
            f"exit_code={returncode}\nrestart_count={restart_count}\n",
            encoding="utf-8",
        )

        if restart_count >= _MAX_RESTARTS:
            print(
                f"[{_now()}] Watchdog: max restarts ({_MAX_RESTARTS}) reached. Giving up."
            )
            return 1

        print(
            f"[{_now()}] Watchdog: restarting in {_RESTART_DELAY_SEC}s..."
        )
        time.sleep(_RESTART_DELAY_SEC)

    return 1


if __name__ == "__main__":
    sys.exit(main())
