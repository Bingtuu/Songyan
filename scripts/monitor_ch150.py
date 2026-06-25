"""
静默监控脚本：监控 Ch1-Ch150 full single-run 进展。
每 5 分钟检查一次，有异常或完成时输出提醒。
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta
import sys

db_path = "c:/Vibe Project/Songyan/songyan.db"

def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def check():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Overall progress
    cursor.execute("SELECT chapter_number, status FROM chapter_heads WHERE chapter_number BETWEEN 1 AND 150")
    rows = cursor.fetchall()
    accepted = [r['chapter_number'] for r in rows if r['status'] == 'accepted']
    under_review = [r['chapter_number'] for r in rows if r['status'] == 'under_review']
    draft = [r['chapter_number'] for r in rows if r['status'] == 'draft']

    max_accepted = max(accepted) if accepted else 0
    total_accepted = len(accepted)

    # Check for gaps
    gaps = []
    if accepted:
        for i in range(1, max_accepted + 1):
            if i not in accepted:
                gaps.append(i)

    # Check errors
    cursor.execute("SELECT error_message, created_at FROM lifecycle_errors ORDER BY created_at DESC LIMIT 5")
    errors = cursor.fetchall()

    # Check latest version creation time for current chapter
    current_ch = None
    if under_review:
        current_ch = min(under_review)
    elif draft:
        current_ch = min(draft)

    latest_version_time = None
    if current_ch:
        cursor.execute("""
            SELECT MAX(created_at) as latest FROM chapter_versions WHERE chapter_number = ?
        """, (current_ch,))
        row = cursor.fetchone()
        latest_version_time = row['latest'] if row else None

    conn.close()
    return {
        'total_accepted': total_accepted,
        'max_accepted': max_accepted,
        'gaps': gaps,
        'under_review': under_review,
        'draft': draft,
        'errors': errors,
        'current_ch': current_ch,
        'latest_version_time': latest_version_time,
    }

def main():
    log("监控启动：目标 Ch150 完成")
    last_accepted = 0
    last_current_ch = None
    stuck_start = None

    while True:
        try:
            state = check()

            # Completion check
            if state['max_accepted'] >= 150:
                log(f"✅ Ch150 完成！总共 accepted {state['total_accepted']} 章。监控结束。")
                sys.exit(0)

            # Progress update
            if state['max_accepted'] > last_accepted:
                log(f"📈 进展更新：Ch1-Ch{state['max_accepted']} 已 accepted（+{state['max_accepted'] - last_accepted} 章）")
                last_accepted = state['max_accepted']
                stuck_start = None

            # Current chapter update
            if state['current_ch'] != last_current_ch:
                if state['current_ch']:
                    log(f"🔄 当前处理中：Ch{state['current_ch']}")
                last_current_ch = state['current_ch']
                stuck_start = None

            # Stuck detection (30 min without new version)
            if state['current_ch'] and state['latest_version_time']:
                try:
                    latest_dt = datetime.fromisoformat(state['latest_version_time'].replace('Z', '+00:00'))
                except Exception:
                    latest_dt = datetime.strptime(state['latest_version_time'], "%Y-%m-%dT%H:%M:%S.%f")
                now = datetime.now(latest_dt.tzinfo if latest_dt.tzinfo else None)
                elapsed = (now - latest_dt).total_seconds()
                if elapsed > 1800:  # 30 minutes
                    if stuck_start is None:
                        stuck_start = now
                    elif (now - stuck_start).total_seconds() > 300:  # Alert once per 5 min after stuck
                        log(f"⚠️  疑似卡住：Ch{state['current_ch']} 已超过 {int(elapsed/60)} 分钟无新版本")
                else:
                    stuck_start = None

            # Gap detection
            if state['gaps']:
                log(f"🚨 发现 accepted 序列间隙：{state['gaps']}")

            # Error detection
            if state['errors']:
                for e in state['errors']:
                    log(f"❌ 错误：{e['created_at']} - {e['error_message'][:120] if e['error_message'] else ''}")

        except Exception as e:
            log(f"监控脚本异常：{e}")

        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
