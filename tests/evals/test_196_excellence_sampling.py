"""Task 196 excellence_sampling 测试."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from songyan.evals.excellence_sampling import (
    DEFAULT_SEED,
    SEGMENT_SIZE,
    AnnotationRecord,
    ExcellenceSamplingError,
    SampledChapter,
    load_accepted_chapters,
    load_chapter_content,
    stratified_sample,
)


def _make_chapters(genre: str = "xuanhuan", count: int = 200) -> list[SampledChapter]:
    return [
        SampledChapter(
            genre=genre,
            chapter_number=i,
            version_id=f"v-{genre}-{i:03d}",
            segment=(i - 1) // SEGMENT_SIZE + 1,
        )
        for i in range(1, count + 1)
    ]


class TestStratifiedSample:
    def test_reproducible_with_fixed_seed(self) -> None:
        chapters = _make_chapters()
        first = stratified_sample(chapters, seed=DEFAULT_SEED)
        second = stratified_sample(chapters, seed=DEFAULT_SEED)
        assert [c.version_id for c in first] == [c.version_id for c in second]

    def test_count_and_segment_coverage(self) -> None:
        picked = stratified_sample(_make_chapters(), seed=DEFAULT_SEED)
        assert len(picked) == 30
        segments = {c.segment for c in picked}
        assert segments == set(range(1, 9))  # 8 个 25 章弧段全覆盖

    def test_segment_quotas(self) -> None:
        picked = stratified_sample(_make_chapters(), seed=DEFAULT_SEED)
        quotas = [sum(1 for c in picked if c.segment == s) for s in range(1, 9)]
        assert quotas == [4, 4, 4, 4, 4, 4, 3, 3]  # 30 = 8*3 + 6，余数给前 6 段

    def test_result_sorted_by_chapter(self) -> None:
        picked = stratified_sample(_make_chapters(), seed=DEFAULT_SEED)
        numbers = [c.chapter_number for c in picked]
        assert numbers == sorted(numbers)

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ExcellenceSamplingError):
            stratified_sample([], seed=DEFAULT_SEED)


class TestAnnotationRecord:
    def _valid(self) -> dict:
        return {
            "genre": "xuanhuan",
            "chapter": 87,
            "version_id": "v-x-087",
            "sample_layer": "anchor",
            "scores": {"homogeneity": 3, "tension": 4, "ai_tone": 2, "overall": 4},
            "rationale": "测试",
            "annotator": "agent-deep-read",
        }

    def test_valid_record(self) -> None:
        rec = AnnotationRecord(**self._valid())
        assert rec.disagreement is None
        assert rec.evidence_quotes == []

    @pytest.mark.parametrize("score", [0, 6])
    def test_score_out_of_range_rejected(self, score: int) -> None:
        data = self._valid()
        data["scores"]["tension"] = score
        with pytest.raises(ValidationError):
            AnnotationRecord(**data)

    def test_invalid_layer_rejected(self) -> None:
        data = self._valid()
        data["sample_layer"] = "unknown"
        with pytest.raises(ValidationError):
            AnnotationRecord(**data)


def _init_db(db_path: Path, project_id: str = "p1", chapters: int = 200) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT, chapter_number INTEGER,
            accepted_version_id TEXT, status TEXT );
        CREATE TABLE chapter_versions (
            version_id TEXT, project_id TEXT, chapter_number INTEGER,
            content TEXT, parent_version_id TEXT );
        """
    )
    heads = [
        (project_id, i, f"v-{i:03d}", "accepted") for i in range(1, chapters + 1)
    ]
    versions = [
        (f"v-{i:03d}", project_id, i, f"第{i}章正文", None)
        for i in range(1, chapters + 1)
    ]
    conn.executemany("INSERT INTO chapter_heads VALUES (?, ?, ?, ?)", heads)
    conn.executemany("INSERT INTO chapter_versions VALUES (?, ?, ?, ?, ?)", versions)
    conn.commit()
    conn.close()


class TestLoadAcceptedChapters:
    def test_loads_200_chapters(self, tmp_path: Path) -> None:
        db = tmp_path / "t.db"
        _init_db(db)
        conn = sqlite3.connect(db)
        chapters = load_accepted_chapters(conn, "p1", "xuanhuan")
        conn.close()
        assert len(chapters) == 200
        assert chapters[0].segment == 1
        assert chapters[-1].segment == 8
        assert chapters[86].version_id == "v-087"

    def test_unknown_project_raises(self, tmp_path: Path) -> None:
        db = tmp_path / "t.db"
        _init_db(db)
        conn = sqlite3.connect(db)
        with pytest.raises(ExcellenceSamplingError):
            load_accepted_chapters(conn, "no-such", "xuanhuan")
        conn.close()

    def test_null_and_dangling_heads_excluded(self, tmp_path: Path) -> None:
        """JOIN/WHERE 口径：NULL accepted_version_id 与悬空 head 均不得入选."""
        db = tmp_path / "t.db"
        _init_db(db)
        conn = sqlite3.connect(db)
        conn.executemany(
            "INSERT INTO chapter_heads VALUES (?, ?, ?, ?)",
            [
                ("p1", 201, None, "draft"),  # accepted_version_id = NULL
                ("p1", 202, "v-dangling", "accepted"),  # 无匹配 chapter_versions 行
            ],
        )
        conn.commit()
        chapters = load_accepted_chapters(conn, "p1", "xuanhuan")
        conn.close()
        assert len(chapters) == 200
        assert all(c.version_id != "v-dangling" for c in chapters)
        assert {c.chapter_number for c in chapters} == set(range(1, 201))


class TestLoadChapterContent:
    def test_returns_content(self, tmp_path: Path) -> None:
        db = tmp_path / "t.db"
        _init_db(db)
        conn = sqlite3.connect(db)
        assert load_chapter_content(conn, "v-087") == "第87章正文"
        conn.close()

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        db = tmp_path / "t.db"
        _init_db(db)
        conn = sqlite3.connect(db)
        with pytest.raises(ExcellenceSamplingError):
            load_chapter_content(conn, "v-missing")
        conn.close()


class TestPrelabelCard:
    def test_card_loads_and_renders(self) -> None:
        from songyan.prompts.loader import get_prompt_loader, reset_prompt_loader

        reset_prompt_loader()
        loader = get_prompt_loader()
        card = loader.load_card("excellence_prelabel")
        rendered = loader.render_card(
            card, {"genre": "xuanhuan", "chapter_content": "测试正文"}
        )
        text = rendered.system_prompt
        assert "测试正文" in text
        assert "homogeneity" in text
        reset_prompt_loader()
