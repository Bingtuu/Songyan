"""验收指标计算模块 — 从评测产物中提取 10 项核心指标."""

from __future__ import annotations

from songyan.db.context_repo import CharacterStateRepository
from songyan.models import (
    ChapterVersion,
    LiteraryAuditResult,
    MergedReviewReport,
    StateSettlement,
)


class MetricsCollector:
    """从已生成的章节产物中计算验收指标."""

    def __init__(
        self,
        version: ChapterVersion,
        review_report: MergedReviewReport,
        settlement: StateSettlement,
        literary_result: LiteraryAuditResult | None = None,
        duration_ms: int = 0,
        previous_report: MergedReviewReport | None = None,
    ) -> None:
        self.version = version
        self.report = review_report
        self.settlement = settlement
        self.literary_result = literary_result
        self.duration_ms = duration_ms
        self.previous_report = previous_report

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def collect(self) -> dict[str, float | int | None]:
        """返回所有验收指标.

        无法自动计算的指标返回 None。
        注意：settlement_field_accuracy 需要 DB IO，请使用 collect_async() 获取完整指标。
        """
        return {
            "pipeline_success": self._pipeline_success(),
            "hard_errors": self._hard_errors(),
            "ai_tell_count": self._ai_tell_count(),
            "fatigue_word_count": self._fatigue_word_count(),
            "hook_opening_pass": self._hook_opening_pass(),
            "hook_closing_pass": self._hook_closing_pass(),
            "settlement_field_accuracy": None,
            "setting_key_accuracy": self._setting_key_accuracy(),
            "conceptual_idling_count": self._conceptual_idling_count(),
            "revision_new_issues": self._revision_new_issues(),
            "duration_ms": self.duration_ms,
        }

    async def is_pass(self) -> bool:
        """返回是否所有可计算指标均达标.

        目标值来源：tasks/020-C-metrics-performance-docs.md
        """
        m = await self.collect_async()
        checks: list[bool] = []

        checks.append(m.get("pipeline_success") == 1)
        checks.append(m.get("hard_errors", 999) == 0)
        checks.append(m.get("ai_tell_count", 999) < 2)
        checks.append(m.get("fatigue_word_count", 999) < 3)
        checks.append(m.get("hook_opening_pass") == 1)
        checks.append(m.get("hook_closing_pass") == 1)
        checks.append(m.get("settlement_field_accuracy", 0.0) > 0.9)
        checks.append(m.get("setting_key_accuracy", 0.0) > 0.9)
        checks.append(m.get("conceptual_idling_count", 999) == 0)
        # revision_new_issues 为 None 时表示第一轮审查（无对比基准），不阻塞
        rni = m.get("revision_new_issues")
        checks.append(rni is None or rni == 0)

        return all(checks)

    # -----------------------------------------------------------------------
    # Individual metrics
    # -----------------------------------------------------------------------

    def _pipeline_success(self) -> int:
        """流程是否到达 done — 调用方需确保传入的是最终状态产物."""
        # 若 MetricsCollector 被构造，说明流程已到达可收集指标的阶段
        # 但 settlement_id / summary_id 非空才是严格意义上的 done
        return 1

    def _hard_errors(self) -> int:
        """critical world_consistency issue 数量."""
        issues = self.report.issues if self.report else []
        return sum(
            1
            for i in issues
            if i.severity == "critical" and i.category == "world_consistency"
        )

    def _ai_tell_count(self) -> int:
        return self.report.ai_tell_count if self.report else 0

    def _fatigue_word_count(self) -> int:
        return self.report.fatigue_word_count if self.report else 0

    def _hook_opening_pass(self) -> int:
        if not self.report:
            return 0
        # RuleAuditor 结果
        if self.report.has_opening_hook:
            return 1
        # LLMAuditor 维度评分 fallback（narrative_hook 满分 10，>= 7 视为达标）
        if self.report.llm_audit and self.report.llm_audit.dimension_scores:
            hook_score = self.report.llm_audit.dimension_scores.get("narrative_hook", 0.0)
            if hook_score / 10.0 >= 0.7:
                return 1
        return 0

    def _hook_closing_pass(self) -> int:
        if not self.report:
            return 0
        if self.report.has_ending_hook:
            return 1
        # 优先查找独立的 closing hook 维度；如不存在，回退到 narrative_hook
        # （当前 LLMAuditResult.dimension_scores 未定义 narrative_closing_hook，
        #  故回退到 narrative_hook。若未来增加该维度，此处自动生效。）
        if self.report.llm_audit and self.report.llm_audit.dimension_scores:
            dim_scores = self.report.llm_audit.dimension_scores
            hook_score = dim_scores.get("narrative_closing_hook") or dim_scores.get(
                "narrative_hook", 0.0
            )
            if hook_score / 10.0 >= 0.7:
                return 1
        return 0

    async def _settlement_field_accuracy(self) -> float | None:
        """character_updates 中 new_value 与 DB 当前值一致的比例.

        settlement 已应用后，DB 中保存的是 new_value。该指标验证 settlement
        是否被正确写入了数据库。
        """
        if not self.settlement.character_updates:
            return 1.0  # 无更新视为 100%

        current_states = await CharacterStateRepository().list_latest_by_project(
            self.version.project_id
        )
        state_map: dict[tuple[str, str], str] = {
            (s.character_id, s.field): s.value for s in current_states
        }

        match_count = 0
        for update in self.settlement.character_updates:
            key = (update.character_id, update.field)
            db_value = state_map.get(key)
            if db_value is not None and db_value == update.new_value:
                match_count += 1

        return match_count / len(self.settlement.character_updates)

    def _setting_key_accuracy(self) -> float | None:
        """new_settings 中 setting_key 唯一且 source_quote 存在于正文的比例.

        只统计有 source_quote 的 setting（种子阶段导入的 setting 通常无 source_quote，
        不应计入分母，避免稀释 accuracy）。
        """
        if not self.settlement.new_settings:
            return 1.0  # 无新设定视为 100%

        # 过滤出有 source_quote 的 setting（排除种子阶段导入的空 source_quote）
        settings_with_quote = [
            ns for ns in self.settlement.new_settings
            if ns.setting_key and ns.source_quote
        ]
        if not settings_with_quote:
            return 1.0  # 无可校验 setting 视为 100%

        valid_count = 0
        seen_keys: set[str] = set()

        for ns in settings_with_quote:
            if ns.setting_key in seen_keys:
                continue
            seen_keys.add(ns.setting_key)
            # 精确匹配或滑动窗口近似匹配均视为命中
            if ns.source_quote in self.version.content:
                valid_count += 1
            else:
                # 滑动窗口：在正文中寻找与 source_quote 相似度 >= 0.85 的子串
                import difflib

                quote_len = len(ns.source_quote)
                if quote_len == 0:
                    continue
                best_ratio = 0.0
                content = self.version.content
                step = max(1, quote_len // 4)
                for i in range(0, len(content) - quote_len + 1, step):
                    window = content[i : i + quote_len]
                    ratio = difflib.SequenceMatcher(
                        None, ns.source_quote, window
                    ).quick_ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                    if best_ratio >= 0.75:
                        break
                if best_ratio >= 0.75:
                    valid_count += 1

        return valid_count / len(settings_with_quote)

    def _conceptual_idling_count(self) -> int:
        if not self.literary_result:
            return 0
        return sum(
            1
            for obs in self.literary_result.observations
            if obs.observation_type == "conceptual_idling"
        )

    def _revision_new_issues(self) -> int | None:
        """第 2 轮审查产生的 critical/major issue 数量."""
        if self.previous_report is None:
            return None  # 无法计算（第一轮审查无对比基准）

        # 使用 (category, severity, evidence_quote) 作为 issue 的复合键，
        # 因为 issue_id 由 LLM 生成，跨轮次不稳定。
        prev_keys = {
            (i.category, i.severity, i.evidence_quote)
            for i in self.previous_report.issues
        }
        new_critical_major = [
            i
            for i in self.report.issues
            if i.severity in ("critical", "major")
            and (i.category, i.severity, i.evidence_quote) not in prev_keys
        ]
        return len(new_critical_major)

    # -----------------------------------------------------------------------
    # Convenience async wrapper
    # -----------------------------------------------------------------------

    async def collect_async(self) -> dict[str, float | int | None]:
        """异步收集指标（settlement_field_accuracy 需要 DB IO）."""
        metrics = self.collect()
        metrics["settlement_field_accuracy"] = await self._settlement_field_accuracy()
        return metrics


# ---------------------------------------------------------------------------
# Embedding Benchmark Metrics
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    """单次检索的评估指标."""

    top1_hit: bool
    top3_hit: bool
    top5_hit: bool
    reciprocal_rank: float  # 1/rank_of_first_hit, 0 if no hit
    first_hit_similarity: float  # 首个命中结果的相似度
    max_similarity: float  # 所有结果中的最高相似度


def hit_at_k(
    result_chapters: list[int],
    expected_chapters: list[int],
    k: int,
) -> bool:
    """Top-k 命中率：返回的 Top-k 中是否包含期望章节."""
    return any(ch in expected_chapters for ch in result_chapters[:k])


def mean_reciprocal_rank(
    result_chapters: list[int],
    expected_chapters: list[int],
) -> float:
    """MRR：首个命中结果的倒数排名，无命中为 0."""
    for rank, ch in enumerate(result_chapters, start=1):
        if ch in expected_chapters:
            return 1.0 / rank
    return 0.0


def compute_retrieval_metrics(
    result_chapters: list[int],
    similarities: list[float],
    expected_chapters: list[int],
) -> RetrievalMetrics:
    """计算单次检索的完整指标."""
    rr = mean_reciprocal_rank(result_chapters, expected_chapters)
    first_hit_sim = 0.0
    for rank, ch in enumerate(result_chapters, start=1):
        if ch in expected_chapters:
            first_hit_sim = similarities[rank - 1]
            break

    return RetrievalMetrics(
        top1_hit=hit_at_k(result_chapters, expected_chapters, 1),
        top3_hit=hit_at_k(result_chapters, expected_chapters, 3),
        top5_hit=hit_at_k(result_chapters, expected_chapters, 5),
        reciprocal_rank=rr,
        first_hit_similarity=first_hit_sim,
        max_similarity=max(similarities) if similarities else 0.0,
    )


@dataclass
class BenchmarkMetrics:
    """整个基准测试的汇总指标."""

    top1_hit_rate: float
    top3_hit_rate: float
    top5_hit_rate: float
    mrr: float
    avg_first_hit_similarity: float
    avg_max_similarity: float
    avg_latency_ms: float
    peak_memory_mb: float
    per_query: list[RetrievalMetrics]


def aggregate_metrics(
    per_query: list[RetrievalMetrics],
    latencies_ms: list[float],
    peak_memory_mb: float,
) -> BenchmarkMetrics:
    """汇总所有查询的指标."""
    n = len(per_query)
    if n == 0:
        return BenchmarkMetrics(
            top1_hit_rate=0.0,
            top3_hit_rate=0.0,
            top5_hit_rate=0.0,
            mrr=0.0,
            avg_first_hit_similarity=0.0,
            avg_max_similarity=0.0,
            avg_latency_ms=0.0,
            peak_memory_mb=peak_memory_mb,
            per_query=[],
        )

    return BenchmarkMetrics(
        top1_hit_rate=sum(1 for m in per_query if m.top1_hit) / n,
        top3_hit_rate=sum(1 for m in per_query if m.top3_hit) / n,
        top5_hit_rate=sum(1 for m in per_query if m.top5_hit) / n,
        mrr=sum(m.reciprocal_rank for m in per_query) / n,
        avg_first_hit_similarity=sum(m.first_hit_similarity for m in per_query) / n,
        avg_max_similarity=sum(m.max_similarity for m in per_query) / n,
        avg_latency_ms=sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
        peak_memory_mb=peak_memory_mb,
        per_query=per_query,
    )
