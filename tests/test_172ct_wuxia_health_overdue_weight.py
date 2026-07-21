"""Task 172c.t: wuxia health overdue weight calibration tests."""

from __future__ import annotations

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models.continuity import OrphanedSetting, OverdueForeshadowing


def _background_orphans(count: int) -> list[OrphanedSetting]:
    return [
        OrphanedSetting(
            tracking_id=f"track-bg-{idx}",
            setting_key=f"world.bg.{idx}",
            setting_name=f"背景设定{idx}",
            introduced_in_chapter=40,
            last_mentioned_chapter=54,
            chapters_since_mention=6,
            category="background",
        )
        for idx in range(count)
    ]


def _technical_orphans(count: int) -> list[OrphanedSetting]:
    return [
        OrphanedSetting(
            tracking_id=f"track-tech-{idx}",
            setting_key=f"world.tech.{idx}",
            setting_name=f"技术设定{idx}",
            introduced_in_chapter=40,
            last_mentioned_chapter=50,
            chapters_since_mention=10,
            category="technical",
        )
        for idx in range(count)
    ]


def _overdue(count: int) -> list[OverdueForeshadowing]:
    return [
        OverdueForeshadowing(
            foreshadowing_id=f"fs-{idx}",
            description=f"伏笔{idx}",
            planted_in_chapter=idx + 1,
            expected_resolve_chapter=50,
            overdue_by=10,
        )
        for idx in range(count)
    ]


def test_scifi_health_overdue_weight_keeps_legacy_default() -> None:
    """No-profile / scifi behavior stays at the legacy 0.3 overdue weight."""
    profile = load_profile_from_registry("scifi")

    assert profile.continuity.health_overdue_weight == 0.3


def test_wuxia_health_overdue_weight_is_long_window_calibrated() -> None:
    """172c.t: wuxia uses a softer health penalty while vdim overdue gate remains."""
    profile = load_profile_from_registry("wuxia")

    assert profile.continuity.health_overdue_weight == 0.15


def test_urban_health_overdue_weight_is_ch25_calibrated() -> None:
    """187.s: urban Ch25 overdue 已过五门，不应被 health 二次重罚."""
    profile = load_profile_from_registry("urban")

    assert profile.continuity.health_overdue_weight == 0.08


def test_wuxia_ch60_health_case_stays_above_gate_after_calibration() -> None:
    """Ch60现场: overdue 15 + background/technical orphan 11 should not halt."""
    orphaned = [*_background_orphans(10), *_technical_orphans(1)]
    overdue = _overdue(15)

    legacy_score = ContinuityAuditor()._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=60,
    )
    wuxia_score = ContinuityAuditor(
        runtime_profile=load_profile_from_registry("wuxia")
    )._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=60,
    )

    assert legacy_score == 7.6
    assert wuxia_score >= 8.0


def test_wuxia_ch99_tail_health_case_stays_above_gate_after_calibration() -> None:
    """Ch99现场: vdim overdue pass 时，tail health should not false-halt."""
    orphaned = [*_background_orphans(22), *_technical_orphans(1)]
    overdue = _overdue(35)

    wuxia_score = ContinuityAuditor(
        runtime_profile=load_profile_from_registry("wuxia")
    )._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=99,
    )

    assert wuxia_score >= 8.0


def test_urban_ch21_health_case_stays_above_gate_after_calibration() -> None:
    """187.s Ch21: 19 overdue + 8 background orphans should stay healthy."""
    orphaned = _background_orphans(8)
    overdue = _overdue(19)

    legacy_score = ContinuityAuditor()._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=21,
    )
    urban_score = ContinuityAuditor(
        runtime_profile=load_profile_from_registry("urban")
    )._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=21,
    )

    assert legacy_score == 5.3
    assert urban_score >= 8.0


def test_urban_ch24_health_case_stays_above_gate_after_calibration() -> None:
    """187.s Ch24: latest health should pass when overdue gate already passes."""
    orphaned = _background_orphans(6)
    overdue = _overdue(27)

    legacy_score = ContinuityAuditor()._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=24,
    )
    urban_score = ContinuityAuditor(
        runtime_profile=load_profile_from_registry("urban")
    )._compute_health_score(
        orphaned=orphaned,
        forgotten=[],
        mismatches=[],
        overdue=overdue,
        chapter_number=24,
    )

    assert legacy_score == 5.2
    assert urban_score >= 8.0
