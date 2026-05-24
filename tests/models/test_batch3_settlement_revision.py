"""Batch 3: Settlement and revision models."""

import pytest
from pydantic import ValidationError

from songyan.models.review import ReviewCategory, ReviewIssue
from songyan.models.revision import RevisionInput, Patch, RevisionOutput
from songyan.models.settlement import (
    StateSettlement,
    CharacterUpdate,
    NewSetting,
    ForeshadowingUpdate,
    NumericalUpdate,
    Increment,
    Decrement,
)


class TestPatch:
    """Patch 测试."""

    def test_instantiation(self) -> None:
        p = Patch(
            issue_id="i-001",
            original_text="他不禁一怔",
            revised_text="他停住了脚步",
            location="第3段第2句",
        )
        assert p.issue_id == "i-001"


class TestRevisionInput:
    """RevisionInput 测试."""

    def test_instantiation(self) -> None:
        ri = RevisionInput(version_id="v-001")
        assert ri.max_rounds == 2
        assert ri.issues == []

    def test_with_issues(self) -> None:
        issue = ReviewIssue(
            issue_id="i-001",
            category=ReviewCategory.WORLD_CONSISTENCY,
            severity="major",
            evidence_quote="test",
            evidence_location="test",
            issue_description="test",
        )
        ri = RevisionInput(
            version_id="v-001",
            issues=[issue],
            max_rounds=1,
        )
        assert len(ri.issues) == 1
        assert ri.max_rounds == 1


class TestRevisionOutput:
    """RevisionOutput 测试."""

    def test_instantiation(self) -> None:
        ro = RevisionOutput(new_version_id="v-002")
        assert ro.patches_applied == []
        assert ro.issues_fixed == []
        assert ro.new_issues_introduced == []

    def test_with_patches(self) -> None:
        ro = RevisionOutput(
            new_version_id="v-002",
            patches_applied=[
                Patch(
                    issue_id="i-001",
                    original_text="old",
                    revised_text="new",
                    location="test",
                ),
            ],
            issues_fixed=["i-001"],
            issues_remaining=["i-002"],
        )
        assert len(ro.patches_applied) == 1
        assert ro.issues_fixed == ["i-001"]


class TestCharacterUpdate:
    """CharacterUpdate 测试."""

    def test_instantiation(self) -> None:
        cu = CharacterUpdate(
            character_id="char-001",
            field="cultivation_level",
            old_value="筑基初期",
            new_value="筑基中期",
            source_quote="他突破了",
        )
        assert cu.old_value == "筑基初期"
        assert cu.new_value == "筑基中期"


class TestNewSetting:
    """NewSetting 测试."""

    def test_instantiation(self) -> None:
        ns = NewSetting(
            setting_name="天逆珠",
            description="神秘珠子",
            source_quote="他得到了天逆珠",
            setting_key="tianni-zhu",
        )
        assert ns.setting_key == "tianni-zhu"

    def test_without_setting_key(self) -> None:
        """setting_key 有默认值空字符串."""
        ns = NewSetting(
            setting_name="天逆珠",
            description="神秘珠子",
            source_quote="他得到了天逆珠",
        )
        assert ns.setting_key == ""


class TestForeshadowingUpdate:
    """ForeshadowingUpdate 测试."""

    def test_all_operations(self) -> None:
        for op in ("plant", "resolve", "update_status"):
            fu = ForeshadowingUpdate(
                operation=op,
                description="test",
            )
            assert fu.operation == op

    def test_with_version_id(self) -> None:
        fu = ForeshadowingUpdate(
            foreshadowing_id="f-001",
            operation="plant",
            description="种下伏笔",
            expected_resolve_chapter=10,
            source_version_id="v-003",
        )
        assert fu.source_version_id == "v-003"


class TestIncrement:
    """Increment 测试."""

    def test_instantiation(self) -> None:
        inc = Increment(
            amount=100.0,
            source="战斗奖励",
            source_quote="获得了100点经验",
        )
        assert inc.amount == 100.0


class TestDecrement:
    """Decrement 测试."""

    def test_instantiation(self) -> None:
        dec = Decrement(
            amount=50.0,
            usage="修炼消耗",
            source_quote="消耗了50点灵力",
        )
        assert dec.amount == 50.0


class TestNumericalUpdate:
    """NumericalUpdate 测试."""

    def test_instantiation(self) -> None:
        nu = NumericalUpdate(
            character_id="char-001",
            attribute_name="spirit_stones",
            opening_value=1000.0,
            closing_value=1050.0,
        )
        assert nu.opening_value == 1000.0
        assert nu.increments == []

    def test_with_transactions(self) -> None:
        nu = NumericalUpdate(
            character_id="char-001",
            attribute_name="spirit_stones",
            opening_value=1000.0,
            increments=[
                Increment(amount=100.0, source="任务奖励", source_quote="获得100灵石"),
            ],
            decrements=[
                Decrement(amount=50.0, usage="购买丹药", source_quote="花费50灵石"),
            ],
            closing_value=1050.0,
        )
        assert len(nu.increments) == 1
        assert len(nu.decrements) == 1
        assert nu.closing_value == 1050.0


class TestStateSettlement:
    """StateSettlement 测试."""

    def test_defaults(self) -> None:
        ss = StateSettlement()
        assert ss.validation_status == "valid"
        assert ss.character_updates == []
        assert ss.new_settings == []
        assert ss.foreshadowing_updates == []
        assert ss.numerical_updates == []

    def test_full_assembly(self) -> None:
        ss = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-001",
                    field="cultivation_level",
                    old_value="筑基初期",
                    new_value="筑基中期",
                    source_quote="突破了",
                ),
            ],
            new_settings=[
                NewSetting(
                    setting_name="天逆珠",
                    description="神秘珠子",
                    source_quote="得到了天逆珠",
                    setting_key="tianni-zhu",
                ),
            ],
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    foreshadowing_id="f-001",
                    operation="plant",
                    description="天逆珠的秘密",
                    expected_resolve_chapter=50,
                    source_version_id="v-005",
                ),
            ],
            numerical_updates=[
                NumericalUpdate(
                    character_id="char-001",
                    attribute_name="spirit_stones",
                    opening_value=1000.0,
                    increments=[
                        Increment(amount=100.0, source="任务", source_quote="奖励"),
                    ],
                    closing_value=1100.0,
                ),
            ],
            planted_hooks=["天逆珠的秘密"],
            validation_status="valid",
        )
        assert ss.validation_status == "valid"
        assert len(ss.character_updates) == 1
        assert len(ss.new_settings) == 1
        assert len(ss.numerical_updates) == 1

    def test_invalid_validation_status(self) -> None:
        """非法 validation_status 抛 ValidationError."""
        with pytest.raises(ValidationError):
            StateSettlement(validation_status="invalid")

    def test_needs_human_review(self) -> None:
        ss = StateSettlement(
            validation_status="needs_human_review",
            validation_errors=["old_value mismatch"],
        )
        assert ss.validation_status == "needs_human_review"
        assert ss.validation_errors == ["old_value mismatch"]
