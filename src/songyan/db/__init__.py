"""Songyan database layer — schema, connection, migrations, repositories."""

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.connection import get_db, get_db_path
from songyan.db.context_repo import CharacterStateRepository, SummaryRepository
from songyan.db.human_mark_repo import HumanMarkRepository
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
    "ChunkRepository",
    "ChapterGoalRepository",
    "ChapterHeadRepository",
    "ChapterVersionRepository",
    "CharacterRepository",
    "CharacterStateRepository",
    "CreativeBriefRepository",
    "ForeshadowingRepository",
    "HumanMarkRepository",
    "LiteraryObservationRepository",
    "NumericalLedgerRepository",
    "ProjectRepository",
    "ReviewReportRepository",
    "SettingSnapshotRepository",
    "SummaryRepository",
    "get_db",
    "get_db_path",
    "init_schema",
    "verify_schema",
]
