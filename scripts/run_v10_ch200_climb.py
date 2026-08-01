"""Task 191: V10 Ch200 climb harness.

This script prepares the control plane for V10 Ch200 climbs:
- fixed V10 paths;
- Task 190 source verdict gate;
- Task 189 Ch200 baseline wiring;
- dry-run/status/audit command construction.

Task 191 validation must not run real Ch101+ generation.  The non-dry-run
``--to`` path is intentionally explicit and is for later Task 192-194 runs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

TASK_ID = "191"
CHECKPOINTS = (125, 150, 175, 200)
DEFAULT_BASELINE = Path("tasks/189-scifi-ch200-baseline.json")
DEFAULT_INVENTORY = Path(".tmp/190_ch100_source_inventory.json")
DEFAULT_CANONICAL_INVENTORY = Path("tasks/190-ch100-terminal-source-inventory-DONE.md")
DEFAULT_WORK_DIR = Path(".tmp")
READY = "CONTINUE_READY"


@dataclass(frozen=True)
class SourceRecord:
    """Task 190 source verdict for one genre."""

    genre: str
    verdict: str
    db_path: Path | None = None
    project_id: str | None = None
    run_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class Inventory:
    """Loaded Task 190 source inventory."""

    source: Path | None
    work_copy_available: bool
    records: dict[str, SourceRecord]
    warning: str | None = None


@dataclass(frozen=True)
class HarnessPaths:
    """Fixed V10 paths for one genre."""

    db: Path
    project_file: Path
    segment_log: Path
    final_report: Path
    work_dir: Path

    def five_gate(self, checkpoint: int) -> Path:
        return self.work_dir / f"v10_{self.genre}_seg{checkpoint}_five_gate.json"

    def segment_audit(self, checkpoint: int) -> Path:
        return self.work_dir / f"v10_{self.genre}_seg{checkpoint}_audit.json"

    def metrics(self, checkpoint: int) -> Path:
        return self.work_dir / f"v10_{self.genre}_seg{checkpoint}_metrics.md"

    @property
    def genre(self) -> str:
        return _genre_from_db_path(self.db)

    def to_dict(self, checkpoint: int | None = None) -> dict[str, str]:
        payload = {
            "db": self.db.as_posix(),
            "project_file": self.project_file.as_posix(),
            "segment_log": self.segment_log.as_posix(),
            "final_report": self.final_report.as_posix(),
        }
        if checkpoint is not None:
            payload.update(
                {
                    "five_gate": self.five_gate(checkpoint).as_posix(),
                    "segment_audit": self.segment_audit(checkpoint).as_posix(),
                    "metrics": self.metrics(checkpoint).as_posix(),
                }
            )
        return payload


def _genre_from_db_path(path: Path) -> str:
    name = path.stem
    match = re.match(r"task_v10_(?P<genre>.+)_ch200$", name)
    return match.group("genre") if match else "unknown"


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true", help="show or prepare V10 paths")
    action.add_argument("--init-from-source", action="store_true", help="copy a ready Ch100 DB")
    action.add_argument("--to", type=int, help="run to a V10 checkpoint")
    action.add_argument("--status", action="store_true", help="show current V10 harness status")
    action.add_argument(
        "--audit",
        action="store_true",
        help="run or show checkpoint audit commands",
    )

    parser.add_argument("--genre", default=None, help="genre id; falls back to TEMPLATE_ID")
    parser.add_argument("--source-db", type=Path, default=None, help="Task 190 source DB")
    parser.add_argument("--source-project-id", default=None, help="Task 190 source project_id")
    parser.add_argument("--source-run-id", default=None, help="Task 190 source run_id")
    parser.add_argument("--run-id", default=None, help="new V10 run trace id")
    parser.add_argument("--up-to", type=int, default=None, help="checkpoint for --audit")
    parser.add_argument(
        "--cost-budget",
        type=float,
        default=None,
        help="run cost budget (CNY); falls back to SONGYAN_RUN_COST_BUDGET",
    )
    parser.add_argument(
        "--on-failure",
        choices=("isolate", "retry", "abort"),
        default="isolate",
        help="single-chapter failure policy for real --to runs; default keeps Task 191 behavior",
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--canonical-inventory", type=Path, default=DEFAULT_CANONICAL_INVENTORY)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--dry-run", action="store_true", help="print decisions without writes/LLM")
    parser.add_argument("--force", action="store_true", help="overwrite target DB on init")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def harness_paths(genre: str, work_dir: Path = DEFAULT_WORK_DIR) -> HarnessPaths:
    """Return fixed V10 paths for a genre."""
    return HarnessPaths(
        db=work_dir / f"task_v10_{genre}_ch200.db",
        project_file=work_dir / f"task_v10_{genre}_project.json",
        segment_log=work_dir / f"task_v10_{genre}_segments.jsonl",
        final_report=work_dir / f"v10_{genre}_ch200_final.json",
        work_dir=work_dir,
    )


def load_inventory(inventory_path: Path, canonical_path: Path) -> Inventory:
    """Load Task 190 source inventory from .tmp JSON or DONE markdown."""
    if inventory_path.exists():
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))
        genres = raw.get("genres", {})
        records = {
            genre: _record_from_mapping(genre, data)
            for genre, data in genres.items()
            if isinstance(data, dict)
        }
        return Inventory(source=inventory_path, work_copy_available=True, records=records)

    if canonical_path.exists():
        records = _records_from_done_markdown(canonical_path.read_text(encoding="utf-8"))
        warning = (
            f"inventory work copy missing: {inventory_path.as_posix()}; "
            f"using canonical DONE: {canonical_path.as_posix()}"
        )
        return Inventory(
            source=canonical_path,
            work_copy_available=False,
            records=records,
            warning=warning,
        )

    warning = (
        f"missing inventory work copy {inventory_path.as_posix()} and canonical "
        f"{canonical_path.as_posix()}"
    )
    return Inventory(source=None, work_copy_available=False, records={}, warning=warning)


def _record_from_mapping(genre: str, data: dict[str, Any]) -> SourceRecord:
    return SourceRecord(
        genre=genre,
        verdict=str(data.get("verdict") or ""),
        db_path=_optional_path(data.get("db_path")),
        project_id=_clean_identifier(data.get("project_id")),
        run_id=_clean_identifier(data.get("run_id")),
        reason=str(data.get("reason") or ""),
    )


def _records_from_done_markdown(text: str) -> dict[str, SourceRecord]:
    records: dict[str, SourceRecord] = {}
    summary_pattern = re.compile(
        r"^\|\s*(?P<genre>xuanhuan|wuxia|urban)\s*"
        r"\|\s*\*\*(?P<verdict>[A-Z_]+)\*\*\s*"
        r"\|\s*(?P<reason>.*?)\s*\|$",
        re.MULTILINE,
    )
    detail_pattern = re.compile(
        r"^### (?P<genre>xuanhuan|wuxia|urban) .*?"
        r"(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    details = {
        match.group("genre"): match.group(0)
        for match in detail_pattern.finditer(text)
    }
    for match in summary_pattern.finditer(text):
        genre = match.group("genre")
        detail = details.get(genre, "")
        records[genre] = SourceRecord(
            genre=genre,
            verdict=match.group("verdict"),
            db_path=_extract_table_path(detail, "db_path"),
            project_id=_extract_table_value(detail, "project_id"),
            run_id=_extract_table_value(detail, "run_id"),
            reason=match.group("reason"),
        )
    return records


def _extract_table_path(section: str, field: str) -> Path | None:
    value = _extract_table_value(section, field)
    return Path(value) if value else None


def _extract_table_value(section: str, field: str) -> str | None:
    pattern = re.compile(rf"^\|\s*{re.escape(field)}[^|]*\|\s*(?P<value>.*?)\s*\|$", re.MULTILINE)
    match = pattern.search(section)
    if not match:
        return None
    raw = match.group("value")
    code_match = re.search(r"`([^`]+)`", raw)
    text = code_match.group(1) if code_match else raw
    return _clean_identifier(text)


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    return Path(text) if text else None


def _clean_identifier(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.split()[0]


def resolve_genre(args: argparse.Namespace) -> str:
    """Resolve target genre."""
    genre = args.genre or os.getenv("TEMPLATE_ID")
    if not genre:
        raise HarnessError("missing --genre and TEMPLATE_ID fallback")
    return str(genre)


class HarnessError(RuntimeError):
    """Controlled harness error."""


def build_init_plan(
    *,
    genre: str,
    args: argparse.Namespace,
    inventory: Inventory,
    paths: HarnessPaths,
) -> dict[str, Any]:
    """Build init/init-from-source decision payload."""
    record = inventory.records.get(genre)
    source_db = args.source_db or (record.db_path if record else None)
    source_project_id = args.source_project_id or (record.project_id if record else None)
    source_run_id = args.source_run_id or (record.run_id if record else None)
    run_id = args.run_id or f"run-v10-{genre}-{uuid.uuid4().hex[:8]}"
    verdict = record.verdict if record else None

    if args.init:
        return {
            "task": TASK_ID,
            "action": "init",
            "dry_run": bool(args.dry_run),
            "genre": genre,
            "allowed": True,
            "blocker": None,
            "next_step": "use --init-from-source with a CONTINUE_READY source",
            "inventory": _inventory_payload(inventory),
            "source": {
                "verdict": verdict,
                "db": source_db.as_posix() if source_db else None,
                "project_id": source_project_id,
                "run_id": source_run_id,
                "reason": record.reason if record else None,
            },
            "target": paths.to_dict(),
            "run_id": run_id,
            "baseline": args.baseline.as_posix(),
            "writes": [] if args.dry_run else [paths.work_dir.as_posix()],
        }

    allowed = bool(args.init_from_source and record and verdict == READY)
    blocker = _source_blocker(record, source_db=source_db, source_project_id=source_project_id)
    if blocker is not None:
        allowed = False

    next_step = _source_next_step(record, source_db=source_db, source_project_id=source_project_id)
    return {
        "task": TASK_ID,
        "action": "init-from-source" if args.init_from_source else "init",
        "dry_run": bool(args.dry_run),
        "genre": genre,
        "allowed": allowed,
        "blocker": blocker,
        "next_step": next_step,
        "inventory": _inventory_payload(inventory),
        "source": {
            "verdict": verdict,
            "db": source_db.as_posix() if source_db else None,
            "project_id": source_project_id,
            "run_id": source_run_id,
            "reason": record.reason if record else None,
        },
        "target": paths.to_dict(),
        "run_id": run_id,
        "baseline": args.baseline.as_posix(),
        "writes": [] if args.dry_run else [paths.db.as_posix(), paths.project_file.as_posix()],
    }


def _source_blocker(
    record: SourceRecord | None,
    *,
    source_db: Path | None,
    source_project_id: str | None,
) -> str | None:
    if record is None:
        return "missing Task 190 source verdict; rebuild .tmp inventory or pass canonical input"
    if record.verdict != READY:
        return f"Task 190 verdict is {record.verdict}; source is not clean"
    if source_db is None:
        return "missing source DB; pass --source-db or rebuild .tmp inventory"
    if source_project_id is None:
        return "missing source project_id; pass --source-project-id or rebuild .tmp inventory"
    if record.db_path is None or record.project_id is None:
        return (
            "Task 190 source lacks canonical db_path/project_id; "
            "rebuild .tmp inventory before initialization"
        )
    if not _same_path(source_db, record.db_path):
        return (
            "source DB does not match Task 190 inventory: "
            f"expected {record.db_path.as_posix()}, got {source_db.as_posix()}"
        )
    if source_project_id != record.project_id:
        return (
            "source project_id does not match Task 190 inventory: "
            f"expected {record.project_id}, got {source_project_id}"
        )
    validation = validate_ch100_source(source_db, source_project_id, record.genre)
    if not validation["valid"]:
        return str(validation["error"])
    return None


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _source_next_step(
    record: SourceRecord | None,
    *,
    source_db: Path | None,
    source_project_id: str | None,
) -> str:
    if record is None:
        return "rebuild .tmp/190_ch100_source_inventory.json or inspect Task 190 DONE"
    if record.verdict == "BLOCKED_DIRTY_SAMPLE":
        return "clean the dirty Ch100 sample, rerun T9=0, then refresh Task 190 verdict"
    if record.verdict == "REBUILD_REQUIRED":
        return "restore the original Ch100 DB or clean-rerun to Ch100 before Ch200"
    if record.verdict == "BLOCKED_MISSING_SOURCE":
        return "provide DB / project_id / run_id and rerun Task 190 inventory"
    if source_db is None or source_project_id is None:
        return "pass --source-db and --source-project-id, or rebuild .tmp inventory"
    return "source accepted for V10 Ch200 initialization"


def _inventory_payload(inventory: Inventory) -> dict[str, Any]:
    return {
        "source": inventory.source.as_posix() if inventory.source else None,
        "work_copy_available": inventory.work_copy_available,
        "warning": inventory.warning,
    }


def init_from_source(plan: dict[str, Any], *, force: bool) -> dict[str, Any]:
    """Copy ready Ch100 source DB into the V10 Ch200 target slot."""
    if not plan["allowed"]:
        raise HarnessError(str(plan["blocker"] or "source is not allowed"))
    source_db = Path(plan["source"]["db"])
    target_db = Path(plan["target"]["db"])
    project_file = Path(plan["target"]["project_file"])
    segment_log = Path(plan["target"]["segment_log"])
    if not source_db.exists():
        raise HarnessError(f"source DB does not exist: {source_db}")
    if target_db.exists() and not force:
        raise HarnessError(f"target DB already exists: {target_db}; use --force to overwrite")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    _remove_sqlite_family(target_db)
    _backup_sqlite_db(source_db, target_db)
    _create_v10_project_run(target_db, plan)
    project_file.write_text(
        json.dumps(_project_file_payload(plan), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _append_segment_log(segment_log, _segment_init_record(plan))
    return {
        **plan,
        "dry_run": False,
        "initialized": True,
        "writes": [target_db.as_posix(), project_file.as_posix(), segment_log.as_posix()],
    }


def validate_ch100_source(source_db: Path, project_id: str, genre: str) -> dict[str, Any]:
    """Validate that a source DB contains a clean Ch1-Ch100 accepted head set."""
    if not source_db.exists():
        return {"valid": False, "error": f"source DB does not exist: {source_db}"}
    conn: sqlite3.Connection | None = None
    try:
        conn = _connect_readonly(source_db)
        project_row = conn.execute(
            "SELECT genre_id FROM projects WHERE project_id = ? LIMIT 1",
            (project_id,),
        ).fetchone()
        if project_row is None:
            return {"valid": False, "error": f"source project_id not found: {project_id}"}
        if project_row[0] != genre:
            return {
                "valid": False,
                "error": f"source genre mismatch: expected {genre}, got {project_row[0]}",
            }
        rows = conn.execute(
            """SELECT h.chapter_number, h.accepted_version_id, h.status,
                      cv.version_id, cv.content
               FROM chapter_heads h
               LEFT JOIN chapter_versions cv ON cv.version_id = h.accepted_version_id
              WHERE h.project_id = ?
              ORDER BY h.chapter_number""",
            (project_id,),
        ).fetchall()
    except sqlite3.Error as exc:
        return {"valid": False, "error": f"failed to validate source DB: {exc}"}
    finally:
        if conn is not None:
            conn.close()

    accepted = [
        int(chapter)
        for chapter, accepted_version_id, status, version_id, _content in rows
        if accepted_version_id and status == "accepted" and version_id
    ]
    expected = list(range(1, 101))
    if accepted != expected:
        return {
            "valid": False,
            "error": (
                "source DB is not a clean Ch100 accepted source: "
                f"accepted_count={len(accepted)}, "
                f"first={accepted[0] if accepted else None}, "
                f"last={accepted[-1] if accepted else None}"
            ),
        }
    t9 = _t9_counts_from_rows(rows)
    if t9["meta_artifact"] or t9["duplicate"] or t9["timeline"]:
        return {
            "valid": False,
            "error": (
                "source DB is not T9 clean: "
                f"meta_artifact={t9['meta_artifact']}, duplicate={t9['duplicate']}, "
                f"timeline={t9['timeline']}"
            ),
        }
    return {
        "valid": True,
        "accepted_count": len(accepted),
        "accepted_range": "Ch1-Ch100",
        "project_id": project_id,
        "genre_id": project_row[0],
        "t9": t9,
    }


def _t9_counts_from_rows(rows: list[sqlite3.Row] | list[tuple[Any, ...]]) -> dict[str, int]:
    from songyan.agents.rule_auditor import (
        detect_duplicate_paragraphs,
        detect_markdown_scene_titles,
        detect_meta_tag_leaks,
        detect_text_cleanliness_artifacts,
    )
    from songyan.evals.timeline_consistency import (
        detect_timeline_conflicts,
        extract_time_signals,
    )

    meta_artifact = 0
    duplicate = 0
    signals_by_chapter: dict[int, Any] = {}
    for row in rows:
        chapter = int(row[0])
        content = str(row[4] or "")
        meta_artifact += len(detect_meta_tag_leaks(content))
        meta_artifact += len(detect_markdown_scene_titles(content))
        meta_artifact += len(detect_text_cleanliness_artifacts(content))
        duplicate += len(detect_duplicate_paragraphs(content))
        signals_by_chapter[chapter] = extract_time_signals(chapter, content)
    timeline = len(detect_timeline_conflicts(signals_by_chapter))
    return {"meta_artifact": meta_artifact, "duplicate": duplicate, "timeline": timeline}


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def _remove_sqlite_family(db_path: Path) -> None:
    for path in (
        db_path,
        db_path.with_name(db_path.name + "-wal"),
        db_path.with_name(db_path.name + "-shm"),
    ):
        if path.exists():
            path.unlink()


def _backup_sqlite_db(source_db: Path, target_db: Path) -> None:
    """Copy a SQLite DB using the backup API to include a consistent WAL snapshot."""
    source = _connect_readonly(source_db)
    target = sqlite3.connect(target_db)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def _create_v10_project_run(target_db: Path, plan: dict[str, Any]) -> None:
    run_id = str(plan["run_id"])
    project_id = str(plan["source"]["project_id"])
    now = datetime.now(UTC).isoformat()
    completed = json.dumps(list(range(1, 101)))
    conn = sqlite3.connect(target_db)
    try:
        existing = conn.execute(
            "SELECT 1 FROM project_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """INSERT INTO project_runs (
                    run_id, project_id, chapter_range_start, chapter_range_end,
                    current_chapter, completed_chapters, failed_chapters,
                    accumulated_summary, total_cost, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    project_id,
                    1,
                    200,
                    101,
                    completed,
                    "[]",
                    "",
                    0.0,
                    "running",
                    now,
                    now,
                ),
            )
            conn.commit()
    except sqlite3.Error as exc:
        raise HarnessError(f"failed to create V10 project_run: {exc}") from exc
    finally:
        conn.close()


