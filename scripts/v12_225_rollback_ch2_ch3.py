"""V12 Task 225 rollback: 回滚 hard-sf-new-weird Ch2/Ch3 到 Ch1-accepted 态。

背景：225 人工读稿判定 Ch2 accepted 正文有三个正文级硬伤：
  1. 数值线矛盾：spec Ch2 beats 写的是 19.0kg 系（"与第一章封存链上的整数
     缺口一致"），但 Ch1 accepted 正文实际为 27.00kg；Ch2 全章 19.0→21.0kg、
     Ch3 又回到 27.00kg。根因是 spec 与 Ch1 正文从未对账。
  2. RevisionHandler patch 引入三处重复/错位段（初稿 v-2-1 干净，rev-2-2 起
     重复；干净重写 v-2-4 被 best-version 选择淘汰）。
  3. 「第一章」元引用（中文数字变体）。

用户判定 STOP：修 spec 到 27 系 + 回滚 Ch2/Ch3 重跑。本脚本执行回滚（方案 A：
备份后原地手术，备份已由执行会话先行写入 backups/）。

回滚面（全部按 project_id scoped，单事务）：
  - chapter_heads ch2/3：accepted_version_id/current_version_id 置 NULL，
    status 回 'draft'（phase2_graph skip 逻辑只看 accepted_version_id）；
  - summaries / chapter_chunks / context_snapshots ch2/3：删（Ch2 19 系
    summary 会污染 Ch4+ 上下文，chunks 是 RAG 索引）；
  - continuity_reports：删 checked_up_to_chapter=3 的报告行；
  - numerical_ledgers ch2/3：删（含 19.0→21.0 台账）；
  - setting_tracking：删 ch2/3 引入行；ch1 引入行被 ch2/3 结算推进的
    last_mentioned_chapter 重置回 1；
  - foreshadowings：删 ch2/3 种植行（ch1 的 3 条仍 planted/active，未污染）；
  - character_states：删 source_version_id 属于 ch2/3 版本的快照行
    （append-only 纪律对结算产物的一次性人工破例，证据保留在
    chapter_versions 与 backups/ 整库备份）；
  - chapter_versions ch2/3 与 chapter_goals/creative_briefs 旧 plan 行
    全部保留作历史（head 置空后不再被引用；approved-plan short-circuit
    按最新行读取）。

Usage:
    python scripts/v12_225_rollback_ch2_ch3.py            # dry-run，只打印计数
    python scripts/v12_225_rollback_ch2_ch3.py --execute  # 实际执行
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DB = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
CHARACTER_ID = "char-a7237e7e"  # 沈砚（本项目唯一角色）
CHAPTERS = (2, 3)


def main() -> None:
    execute = "--execute" in sys.argv
    db = sqlite3.connect(RUNTIME_DB)
    db.row_factory = sqlite3.Row
    try:
        version_ids = [
            r["version_id"]
            for r in db.execute(
                "SELECT version_id FROM chapter_versions "
                "WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            )
        ]
        placeholders = ",".join("?" for _ in version_ids)

        ops: list[tuple[str, str, tuple]] = [
            (
                "chapter_heads reset",
                "UPDATE chapter_heads SET accepted_version_id=NULL, "
                "current_version_id=NULL, status='draft', "
                "updated_at=datetime('now') "
                "WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "summaries delete",
                "DELETE FROM summaries WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "chapter_chunks delete",
                "DELETE FROM chapter_chunks WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "context_snapshots delete",
                "DELETE FROM context_snapshots WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "continuity_reports delete",
                "DELETE FROM continuity_reports WHERE project_id=?",
                (PROJECT_ID,),
            ),
            (
                "numerical_ledgers delete",
                "DELETE FROM numerical_ledgers WHERE project_id=? AND chapter_number IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "setting_tracking delete ch2/3-introduced",
                "DELETE FROM setting_tracking WHERE project_id=? "
                "AND introduced_in_chapter IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "setting_tracking reset ch1 last_mentioned",
                "UPDATE setting_tracking SET last_mentioned_chapter=1 "
                "WHERE project_id=? AND introduced_in_chapter=1 "
                "AND last_mentioned_chapter>1",
                (PROJECT_ID,),
            ),
            (
                "foreshadowings delete ch2/3-planted",
                "DELETE FROM foreshadowings WHERE project_id=? "
                "AND planted_in_chapter IN (2,3)",
                (PROJECT_ID,),
            ),
            (
                "character_states delete ch2/3 snapshots",
                f"DELETE FROM character_states WHERE character_id=? "
                f"AND source_version_id IN ({placeholders})",
                (CHARACTER_ID, *version_ids),
            ),
        ]

        counts: list[tuple[str, int]] = []
        if execute:
            with db:  # 单事务，任一步失败整体回滚
                for label, sql, params in ops:
                    cur = db.execute(sql, params)
                    counts.append((label, cur.rowcount))
        else:
            for label, sql, params in ops:
                verb, rest = sql.split(" ", 1)
                if verb == "DELETE":
                    count_sql = f"SELECT COUNT(*) {rest}"
                else:  # UPDATE ... -> COUNT 满足 WHERE 的行
                    where_idx = rest.index("WHERE")
                    table = rest.split("SET")[0].strip()
                    count_sql = f"SELECT COUNT(*) FROM {table} {rest[where_idx:]}"
                cur = db.execute(count_sql, params)
                counts.append((label, cur.fetchone()[0]))

        mode = "EXECUTE" if execute else "DRY-RUN"
        print(f"[{mode}] project={PROJECT_ID} ch2/3 versions={len(version_ids)}")
        for label, n in counts:
            print(f"  {label}: {n}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
