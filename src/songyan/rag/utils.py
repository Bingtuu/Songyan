"""RAG 启用判断与阈值计算工具."""

from __future__ import annotations

from songyan.models.project import ProjectSetting
from songyan.models.rag import RAGConfig

_MIN_THRESHOLD = 10
_MAX_THRESHOLD = 50
_THRESHOLD_RATIO = 0.3


def should_enable_rag(
    current_chapter: int,
    project_setting: ProjectSetting,
    rag_config: RAGConfig,
) -> bool:
    """判断当前章节是否应启用 RAG 检索.

    Args:
        current_chapter: 当前章节号
        project_setting: 项目设置
        rag_config: RAG 配置

    Returns:
        True 表示应启用 RAG
    """
    if rag_config.enabled == "never":
        return False
    if rag_config.enabled == "always":
        return True
    # auto 模式
    threshold = rag_config.threshold_chapters
    if threshold is None:
        threshold = compute_rag_threshold(project_setting)
    return current_chapter >= threshold


def compute_rag_threshold(project_setting: ProjectSetting) -> int:
    """计算 RAG 自动启用阈值.

    公式: estimated_chapters * 0.3，最低 10 章，最高 50 章
    """
    estimated = project_setting.estimated_chapters or 30
    threshold = int(estimated * _THRESHOLD_RATIO)
    return max(_MIN_THRESHOLD, min(_MAX_THRESHOLD, threshold))