def prepare_paths(plan: dict[str, Any]) -> dict[str, Any]:
    """Create the V10 work directory without creating a DB or project."""
    work_dir = Path(plan["target"]["db"]).parent
    work_dir.mkdir(parents=True, exist_ok=True)
    return {
        **plan,
        "dry_run": False,
        "prepared": True,
        "writes": [work_dir.as_posix()],
    }


def _project_file_payload(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK_ID,
        "genre": plan["genre"],
        "project_id": plan["source"]["project_id"],
        "run_id": plan["run_id"],
        "db": plan["target"]["db"],
        "source_db": plan["source"]["db"],
        "source_project_id": plan["source"]["project_id"],
        "source_run_id": plan["source"]["run_id"],
        "source_verdict": plan["source"]["verdict"],
        "baseline": plan["baseline"],
        "initialized_at": datetime.now(UTC).isoformat(),
    }


def _segment_init_record(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "event": "init_from_source",
        "task": TASK_ID,
        "genre": plan["genre"],
        "source_db": plan["source"]["db"],
        "target_db": plan["target"]["db"],
        "source_project_id": plan["source"]["project_id"],
        "run_id": plan["run_id"],
        "source_verdict": plan["source"]["verdict"],
        "created_at": datetime.now(UTC).isoformat(),
    }


