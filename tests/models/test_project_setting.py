"""Tests for ProjectSetting model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from songyan.models import ProjectSetting


class TestProjectSettingDefaults:
    def test_defaults(self) -> None:
        setting = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
        )
        assert setting.estimated_chapters == 30
        assert setting.words_per_chapter == 3000
        assert setting.story_structure == "free"
        assert setting.arc_boundaries_auto is False
        assert setting.sub_genre_id is None

    def test_word_range_property(self) -> None:
        setting = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
            words_per_chapter=3000,
        )
        assert setting.word_range == (2400, 3600)

    def test_word_range_with_custom_value(self) -> None:
        setting = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
            words_per_chapter=5000,
        )
        assert setting.word_range == (4000, 6000)

    def test_story_structure_valid_values(self) -> None:
        for struct in ["three_act", "five_act", "serial", "free"]:
            setting = ProjectSetting(
                genre_id="scifi",
                protagonist_name="Zhang",
                story_structure=struct,
            )
            assert setting.story_structure == struct

    def test_story_structure_invalid_value_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectSetting(
                genre_id="scifi",
                protagonist_name="Zhang",
                story_structure="invalid",
            )

    def test_boundary_values(self) -> None:
        setting = ProjectSetting(
            genre_id="scifi",
            protagonist_name="Zhang",
            estimated_chapters=1,
            words_per_chapter=500,
        )
        assert setting.estimated_chapters == 1
        assert setting.words_per_chapter == 500
        assert setting.word_range == (400, 600)

    def test_full_fields(self) -> None:
        setting = ProjectSetting(
            title="Orbital Horror",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="Zhang",
            protagonist_background="engineer",
            core_hook="survive",
            target_reader_expectation="thriller",
            taboos=["jump scare"],
            target_word_count=100_000,
            tone="dark",
            reference_works=["Alien"],
            arc_boundaries=[10, 20],
            volume_boundaries=[15],
            estimated_chapters=50,
            words_per_chapter=3500,
            story_structure="three_act",
            arc_boundaries_auto=True,
            sub_genre_id="cosmic_horror",
        )
        assert setting.estimated_chapters == 50
        assert setting.words_per_chapter == 3500
        assert setting.story_structure == "three_act"
        assert setting.arc_boundaries_auto is True
        assert setting.sub_genre_id == "cosmic_horror"
        assert setting.word_range == (2800, 4200)
