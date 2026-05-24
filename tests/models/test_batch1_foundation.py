"""Batch 1: Foundation models — project, character, chapter, genre."""

import pytest
from pydantic import ValidationError

from songyan.models.chapter import ChapterGoal, ChapterHead, ChapterVersion
from songyan.models.character import Character, CharacterState
from songyan.models.genre import GenreProfile
from songyan.models.project import ProjectSetting


class TestProjectSetting:
    """ProjectSetting 测试."""

    def test_minimal_instantiation(self) -> None:
        """最小必填字段实例化."""
        s = ProjectSetting(
            genre_id="xuanhuan",
            protagonist_name="王林",
        )
        assert s.genre_id == "xuanhuan"
        assert s.protagonist_name == "王林"

    def test_defaults(self) -> None:
        """默认值正确."""
        s = ProjectSetting(
            genre_id="xuanhuan",
            protagonist_name="王林",
        )
        assert s.mode_id == "webnovel"
        assert s.target_word_count == 100_000
        assert s.tone == "热血"
        assert s.taboos == []
        assert s.title is None

    def test_full_instantiation(self) -> None:
        """全字段实例化."""
        s = ProjectSetting(
            title="仙逆",
            genre_id="xuanhuan",
            mode_id="webnovel",
            protagonist_name="王林",
            protagonist_background="平凡少年",
            core_hook="逆修成仙",
            target_reader_expectation="热血升级",
            taboos=["绿帽", "圣母"],
            target_word_count=300_000,
            tone="冷酷",
            reference_works=["凡人修仙传"],
        )
        assert s.title == "仙逆"
        assert s.taboos == ["绿帽", "圣母"]

    def test_missing_required_raises(self) -> None:
        """必填字段缺失抛 ValidationError."""
        with pytest.raises(ValidationError):
            ProjectSetting()  # genre_id 和 protagonist_name 都是必填


class TestCharacter:
    """Character 测试."""

    def test_instantiation(self) -> None:
        c = Character(
            character_id="char-001",
            project_id="proj-001",
            name="王林",
        )
        assert c.name == "王林"
        assert c.role_type == "protagonist"

    def test_defaults(self) -> None:
        c = Character(
            character_id="char-001",
            project_id="proj-001",
            name="王林",
        )
        assert c.background == ""
        assert c.personality_traits == []
        assert c.relationships == {}


class TestCharacterState:
    """CharacterState 测试."""

    def test_instantiation(self) -> None:
        cs = CharacterState(
            character_id="char-001",
            field="cultivation_level",
            value="筑基初期",
        )
        assert cs.value == "筑基初期"
        assert cs.source_version_id == ""


class TestChapterGoal:
    """ChapterGoal 测试."""

    def test_minimal_instantiation(self) -> None:
        g = ChapterGoal(chapter_number=1)
        assert g.chapter_number == 1
        assert g.word_count_target == 3000

    def test_defaults(self) -> None:
        g = ChapterGoal(chapter_number=1)
        assert g.target_events == []
        assert g.hooks == []
        assert g.chapter_type == ""
        assert g.previous_summary == ""

    def test_full_instantiation(self) -> None:
        g = ChapterGoal(
            chapter_number=1,
            previous_summary="主角离开山村",
            target_events=["发现神秘洞穴"],
            emotional_arc="好奇→紧张",
            hooks=["洞穴深处传来低语"],
            obligations=["不能暴露身份"],
            word_count_target=3500,
            chapter_type="布局章",
        )
        assert g.chapter_type == "布局章"
        assert len(g.target_events) == 1


class TestChapterVersion:
    """ChapterVersion 测试."""

    def test_instantiation(self) -> None:
        v = ChapterVersion(
            version_id="v-001",
            project_id="proj-001",
            chapter_number=1,
        )
        assert v.version_type == "draft"
        assert v.word_count == 0
        assert v.parent_version_id is None

    def test_version_types(self) -> None:
        """版本类型可设置为所有合法值."""
        for vt in ("draft", "revision", "accepted", "edited"):
            v = ChapterVersion(
                version_id=f"v-{vt}",
                project_id="proj-001",
                chapter_number=1,
                version_type=vt,
            )
            assert v.version_type == vt

    def test_foreign_keys(self) -> None:
        """外键引用为字符串 ID."""
        v = ChapterVersion(
            version_id="v-001",
            project_id="proj-001",
            chapter_number=1,
            creative_brief_id="brief-001",
            literary_observation_id="lit-001",
            parent_version_id="v-000",
        )
        assert v.creative_brief_id == "brief-001"


class TestChapterHead:
    """ChapterHead 测试."""

    def test_instantiation(self) -> None:
        h = ChapterHead(
            project_id="proj-001",
            chapter_number=1,
        )
        assert h.status == "draft"
        assert h.current_version_id is None


class TestGenreProfile:
    """GenreProfile 测试."""

    def test_instantiation(self) -> None:
        gp = GenreProfile(
            id="xuanhuan",
            name="玄幻",
        )
        assert gp.id == "xuanhuan"
        assert gp.language == "zh"

    def test_defaults(self) -> None:
        gp = GenreProfile(id="xuanhuan", name="玄幻")
        assert gp.fatigue_words == []
        assert gp.has_numerical_system is False
        assert gp.pacing_rule == ""

    def test_from_dict(self) -> None:
        """从 dict 加载."""
        data = {
            "id": "xuanhuan",
            "name": "玄幻",
            "chapter_types": ["战斗章", "布局章"],
            "fatigue_words": ["冷笑", "蝼蚁"],
            "has_numerical_system": True,
        }
        gp = GenreProfile.from_dict(data)
        assert gp.id == "xuanhuan"
        assert "战斗章" in gp.chapter_types
        assert gp.has_numerical_system is True

    def test_from_dict_full(self) -> None:
        """从完整 dict 加载（模拟 JSON 配置文件）."""
        data = {
            "id": "xuanhuan",
            "name": "玄幻",
            "language": "zh",
            "chapter_types": ["战斗章", "布局章", "过渡章", "回收章"],
            "fatigue_words": ["冷笑", "蝼蚁", "倒吸凉气"],
            "satisfaction_types": ["打脸", "升级突破"],
            "has_numerical_system": True,
            "has_power_scaling": True,
            "pacing_rule": "三章内必有明确反馈",
            "writer_rules": ["设定不可吃书"],
            "reviewer_focus": ["战力体系一致性"],
            "active_audit_dimensions": ["genre_numerical"],
            "taboos": ["绿帽"],
        }
        gp = GenreProfile.from_dict(data)
        assert gp.taboos == ["绿帽"]
        assert gp.active_audit_dimensions == ["genre_numerical"]
