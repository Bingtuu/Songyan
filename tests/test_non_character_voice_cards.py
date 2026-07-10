"""Task 170g Phase 2: 非角色声源声纹卡补漏测试."""

from __future__ import annotations

from songyan.models.character import DialogueStyleCard
from songyan.workflows._helpers import _build_non_character_voice_cards


class TestNonCharacterVoiceCards:
    def test_builds_cards_for_non_character_voices(self) -> None:
        appeared = {"林渊", "建造者", "残影", "舰队之手"}
        existing = {"林渊"}
        cards = _build_non_character_voice_cards(appeared, "proj-001", existing)
        names = {c.character_id for c in cards}
        assert "voice-建造者" in names
        assert "voice-残影" in names
        assert "voice-舰队之手" in names
        assert "voice-林渊" not in names
        assert all(isinstance(c, DialogueStyleCard) for c in cards)
        assert all(c.project_id == "proj-001" for c in cards)

    def test_skips_unknown_names(self) -> None:
        appeared = {"林渊", "某个路人"}
        existing = {"林渊"}
        cards = _build_non_character_voice_cards(appeared, "proj-001", existing)
        assert not cards

    def test_existing_character_name_skipped(self) -> None:
        appeared = {"建造者"}
        existing = {"建造者"}
        cards = _build_non_character_voice_cards(appeared, "proj-001", existing)
        assert not cards

    def test_style_fields_populated(self) -> None:
        cards = _build_non_character_voice_cards({"守门人"}, "proj-001", set())
        assert len(cards) == 1
        card = cards[0]
        assert card.sentence_length_preference == "medium"
        assert card.common_openers
        assert card.anger_expression
        assert card.social_role_speech_pattern
