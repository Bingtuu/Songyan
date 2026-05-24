"""Songyan database layer — schema, connection, migrations, repositories."""

from songyan.db.connection import get_db, get_db_path
from songyan.db.migrations import init_schema, verify_schema
from songyan.db.repository import (
    ChapterGoalRepository,
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.review_repo import (
    CreativeBriefRepository,
    LiteraryObservationRepository,
    ReviewReportRepository,
)
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)

__all__ = [
    "ChapterGoalRepository",
    "ChapterHeadRepository",
    "ChapterVersionRepository",
    "CharacterRepository",
    "CreativeBriefRepository",
    "ForeshadowingRepository",
    "LiteraryObservationRepository",
    "NumericalLedgerRepository",
    "ProjectRepository",
    "ReviewReportRepository",
    "SettingSnapshotRepository",
    "get_db",
    "get_db_path",
    "init_schema",
    "verify_schema",
]