def _append_segment_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def resolve_cost_budget(args: argparse.Namespace) -> float | None:
    """Task 193.r: 成本预算解析 — 显式 --cost-budget 优先，回读 SONGYAN_RUN_COST_BUDGET."""
    value = getattr(args, "cost_budget", None)
    if value is not None:
        return float(value)
    raw = os.environ.get("SONGYAN_RUN_COST_BUDGET")
    if raw:
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def apply_cost_budget(value: float) -> None:
    """Task 193.r: 预算写入运行时 settings（与 database_url 覆写同进程作用域）."""
    from songyan.config import settings

    settings.run_cost_budget = float(value)


def build_status_payload(genre: str, paths: HarnessPaths) -> dict[str, Any]:
    """Collect no-write status for a V10 target DB."""
    project_info = _load_project_file(paths.project_file)
    db_exists = paths.db.exists()
    project_id = project_info.get("project_id") if project_info else None
    accepted = _accepted_summary(paths.db, project_id) if db_exists and project_id else None
    run_info = _run_summary(paths.db, project_id) if db_exists and project_id else None
    cost_budget = resolve_cost_budget(argparse.Namespace(cost_budget=None))
    next_step = "run --init-from-source with a CONTINUE_READY source"
    if db_exists and project_info:
        next_step = "run --audit --up-to <checkpoint> or --to <checkpoint>"
    return {
        "task": TASK_ID,
        "action": "status",
        "genre": genre,
        "paths": paths.to_dict(),
        "db_exists": db_exists,
        "project_file_exists": paths.project_file.exists(),
        "project": project_info,
        "accepted": accepted,
        "run": run_info,
        "cost_budget": cost_budget,
        "next_step": next_step,
    }


