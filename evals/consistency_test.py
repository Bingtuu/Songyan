"""随机一致性测试引擎 — 跨章设定/道具/角色/伏笔/时间线验证.

不依赖 LLM，纯 DB + 文本扫描，可复现抽样。
"""

from __future__ import annotations

import random
import re
from typing import Any

import structlog

from songyan.db.continuity_repo import (
    InventoryTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.db.settlement_repo import ForeshadowingRepository

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class SettingConsistencyResult:
    """设定一致性检查结果."""

    def __init__(
        self,
        setting_key: str,
        setting_name: str,
        introduced_in_chapter: int,
        last_mentioned_chapter: int | None,
        recall_chapters: list[int],
        missed_chapters: list[int],
        recall_rate: float,
    ) -> None:
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.introduced_in_chapter = introduced_in_chapter
        self.last_mentioned_chapter = last_mentioned_chapter
        self.recall_chapters = recall_chapters
        self.missed_chapters = missed_chapters
        self.recall_rate = recall_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "setting_key": self.setting_key,
            "setting_name": self.setting_name,
            "introduced_in_chapter": self.introduced_in_chapter,
            "last_mentioned_chapter": self.last_mentioned_chapter,
            "recall_chapters": self.recall_chapters,
            "missed_chapters": self.missed_chapters,
            "recall_rate": self.recall_rate,
        }


class InventoryTrackingResult:
    """道具追踪检查结果."""

    def __init__(
        self,
        item_name: str,
        character_id: str,
        acquired_in_chapter: int,
        recall_chapters: list[int],
        missed_chapters: list[int],
        recall_rate: float,
    ) -> None:
        self.item_name = item_name
        self.character_id = character_id
        self.acquired_in_chapter = acquired_in_chapter
        self.recall_chapters = recall_chapters
        self.missed_chapters = missed_chapters
        self.recall_rate = recall_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_name": self.item_name,
            "character_id": self.character_id,
            "acquired_in_chapter": self.acquired_in_chapter,
            "recall_chapters": self.recall_chapters,
            "missed_chapters": self.missed_chapters,
            "recall_rate": self.recall_rate,
        }


class ForeshadowingResult:
    """伏笔回收检查结果."""

    def __init__(
        self,
        foreshadowing_id: str,
        description: str,
        planted_in_chapter: int,
        expected_resolve_chapter: int | None,
        resolved: bool,
        overdue: bool,
    ) -> None:
        self.foreshadowing_id = foreshadowing_id
        self.description = description
        self.planted_in_chapter = planted_in_chapter
        self.expected_resolve_chapter = expected_resolve_chapter
        self.resolved = resolved
        self.overdue = overdue

    def to_dict(self) -> dict[str, Any]:
        return {
            "foreshadowing_id": self.foreshadowing_id,
            "description": self.description,
            "planted_in_chapter": self.planted_in_chapter,
            "expected_resolve_chapter": self.expected_resolve_chapter,
            "resolved": self.resolved,
            "overdue": self.overdue,
        }


class ConsistencyTestReport:
    """随机一致性测试总报告."""

    def __init__(
        self,
        project_id: str,
        sample_count: int,
        setting_results: list[SettingConsistencyResult],
        inventory_results: list[InventoryTrackingResult],
        foreshadowing_results: list[ForeshadowingResult],
    ) -> None:
        self.project_id = project_id
        self.sample_count = sample_count
        self.setting_results = setting_results
        self.inventory_results = inventory_results
        self.foreshadowing_results = foreshadowing_results

    @property
    def overall_recall_rate(self) -> float:
        """所有测试类型的加权平均召回率."""
        rates: list[float] = []
        weights: list[float] = []
        if self.setting_results:
            rates.append(
                sum(r.recall_rate for r in self.setting_results) / len(self.setting_results)
            )
            weights.append(len(self.setting_results))
        if self.inventory_results:
            rates.append(
                sum(r.recall_rate for r in self.inventory_results) / len(self.inventory_results)
            )
            weights.append(len(self.inventory_results))
        if not rates:
            return 0.0
        return sum(r * w for r, w in zip(rates, weights)) / sum(weights)

    @property
    def foreshadowing_recovery_rate(self) -> float | None:
        """已 resolve 的伏笔占所有应 resolve 伏笔的比例."""
        due = [r for r in self.foreshadowing_results if r.expected_resolve_chapter is not None]
        if not due:
            return None
        resolved = sum(1 for r in due if r.resolved)
        return resolved / len(due)

    @property
    def overall_score(self) -> float:
        """综合评分 0~10."""
        recall = self.overall_recall_rate
        fs_rate = self.foreshadowing_recovery_rate
        if fs_rate is not None:
            return min(10.0, recall * 7 + fs_rate * 3)
        return min(10.0, recall * 10)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "sample_count": self.sample_count,
            "overall_recall_rate": self.overall_recall_rate,
            "foreshadowing_recovery_rate": self.foreshadowing_recovery_rate,
            "overall_score": self.overall_score,
            "setting_consistency": [r.to_dict() for r in self.setting_results],
            "inventory_tracking": [r.to_dict() for r in self.inventory_results],
            "foreshadowing_recovery": [r.to_dict() for r in self.foreshadowing_results],
        }


