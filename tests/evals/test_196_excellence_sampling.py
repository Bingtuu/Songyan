"""Task 196 excellence_sampling 测试."""
from __future__ import annotations

import sqlite3  # noqa: F401  # 后续 Task 追加测试使用
from pathlib import Path  # noqa: F401  # 后续 Task 追加测试使用

import pytest
from pydantic import ValidationError

from songyan.evals.excellence_sampling import (
    DEFAULT_SEED,
    AnnotationRecord,
    AnnotationScores,  # noqa: F401  # 后续 Task 追加测试使用
    ExcellenceSamplingError,
    SampledChapter,
    load_accepted_chapters,  # noqa: F401  # 后续 Task 追加测试使用
    stratified_sample,
)


def _make_chapters(genre: str = "xuanhuan", count: int = 200) -> list[SampledChapter]:
    return [
        SampledChapter(
            genre=genre,
            chapter_number=i,
            version_id=f"v-{genre}-{i:03d}",
            segment=(i - 1) // 25 + 1,
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