def _run_summary(db_path: Path, project_id: str | None) -> dict[str, Any] | None:
    """Task 193.r: --status 展示最新 run 状态（含 pause_reason；旧库无列回退 None）."""
    if project_id is None:
        return None
    try:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cols = {
            row[1] for row in conn.execute("PRAGMA table_info(project_runs)").fetchall()
        }
        select = "run_id, status, current_chapter, total_cost, updated_at"
        if "pause_reason" in cols:
            select += ", pause_reason"
        row = conn.execute(
            f"""SELECT {select} FROM project_runs
                WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1""",
            (project_id,),
        ).fetchone()
        conn.close()
    except sqlite3.Error as exc:
        return {"error": str(exc)}
    if row is None:
        return None
    info = dict(zip(select.split(", "), row, strict=True))
    info.setdefault("pause_reason", None)
    return info


def _load_project_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"error": f"invalid project file: {path.as_posix()}"}
    return raw if isinstance(raw, dict) else {"error": f"invalid project file: {path.as_posix()}"}


def _accepted_summary(db_path: Path, project_id: str | None) -> dict[str, Any] | None:
    if project_id is None:
        return None
    try:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        row = conn.execute(
            """SELECT COUNT(*), MIN(chapter_number), MAX(chapter_number)
               FROM chapter_heads
               WHERE project_id = ? AND accepted_version_id IS NOT NULL""",
            (project_id,),
        ).fetchone()
        conn.close()
    except sqlite3.Error as exc:
        return {"error": str(exc)}
    count, first, last = row
    return {"count": count, "first": first, "last": last}


