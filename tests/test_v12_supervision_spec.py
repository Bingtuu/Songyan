from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from songyan.models import BeatSpec, SupervisionSpec
from songyan.services.supervision_spec import (
    SupervisionSpecError,
    load_project_supervision_spec,
    load_supervision_spec_data,
    load_supervision_spec_file,
)


def _valid_spec_data() -> dict[str, object]:
    beat = {
        "visible_action": "沈砚复核 C 区七号舱当前门禁响应。",
        "current_friction": "门禁返回同一尾标，但责任栏为空。",
        "feedback": "终端只显示当前舱压和货物质量，不显示历史日志。",
        "micro_decision": "沈砚决定先保存当前响应，不提交确认。",
        "landing": "尾标被抄到离线纸面记录。",
    }
    return {
        "version": "v12.1",
        "stage": "startup_ch1_3",
        "word_count": {
            "target": 3000,
            "hard_min": 2700,
            "hard_max": 3300,
            "soft_min": 2850,
            "soft_max": 3150,
        },
        "review": {
            "go_conditions": ["Ch1-Ch3 reading review = GO"],
            "stop_conditions": ["不得进入 Ch1-Ch10"],
        },
        "chapters": {
            "1": {
                "allowed_beats": [beat],
                "required_phrases": ["沈砚决定只保存当前证据，不提交确认。"],
                "forbidden_literals": ["三天前", "沈弥账号"],
                "forbidden_patterns": [r"\d+\.\d+,\s*\d+\.\d+"],
                "stage_policy": {
                    "allow_new_characters": False,
                    "allow_past_backstory": False,
                    "allow_cross_location_chase": False,
                    "allow_identity_secret_reveal": False,
                    "allow_relative_time": False,
                    "allow_coordinates": False,
                },
                "review": {
                    "go_conditions": ["当前动作完整"],
                    "stop_conditions": ["出现旧事故"],
                },
            }
        },
    }


def test_load_supervision_spec_data_validates_startup_contract() -> None:
    spec = load_supervision_spec_data(_valid_spec_data())

    assert spec.stage == "startup_ch1_3"
    assert spec.word_count.hard_min == 2700
    assert spec.word_count.hard_max == 3300
    assert spec.required_phrases_for_chapter(1) == [
        "沈砚决定只保存当前证据，不提交确认。"
    ]
    assert spec.forbidden_literals_for_chapter(1) == ["三天前", "沈弥账号"]


def test_supervision_spec_exposes_beat_sheet_for_writer_contract() -> None:
    spec = SupervisionSpec.model_validate(_valid_spec_data())

    beats = spec.beat_sheet_for_chapter(1)

    assert len(beats) == 1
    assert isinstance(beats[0], BeatSpec)
    assert beats[0].visible_action.startswith("沈砚复核")
    assert beats[0].micro_decision == "沈砚决定先保存当前响应，不提交确认。"


def test_supervision_spec_compiles_forbidden_patterns() -> None:
    spec = load_supervision_spec_data(_valid_spec_data())

    patterns = spec.forbidden_patterns_for_chapter(1)

    assert len(patterns) == 1
    assert isinstance(patterns[0], re.Pattern)
    assert patterns[0].search("坐标 31.23, 121.47") is not None


def test_invalid_word_count_window_is_structured_error() -> None:
    data = _valid_spec_data()
    data["word_count"] = {"target": 3000, "hard_min": 3301, "hard_max": 3300}

    with pytest.raises(SupervisionSpecError) as exc_info:
        load_supervision_spec_data(data)

    assert "hard_min must be <= target" in str(exc_info.value)


def test_invalid_regex_is_rejected_at_load_time() -> None:
    data = _valid_spec_data()
    chapters = data["chapters"]
    assert isinstance(chapters, dict)
    chapter_1 = chapters["1"]
    assert isinstance(chapter_1, dict)
    chapter_1["forbidden_patterns"] = ["["]

    with pytest.raises(SupervisionSpecError) as exc_info:
        load_supervision_spec_data(data)

    assert "invalid forbidden pattern" in str(exc_info.value)


def test_empty_beat_field_is_rejected() -> None:
    data = _valid_spec_data()
    chapters = data["chapters"]
    assert isinstance(chapters, dict)
    chapter_1 = chapters["1"]
    assert isinstance(chapter_1, dict)
    beats = chapter_1["allowed_beats"]
    assert isinstance(beats, list)
    beat = beats[0]
    assert isinstance(beat, dict)
    beat["current_friction"] = " "

    with pytest.raises(SupervisionSpecError) as exc_info:
        load_supervision_spec_data(data)

    assert "current_friction" in str(exc_info.value)


def test_load_supervision_spec_file_requires_json_object(tmp_path: Path) -> None:
    path = tmp_path / "supervision_spec.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(SupervisionSpecError) as exc_info:
        load_supervision_spec_file(path)

    assert "top-level value must be a JSON object" in str(exc_info.value)


def test_load_project_supervision_spec_uses_default_asset_path(tmp_path: Path) -> None:
    spec_dir = tmp_path / "planning"
    spec_dir.mkdir()
    (spec_dir / "supervision_spec.json").write_text(
        json.dumps(_valid_spec_data(), ensure_ascii=False),
        encoding="utf-8",
    )

    spec = load_project_supervision_spec(tmp_path)

    assert spec.chapter(1).stage_policy.allow_new_characters is False
    assert spec.chapter(1).review.stop_conditions == ["出现旧事故"]

