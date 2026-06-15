"""Tests for review history compression (Task 033 A2-3)."""

from __future__ import annotations

from songyan.agents.llm_auditor import _compress_review_history
from songyan.models import LLMAuditResult, ReviewCategory, ReviewIssue


def _make_issue(
    issue_id: str,
    category: ReviewCategory = ReviewCategory.WORLD_CONSISTENCY,
    severity: str = "major",
    description: str = "问题描述",
    evidence: str | None = None,
) -> ReviewIssue:
    # 使用唯一 evidence 避免去重冲突
    evidence_quote = evidence or f"证据引用-{issue_id}"
    return ReviewIssue(
        issue_id=issue_id,
        category=category,
        severity=severity,  # type: ignore[arg-type]
        evidence_quote=evidence_quote,
        evidence_location="第3段",
        issue_description=description,
    )


class TestCompressReviewHistory:
    """Review 历史压缩测试."""

    def test_empty_reviews(self) -> None:
        """空列表返回空字符串."""
        assert _compress_review_history([]) == ""

    def test_single_review(self) -> None:
        """单轮 review 压缩."""
        review = LLMAuditResult(
            issues=[
                _make_issue("i1", severity="critical", description="世界观矛盾"),
                _make_issue("i2", severity="minor", description="节奏拖沓"),
            ]
        )
        compressed = _compress_review_history([review])
        assert "critical" in compressed
        assert "世界观矛盾" in compressed
        assert "minor" in compressed

    def test_multiple_reviews_keep_recent_two(self) -> None:
        """多轮 review 只保留最近 2 轮."""
        reviews = [
            LLMAuditResult(issues=[
                _make_issue(f"r1_i{i}", description=f"第一轮问题{i}") for i in range(3)
            ]),
            LLMAuditResult(issues=[
                _make_issue(f"r2_i{i}", description=f"第二轮问题{i}") for i in range(3)
            ]),
            LLMAuditResult(issues=[
                _make_issue(f"r3_i{i}", description=f"第三轮问题{i}") for i in range(3)
            ]),
        ]
        compressed = _compress_review_history(reviews)
        # 应包含第2轮和第3轮，不包含第1轮
        assert "第二轮问题" in compressed
        assert "第三轮问题" in compressed
        assert "第一轮问题" not in compressed

    def test_deduplication(self) -> None:
        """相同 category + evidence 的 issue 应去重."""
        reviews = [
            LLMAuditResult(
                issues=[
                    _make_issue(
                        "i1", category=ReviewCategory.WORLD_CONSISTENCY, description="矛盾A",
                    ),
                ]
            ),
            LLMAuditResult(
                issues=[
                    _make_issue(
                        "i2", category=ReviewCategory.WORLD_CONSISTENCY, description="矛盾B",
                    ),
                    _make_issue(
                        "i3", category=ReviewCategory.WORLD_CONSISTENCY, description="矛盾A",
                    ),  # 重复
                ]
            ),
        ]
        compressed = _compress_review_history(reviews)
        # "矛盾A" 只应出现一次
        assert compressed.count("矛盾A") == 1

    def test_severity_priority(self) -> None:
        """critical/major 应优先保留."""
        review = LLMAuditResult(
            issues=[
                _make_issue("i1", severity="info", description="信息性问题"),
                _make_issue("i2", severity="critical", description="严重问题"),
                _make_issue("i3", severity="minor", description="轻微问题"),
                _make_issue("i4", severity="major", description="主要问题"),
            ]
        )
        compressed = _compress_review_history([review], max_issues_per_round=2)
        # 只保留 2 个，应优先 critical 和 major
        assert "严重问题" in compressed
        assert "主要问题" in compressed
        # minor 和 info 可能被截断

    def test_max_total_length(self) -> None:
        """超长输出应截断."""
        # 需要足够多的 issues 才能超过 500 字符（每行 description 截断到 80）
        reviews = [
            LLMAuditResult(
                issues=[
                    _make_issue(f"i{i}", description=f"这是一个非常长的问题描述{i}" * 50)
                    for i in range(20)
                ]
            )
        ]
        compressed = _compress_review_history(reviews, max_total_length=300)
        assert len(compressed) <= 350  # 允许一点余量给截断提示
        assert "...（已截断）" in compressed

    def test_dimension_scores_summary(self) -> None:
        """低分维度应出现在摘要中."""
        review = LLMAuditResult(
            issues=[],
            dimension_scores={
                "world_consistency": 8.0,
                "narrative_pacing": 4.5,
                "info_dump": 3.0,
            },
        )
        compressed = _compress_review_history([review])
        assert "narrative_pacing=4.5" in compressed
        assert "info_dump=3.0" in compressed
        assert "world_consistency=8.0" not in compressed  # 高分不显示

    def test_compression_ratio(self) -> None:
        """压缩率测试：3 轮 review → 压缩后长度显著缩减."""
        issues_per_round = 5
        reviews = [
            LLMAuditResult(
                issues=[
                    _make_issue(
                        f"r{ri}_i{i}",
                        description=f"这是第{ri}轮的第{i}个问题描述，包含足够长度的文本来说明压缩效果。",
                    )
                    for i in range(issues_per_round)
                ]
            )
            for ri in range(3)
        ]

        # 原始总长度（完整 description）
        original_len = sum(
            len(issue.issue_description) for r in reviews for issue in r.issues
        )

        compressed = _compress_review_history(reviews, max_issues_per_round=2)
        # 3 轮 * 5 issues = 15 个完整 description
        # 压缩后只保留 2 轮 * 2 issues = 4 个截断 description
        # 压缩后长度应显著小于原始长度（< 60%）
        assert len(compressed) < original_len * 0.6