def build_audit_plan(
    *,
    genre: str,
    args: argparse.Namespace,
    paths: HarnessPaths,
) -> dict[str, Any]:
    """Build checkpoint audit commands and paths."""
    up_to = _resolve_checkpoint(args.up_to)
    project_info = _load_project_file(paths.project_file) or {}
    project_id = args.source_project_id or project_info.get("project_id")
    if project_id is None:
        if not args.dry_run:
            raise HarnessError("missing project_id; run --init-from-source first")
        project_id = "<project_id>"
    commands = _audit_commands(
        genre=genre,
        db_path=paths.db,
        project_id=str(project_id),
        up_to=up_to,
        baseline=args.baseline,
        metrics_path=paths.metrics(up_to),
    )
    return {
        "task": TASK_ID,
        "action": "audit",
        "dry_run": bool(args.dry_run),
        "genre": genre,
        "up_to": up_to,
        "baseline": args.baseline.as_posix(),
        "paths": paths.to_dict(up_to),
        "commands": commands,
        "environment": {
            "DATABASE_URL": f"sqlite:///{paths.db.as_posix()}",
            "cleanup": "remove DATABASE_URL after metrics/audit",
        },
    }


def _resolve_checkpoint(up_to: int | None) -> int:
    if up_to is None:
        raise HarnessError("--audit requires --up-to")
    if up_to not in CHECKPOINTS:
        raise HarnessError(f"checkpoint must be one of {CHECKPOINTS}; got {up_to}")
    return up_to


