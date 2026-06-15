"""RAG 工具函数测试."""

from __future__ import annotations

from songyan.models.project import ProjectSetting
from songyan.models.rag import RAGConfig
from songyan.rag.utils import compute_rag_threshold, should_enable_rag


class TestShouldEnableRAG:
    """RAG 启用判断测试."""

    def test_never_returns_false(self) -> None:
        config = RAGConfig(enabled="never")
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p"
        )
        assert should_enable_rag(100, project, config) is False

    def test_always_returns_true(self) -> None:
        config = RAGConfig(enabled="always")
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p"
        )
        assert should_enable_rag(1, project, config) is True

    def test_auto_below_threshold(self) -> None:
        config = RAGConfig(enabled="auto", threshold_chapters=30)
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p"
        )
        assert should_enable_rag(29, project, config) is False

    def test_auto_at_threshold(self) -> None:
        config = RAGConfig(enabled="auto", threshold_chapters=30)
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p"
        )
        assert should_enable_rag(30, project, config) is True

    def test_auto_above_threshold(self) -> None:
        config = RAGConfig(enabled="auto", threshold_chapters=30)
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p"
        )
        assert should_enable_rag(31, project, config) is True

    def test_auto_uses_computed_threshold(self) -> None:
        """threshold_chapters 为 None 时自动计算."""
        config = RAGConfig(enabled="auto", threshold_chapters=None)
        project = ProjectSetting(
            title="t",
            genre_id="g",
            mode_id="m",
            protagonist_name="p",
            estimated_chapters=100,
        )
        # 100 * 0.3 = 30
        assert should_enable_rag(29, project, config) is False
        assert should_enable_rag(30, project, config) is True


class TestComputeThreshold:
    """阈值计算测试."""

    def test_typical_project(self) -> None:
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p",
            estimated_chapters=100,
        )
        assert compute_rag_threshold(project) == 30

    def test_small_project_clamped_to_min(self) -> None:
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p",
            estimated_chapters=10,
        )
        # 10 * 0.3 = 3 → clamped to 10
        assert compute_rag_threshold(project) == 10

    def test_large_project_clamped_to_max(self) -> None:
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p",
            estimated_chapters=300,
        )
        # 300 * 0.3 = 90 → clamped to 50
        assert compute_rag_threshold(project) == 50

    def test_default_estimated_chapters(self) -> None:
        project = ProjectSetting(
            title="t", genre_id="g", mode_id="m", protagonist_name="p",
        )
        # default estimated_chapters = 30
        assert compute_rag_threshold(project) == 10