# ---------------------------------------------------------------------------
# Text scanning helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """统一空白字符：去头尾空格、压缩连续空白."""
    text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _keyword_in_content(keyword: str, content: str, threshold: float = 0.75) -> bool:
    """检查关键词是否存在于正文中（支持模糊匹配）.

    先尝试精确子串匹配（归一化后），再尝试滑动窗口模糊匹配。
    """
    if not keyword or not content:
        return True  # 空关键词视为通过

    norm_kw = _normalize_text(keyword)
    norm_content = _normalize_text(content)

    # 1. 精确子串匹配
    if norm_kw in norm_content:
        return True

    # 2. 滑动窗口模糊匹配
    kw_len = len(norm_kw)
    if kw_len == 0:
        return True

    best_ratio = 0.0
    step = max(1, kw_len // 4)
    for i in range(0, len(norm_content) - kw_len + 1, step):
        window = norm_content[i : i + kw_len]
        ratio = _quick_ratio(norm_kw, window)
        if ratio > best_ratio:
            best_ratio = ratio
        if best_ratio >= threshold:
            return True

    return False


def _quick_ratio(a: str, b: str) -> float:
    """快速计算两个字符串的相似度（简化版）."""
    if a == b:
        return 1.0
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


# ---------------------------------------------------------------------------
# Random Consistency Test Engine
# ---------------------------------------------------------------------------


class RandomConsistencyTest:
    """随机一致性测试 — 在已有章节文本上抽样验证跨章一致性."""

    def __init__(
        self,
        setting_repo: SettingTrackingRepository | None = None,
        inventory_repo: InventoryTrackerRepository | None = None,
        foreshadowing_repo: ForeshadowingRepository | None = None,
        version_repo: ChapterVersionRepository | None = None,
        head_repo: ChapterHeadRepository | None = None,
    ) -> None:
        self.setting_repo = setting_repo or SettingTrackingRepository()
        self.inventory_repo = inventory_repo or InventoryTrackerRepository()
        self.foreshadowing_repo = foreshadowing_repo or ForeshadowingRepository()
        self.version_repo = version_repo or ChapterVersionRepository()
        self.head_repo = head_repo or ChapterHeadRepository()

    async def run(
        self,
        project_id: str,
        sample_count: int = 20,
    ) -> ConsistencyTestReport:
        """运行随机一致性测试.

        Args:
            project_id: 项目 ID
            sample_count: 每种测试类型的最大抽样数

        Returns:
            ConsistencyTestReport
        """
        chapter_contents = await self._load_chapter_contents(project_id)
        if not chapter_contents:
            logger.warning("consistency.no_chapters", project_id=project_id)
            return ConsistencyTestReport(
                project_id=project_id,
                sample_count=0,
                setting_results=[],
                inventory_results=[],
                foreshadowing_results=[],
            )

        max_chapter = max(chapter_contents.keys())
        rng = random.Random(project_id)  # 可复现的伪随机

        setting_results = await self._test_settings(
            project_id, chapter_contents, sample_count, rng, max_chapter
        )
        inventory_results = await self._test_inventory(
            project_id, chapter_contents, sample_count, rng, max_chapter
        )
        foreshadowing_results = await self._test_foreshadowing(
            project_id, max_chapter
        )

        report = ConsistencyTestReport(
            project_id=project_id,
            sample_count=sample_count,
            setting_results=setting_results,
            inventory_results=inventory_results,
            foreshadowing_results=foreshadowing_results,
        )

        logger.info(
            "consistency.test_complete",
            project_id=project_id,
            overall_recall_rate=report.overall_recall_rate,
            overall_score=report.overall_score,
            setting_samples=len(setting_results),
            inventory_samples=len(inventory_results),
            foreshadowing_samples=len(foreshadowing_results),
        )
        return report

    async def _load_chapter_contents(
        self, project_id: str
    ) -> dict[int, str]:
        """加载项目下所有 accepted 章节的正文，返回 {chapter_number: content}."""
        contents: dict[int, str] = {}
        heads = await self.head_repo.list_by_project(project_id)
        for head in heads:
            if head.status != "accepted" or not head.accepted_version_id:
                continue
            version = await self.version_repo.get(head.accepted_version_id)
            if version and version.content:
                contents[head.chapter_number] = version.content
        return contents

    async def _test_settings(
        self,
        project_id: str,
        chapter_contents: dict[int, str],
        sample_count: int,
        rng: random.Random,
        max_chapter: int,
    ) -> list[SettingConsistencyResult]:
        """设定一致性测试：抽样设定，检查后续章节是否提及."""
        settings = await self.setting_repo.list_by_project(project_id)
        if not settings:
            return []

        eligible = [s for s in settings if s["introduced_in_chapter"] < max_chapter]
        if not eligible:
            return []

        samples = rng.sample(eligible, min(sample_count, len(eligible)))
        results: list[SettingConsistencyResult] = []

        for s in samples:
            intro_ch = s["introduced_in_chapter"]
            keywords = [k for k in (s["setting_key"], s["setting_name"]) if k]
            if not keywords:
                continue

            recall_chapters: list[int] = []
            missed_chapters: list[int] = []

            for ch_num in range(intro_ch + 1, max_chapter + 1):
                content = chapter_contents.get(ch_num, "")
                if any(_keyword_in_content(kw, content) for kw in keywords):
                    recall_chapters.append(ch_num)
                else:
                    missed_chapters.append(ch_num)

            total = len(recall_chapters) + len(missed_chapters)
            recall_rate = len(recall_chapters) / total if total > 0 else 1.0

            results.append(
                SettingConsistencyResult(
                    setting_key=s["setting_key"],
                    setting_name=s["setting_name"],
                    introduced_in_chapter=intro_ch,
                    last_mentioned_chapter=s.get("last_mentioned_chapter"),
                    recall_chapters=recall_chapters,
                    missed_chapters=missed_chapters,
                    recall_rate=recall_rate,
                )
            )

        return results

    async def _test_inventory(
        self,
        project_id: str,
        chapter_contents: dict[int, str],
        sample_count: int,
        rng: random.Random,
        max_chapter: int,
    ) -> list[InventoryTrackingResult]:
        """道具追踪测试：抽样道具，检查获得后章节是否出现."""
        items = await self.inventory_repo.list_by_project(project_id)
        if not items:
            return []

        eligible = [i for i in items if i["acquired_in_chapter"] < max_chapter]
        if not eligible:
            return []

        samples = rng.sample(eligible, min(sample_count, len(eligible)))
        results: list[InventoryTrackingResult] = []

        for item in samples:
            acq_ch = item["acquired_in_chapter"]
            item_name = item["item_name"]
            if not item_name:
                continue

            recall_chapters: list[int] = []
            missed_chapters: list[int] = []

            for ch_num in range(acq_ch + 1, max_chapter + 1):
                content = chapter_contents.get(ch_num, "")
                if _keyword_in_content(item_name, content):
                    recall_chapters.append(ch_num)
                else:
                    missed_chapters.append(ch_num)

            total = len(recall_chapters) + len(missed_chapters)
            recall_rate = len(recall_chapters) / total if total > 0 else 1.0

            results.append(
                InventoryTrackingResult(
                    item_name=item_name,
                    character_id=item["character_id"],
                    acquired_in_chapter=acq_ch,
                    recall_chapters=recall_chapters,
                    missed_chapters=missed_chapters,
                    recall_rate=recall_rate,
                )
            )

        return results

    async def _test_foreshadowing(
        self,
        project_id: str,
        max_chapter: int,
    ) -> list[ForeshadowingResult]:
        """伏笔回收测试：检查所有 planted 伏笔是否已 resolve 或 overdue."""
        all_items = await self.foreshadowing_repo.list_all(project_id)
        results: list[ForeshadowingResult] = []
        for item in all_items:
            resolved = item.status == "resolved"
            overdue = (
                item.status == "planted"
                and item.expected_resolve_chapter is not None
                and max_chapter > item.expected_resolve_chapter
            )
            results.append(
                ForeshadowingResult(
                    foreshadowing_id=item.foreshadowing_id,
                    description=item.description,
                    planted_in_chapter=item.planted_in_chapter or 0,
                    expected_resolve_chapter=item.expected_resolve_chapter,
                    resolved=resolved,
                    overdue=overdue,
                )
            )
        return results