def _audit_commands(
    *,
    genre: str,
    db_path: Path,
    project_id: str,
    up_to: int,
    baseline: Path,
    metrics_path: Path,
) -> dict[str, list[str]]:
    return {
        "five_gate": [
            sys.executable,
            "scripts/five_gate_check.py",
            "--genre",
            genre,
            "--db",
            db_path.as_posix(),
            "--project-id",
            project_id,
            "--up-to",
            str(up_to),
            "--baseline",
            baseline.as_posix(),
            "--format",
            "json",
        ],
        "segment_audit": [
            sys.executable,
            "scripts/segment_audit.py",
            "--db",
            db_path.as_posix(),
            "--project-id",
            project_id,
            "--up-to",
            str(up_to),
            "--genre",
            genre,
            "--format",
            "json",
        ],
        "metrics": [
            "songyan",
            "metrics",
            "--project-id",
            project_id,
            "--chapters",
            f"1-{up_to}",
            "-o",
            metrics_path.as_posix(),
        ],
    }


def _load_json_output(raw: str) -> dict[str, Any] | None:
    """Parse a captured command stdout as JSON; None when not JSON."""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _build_audit_verdict(
    plan: dict[str, Any],
    five_gate: dict[str, Any] | None,
    segment: dict[str, Any] | None,
) -> dict[str, Any]:
    """Task 193.w F2/F3: 段审计 verdict 块.

    five_gate / segment_audit 脚本的退出码不承载判定（segment_audit 恒 0），
    必须解析 JSON 输出上浮 verdict；stale health 预警（192.aw 型）：health
    报告滞后审计点 >= 2 章时提示先补跑 continuity audit 再判 health 门。
    """
    up_to = int(plan.get("up_to") or 0)
    metrics = five_gate.get("metrics") if five_gate else None
    health_chapter = (
        metrics.get("health_report_chapter") if isinstance(metrics, dict) else None
    )
    stale = (
        isinstance(health_chapter, int)
        and up_to > 0
        and (up_to - health_chapter) >= 2
    )
    verdict: dict[str, Any] = {
        "five_gate": five_gate.get("verdict") if five_gate else None,
        "segment_halt_would_fire": (
            bool(segment.get("halt_would_fire")) if segment else None
        ),
        "critical_orphans": segment.get("critical_orphans") if segment else None,
        "health_report_chapter": health_chapter,
        "stale_health_warning": stale,
    }
    if stale:
        verdict["health_note"] = (
            f"health 报告 @Ch{health_chapter} 滞后于审计点 Ch{up_to}（192.aw 型）；"
            f"若 health 门 FAIL，先补跑 continuity audit 到 Ch{up_to} 再判定"
        )
    return verdict


