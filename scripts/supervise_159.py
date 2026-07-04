"""Task 159 自主督跑（supervisor）— 保守策略.

职责：监控 run_159_ch1_ch150.py 长跑，在 AutoHalt/paused 后按"保守策略"自动判断
resume 还是停下上报，无需人工逐次介入，直到 150 章跑完或需人判时停下。

纯运维脚本，**不碰 src/ 治理代码**。验证纪律：真退化只记录/上报，不改治理绕过。

保守策略：
  自动 resume 当且仅当命中已知良性暂停：
    - context_emergency_budget_ratio_halt （resume 重算早期章的预算压力，已确认良性）
    - health_low_p1_halt 且 P1 数 ≤ P1_SMALL_MAX 且较上次有进展（accepted 增加）
  停下上报（escalation）当命中：
    - quality_gate_fail_streak / health_low_score_halt / health<7.0 / 未知暂停原因
  防呆护栏（无论原因）：
    - 同章连续暂停 ≥ SAME_CHAPTER_MAX 次且 accepted 不增 → 停
    - 连续 NO_PROGRESS_MAX 次 resume 后 accepted 不增 → 停
    - 总 resume 次数 ≥ RESUME_CAP → 停
    - 进程卡死（日志 idle 超时）→ 清理僵尸后按 paused 处理

用法：
    $env:DATABASE_URL = "sqlite:///.tmp/task159_ch1_ch150.db"
    python scripts/supervise_159.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(".tmp/task159_ch1_ch150.db")
RUN_SCRIPT = "scripts/run_159_ch1_ch150.py"
RESUME_LOG_PREFIX = ".tmp/task159_supervised_resume"
ESCALATION_FILE = Path(".tmp/task159_supervisor_escalation.json")
SUPERVISOR_LOG = Path(".tmp/task159_supervisor.log")
END_CHAPTER = 150

# --- 保守策略参数 ---
P1_SMALL_MAX = 2          # health_low_p1_halt 可自动 resume 的最大 P1 数
SAME_CHAPTER_MAX = 3      # 同章连续暂停上限
NO_PROGRESS_MAX = 2       # 连续无进展 resume 上限
RESUME_CAP = 30           # 总 resume 次数上限
HEALTH_FLOOR = 7.0        # health 崩盘线
POLL_SEC = 120            # running 时轮询间隔
LOG_IDLE_DEAD_SEC = 600   # 日志 idle 超过此值视为进程卡死/退出

# 良性暂停原因（可自动 resume）
BENIGN_BUDGET = "context_emergency_budget_ratio_halt"
BENIGN_P1 = "health_low_p1_halt"
# 需上报的严重原因
SEVERE_REASONS = ("quality_gate_fail_streak", "health_low_score_halt")


def _log(msg: str) -> None:
    line = f"{datetime.now().isoformat()} {msg}"
    print(line, flush=True)
    SUPERVISOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SUPERVISOR_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _db_state() -> dict:
    import sqlite3

    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    r = c.execute(
        "SELECT run_id,current_chapter,status,completed_chapters,failed_chapters "
        "FROM project_runs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    acc = c.execute(
        "SELECT COUNT(*) FROM chapter_heads WHERE status='accepted'"
    ).fetchone()[0]
    # 最近 continuity health（用于 health 崩盘护栏）
    hrow = c.execute(
        "SELECT overall_health_score FROM continuity_reports "
        "ORDER BY checked_up_to_chapter DESC LIMIT 1"
    ).fetchone()
    c.close()
    return {
        "run_id": r["run_id"],
        "status": r["status"],
        "current_chapter": r["current_chapter"],
        "completed": json.loads(r["completed_chapters"] or "[]"),
        "failed": json.loads(r["failed_chapters"] or "[]"),
        "accepted_heads": acc,
        "latest_health": hrow["overall_health_score"] if hrow else None,
    }


def _latest_run_log(run_id: str) -> Path | None:
    p = Path(f"logs/chapter_runs/{run_id}.jsonl")
    return p if p.exists() else None


def _find_halt_reason() -> str | None:
    """从最近的 supervised_resume 日志或首个 run 日志里解析 halt 原因."""
    candidates = sorted(
        Path(".tmp").glob("task159_*resume*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # 也含首跑日志
    first = Path(".tmp/task159_run.log")
    if first.exists():
        candidates.append(first)
    for logp in candidates:
        try:
            text = logp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matches = re.findall(r"gate_triggered .*reasons=\['([^']+)'", text)
        if matches:
            return matches[-1]
    return None


def _newest_log_mtime() -> float:
    logs = list(Path(".tmp").glob("task159_*resume*.log"))
    logs.append(Path(".tmp/task159_run.log"))
    mtimes = [p.stat().st_mtime for p in logs if p.exists()]
    return max(mtimes) if mtimes else 0.0


def _kill_stale_python() -> None:
    """终止卡死的 run_159 python 进程（僵尸收尾线程）."""
    try:
        out = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*run_159_ch1_ch150*' } | "
                "Select-Object -ExpandProperty ProcessId",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        pids = [p.strip() for p in out.stdout.splitlines() if p.strip().isdigit()]
        for pid in pids:
            subprocess.run(
                ["powershell", "-Command", f"Stop-Process -Id {pid} -Force"],
                capture_output=True,
                timeout=30,
            )
            _log(f"[cleanup] killed stale run_159 pid {pid}")
    except (subprocess.SubprocessError, OSError) as exc:
        _log(f"[cleanup] kill attempt failed: {exc}")


def _launch_resume(idx: int) -> subprocess.Popen:
    logf = open(f"{RESUME_LOG_PREFIX}{idx}.log", "w", encoding="utf-8")  # noqa: SIM115
    env = {**_env(), "DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}"}
    proc = subprocess.Popen(
        [sys.executable, RUN_SCRIPT, "--resume"],
        stdout=logf,
        stderr=subprocess.STDOUT,
        env=env,
    )
    _log(f"[resume #{idx}] launched pid {proc.pid} → {RESUME_LOG_PREFIX}{idx}.log")
    return proc


def _env() -> dict:
    import os

    return dict(os.environ)


def _escalate(reason: str, state: dict, detail: str) -> None:
    payload = {
        "escalated_at": datetime.now().isoformat(),
        "reason": reason,
        "detail": detail,
        "state": state,
    }
    ESCALATION_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log(f"[ESCALATE] {reason}: {detail}")
    _log(f"[ESCALATE] state={state}")


def _classify(halt_reason: str | None, state: dict, made_progress: bool) -> tuple[str, str]:
    """返回 (action, detail)。action ∈ {resume, escalate}."""
    health = state.get("latest_health")
    if health is not None and health < HEALTH_FLOOR:
        return "escalate", f"health {health} < {HEALTH_FLOOR} 崩盘线"
    if halt_reason is None:
        return "escalate", "未能解析暂停原因（fail-safe 停下上报）"
    for severe in SEVERE_REASONS:
        if severe in halt_reason:
            return "escalate", f"严重门禁 {severe}：{halt_reason}"
    if BENIGN_BUDGET in halt_reason:
        return "resume", f"良性预算门禁：{halt_reason}"
    if BENIGN_P1 in halt_reason:
        m = re.search(r"P1_count=(\d+)", halt_reason)
        p1 = int(m.group(1)) if m else 99
        if p1 <= P1_SMALL_MAX and made_progress:
            return "resume", f"小 P1={p1} 且有进展：{halt_reason}"
        if p1 > P1_SMALL_MAX:
            return "escalate", f"P1={p1} 超过 {P1_SMALL_MAX}：{halt_reason}"
        return "escalate", f"P1 halt 但无进展：{halt_reason}"
    return "escalate", f"未知门禁原因（fail-safe）：{halt_reason}"


def _generate_report() -> None:
    _log("[done] 150 章完成，生成验收报告 …")
    env = {**_env(), "DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}"}
    subprocess.run(
        [sys.executable, RUN_SCRIPT, "--report"],
        env=env,
        timeout=1800,
    )
    _log("[done] 报告已生成：docs/reports/task-159-v6-final-acceptance-report.md")


def main() -> None:
    _log("=== supervisor 启动（保守策略）===")
    resume_idx = 0
    last_accepted = -1
    no_progress_streak = 0
    same_chapter_halts: dict[int, int] = {}

    while True:
        try:
            state = _db_state()
        except Exception as exc:  # noqa: BLE001 — DB 可能瞬时被写锁
            _log(f"[warn] 读状态失败，重试：{exc}")
            time.sleep(15)
            continue

        status = state["status"]
        accepted = state["accepted_heads"]

        # 完成
        if status == "completed" or accepted >= END_CHAPTER:
            _log(f"[complete] status={status} accepted={accepted}")
            _generate_report()
            _log("=== supervisor 正常结束 ===")
            return

        # 运行中：检查是否卡死
        if status == "running":
            idle = time.time() - _newest_log_mtime()
            if idle > LOG_IDLE_DEAD_SEC:
                _log(f"[stuck] running 但日志 idle {int(idle)}s，视为卡死，清理后按 paused 处理")
                _kill_stale_python()
                time.sleep(5)
                # 落到 paused 分支处理
            else:
                _log(
                    f"[running] Ch{state['current_chapter']} "
                    f"accepted={accepted} idle={int(idle)}s"
                )
                time.sleep(POLL_SEC)
                continue

        # paused（或卡死判为需 resume）
        _kill_stale_python()  # 确保无僵尸持有 DB
        time.sleep(5)

        made_progress = accepted > last_accepted
        cur = state["current_chapter"]
        same_chapter_halts[cur] = same_chapter_halts.get(cur, 0) + 1

        # 护栏：撞墙
        if same_chapter_halts[cur] >= SAME_CHAPTER_MAX and not made_progress:
            _escalate(
                "wall_hit",
                state,
                f"Ch{cur} 连续暂停 {same_chapter_halts[cur]} 次且无进展",
            )
            return
        # 护栏：无进展
        if not made_progress:
            no_progress_streak += 1
        else:
            no_progress_streak = 0
        if no_progress_streak >= NO_PROGRESS_MAX:
            _escalate("no_progress", state, f"连续 {no_progress_streak} 次 resume 无进展")
            return
        # 护栏：resume 上限
        if resume_idx >= RESUME_CAP:
            _escalate("resume_cap", state, f"resume 次数达上限 {RESUME_CAP}")
            return

        halt_reason = _find_halt_reason()
        action, detail = _classify(halt_reason, state, made_progress)
        _log(f"[paused] Ch{cur} accepted={accepted} reason={halt_reason} → {action}: {detail}")

        if action == "escalate":
            _escalate("policy_stop", state, detail)
            return

        # resume（不 proc.wait：resume 进程 halt 后会变僵尸线程，wait 会永久挂起）
        last_accepted = accepted
        resume_idx += 1
        _launch_resume(resume_idx)
        # 等 resume 接管：轮询到 status 变 running（或 accepted 增长/完成）再回主循环
        took_hold = False
        for _ in range(30):  # 最多等 ~5min
            time.sleep(10)
            try:
                s2 = _db_state()
            except Exception:  # noqa: BLE001
                continue
            if s2["status"] == "running" or s2["accepted_heads"] > accepted or (
                s2["status"] == "completed"
            ):
                took_hold = True
                _log(
                    f"[resume #{resume_idx}] 接管：status={s2['status']} "
                    f"accepted={s2['accepted_heads']}"
                )
                break
        if not took_hold:
            _log(f"[resume #{resume_idx}] 未接管（status 未转 running），下一轮重判")
        time.sleep(10)  # 让 DB/WAL 落定后回主循环


if __name__ == "__main__":
    main()