def run_audit(plan: dict[str, Any]) -> dict[str, Any]:
    """Execute audit commands and write outputs."""
    paths = plan["paths"]
    db_path = Path(paths["db"])
    if not db_path.exists():
        raise HarnessError(f"target DB does not exist: {db_path}")
    outputs = {
        "five_gate": Path(paths["five_gate"]),
        "segment_audit": Path(paths["segment_audit"]),
        "metrics": Path(paths["metrics"]),
    }
    for output in outputs.values():
        output.parent.mkdir(parents=True, exist_ok=True)

    five_gate = _run_capture(plan["commands"]["five_gate"])
    outputs["five_gate"].write_text(five_gate.stdout, encoding="utf-8")
    segment = _run_capture(plan["commands"]["segment_audit"])
    outputs["segment_audit"].write_text(segment.stdout, encoding="utf-8")

    env = os.environ.copy()
    env["DATABASE_URL"] = plan["environment"]["DATABASE_URL"]
    metrics = _run_capture(plan["commands"]["metrics"], env=env)
    verdict = _build_audit_verdict(
        plan,
        _load_json_output(five_gate.stdout),
        _load_json_output(segment.stdout),
    )
    return {
        **plan,
        "dry_run": False,
        "verdict": verdict,
        "exit_codes": {
            "five_gate": five_gate.returncode,
            "segment_audit": segment.returncode,
            "metrics": metrics.returncode,
        },
        "outputs": {key: value.as_posix() for key, value in outputs.items()},
    }


def _run_capture(
    command: list[str],
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise HarnessError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr}"
        )
    return result


def build_to_plan(
    *,
    genre: str,
    args: argparse.Namespace,
    paths: HarnessPaths,
) -> dict[str, Any]:
    """Build run-to-checkpoint plan."""
    target = _resolve_checkpoint(args.to)
    project_info = _load_project_file(paths.project_file) or {}
    project_id = project_info.get("project_id")
    run_id = args.run_id or project_info.get("run_id") or f"run-v10-{genre}-{uuid.uuid4().hex[:8]}"
    cost_budget = resolve_cost_budget(args)
    on_failure = str(getattr(args, "on_failure", "isolate") or "isolate")
    wrapper_command = [
        "powershell",
        "-File",
        "scripts/run_with_timeout.ps1",
        "-TimeoutSec",
        "<sec>",
        "-SuccessMarkerRegex",
        f"accepted.*{target}/{target}|project_pipeline\\.end.*final_status=completed",
        "--",
        sys.executable,
        "scripts/run_v10_ch200_climb.py",
        "--to",
        str(target),
        "--genre",
        genre,
        "--cost-budget",
        str(cost_budget) if cost_budget is not None else "<required>",
    ]
    if on_failure != "isolate":
        wrapper_command.extend(["--on-failure", on_failure])
    return {
        "task": TASK_ID,
        "action": "to",
        "dry_run": bool(args.dry_run),
        "genre": genre,
        "target": target,
        "project_id": project_id,
        "run_id": run_id,
        "cost_budget": cost_budget,
        "on_failure": on_failure,
        "paths": paths.to_dict(target),
        "baseline": args.baseline.as_posix(),
        "wrapper_command": wrapper_command,
        "next_step": "run via wrapper; Task 191 validation must use dry-run only",
    }


async def ensure_target_schema(db_path: Path) -> None:
    """Task 193.u: --to 前保证目标库 schema 与代码一致.

    旧 source 复制库（如 172b 时代 DB）可能缺少后续 additive 迁移列
    （如 193.r 的 project_runs.pause_reason）；harness 路径不经 CLI 的
    init_schema，需在 pipeline 启动前显式迁移。init_schema 幂等。
    """
    from songyan.db.migrations import init_schema

    await init_schema(db_path)


async def run_to_checkpoint(plan: dict[str, Any]) -> dict[str, Any]:
    """Run real generation to a checkpoint.  Not used by Task 191 validation."""
    from songyan.config import settings
    from songyan.db.repository import ProjectRepository
    from songyan.models import GateConfig
    from songyan.workflows.phase2_graph import run_project_pipeline

    db_path = Path(plan["paths"]["db"])
    if not db_path.exists():
        raise HarnessError(f"target DB does not exist: {db_path}")
    project_id = plan.get("project_id")
    if not project_id:
        raise HarnessError("missing project_id in V10 project file")
    run_id = str(plan["run_id"])
    if not _run_exists(db_path, run_id):
        raise HarnessError(
            f"V10 run_id does not exist in target DB: {run_id}; "
            "re-run --init-from-source for this target DB"
        )
    await ensure_target_schema(db_path)
    settings.database_url = f"sqlite:///{db_path.as_posix()}"
    cost_budget = plan.get("cost_budget")
    if cost_budget is None:
        raise HarnessError(
            "missing cost budget; pass --cost-budget <CNY> or set SONGYAN_RUN_COST_BUDGET"
        )
    apply_cost_budget(float(cost_budget))
    project = await ProjectRepository().get(str(project_id))
    if project is None:
        raise HarnessError(f"project not found: {project_id}")
    result = await run_project_pipeline(
        str(project_id),
        chapter_range=(1, int(plan["target"])),
        mode_id=project.mode_id,
        auto_confirm=True,
        on_failure=str(plan.get("on_failure") or "isolate"),
        gate_config=GateConfig.for_mode("enforce"),
        resume=True,
        run_id=run_id,
    )
    return {
        **plan,
        "dry_run": False,
        "result": {
            "run_id": result.run_id,
            "completed": result.chapters_completed,
            "failed": result.chapters_failed,
            "final_status": result.final_status,
            "total_cost": result.total_cost,
        },
    }


def _run_exists(db_path: Path, run_id: str) -> bool:
    conn: sqlite3.Connection | None = None
    try:
        conn = _connect_readonly(db_path)
        row = conn.execute(
            "SELECT 1 FROM project_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def emit(payload: dict[str, Any], output_format: str) -> None:
    """Print payload as text or JSON."""
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key}: {value}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        genre = resolve_genre(args)
        paths = harness_paths(genre, args.work_dir)
        if args.init or args.init_from_source:
            inventory = load_inventory(args.inventory, args.canonical_inventory)
            plan = build_init_plan(genre=genre, args=args, inventory=inventory, paths=paths)
            if args.dry_run:
                payload = plan
            elif args.init:
                payload = prepare_paths(plan)
            else:
                payload = init_from_source(plan, force=args.force)
        elif args.status:
            payload = build_status_payload(genre, paths)
        elif args.audit:
            plan = build_audit_plan(genre=genre, args=args, paths=paths)
            payload = plan if args.dry_run else run_audit(plan)
        elif args.to is not None:
            plan = build_to_plan(genre=genre, args=args, paths=paths)
            if not args.dry_run and plan["cost_budget"] is None:
                raise HarnessError(
                    "real --to requires a cost budget: pass --cost-budget <CNY> "
                    "or set SONGYAN_RUN_COST_BUDGET (V10 执行纪律第 6 条)"
                )
            payload = plan if args.dry_run else asyncio.run(run_to_checkpoint(plan))
        else:
            raise HarnessError("no action selected")
    except HarnessError as exc:
        if args.format == "json":
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"run_v10_ch200_climb error: {exc}", file=sys.stderr)
        return 2
    emit(payload, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
