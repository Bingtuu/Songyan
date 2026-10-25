"""Claim checker: structured I/O, deterministic anchors, and a stubbed LLM."""

from __future__ import annotations

import pytest

from songyan.models.plan_facts import PlanClaim, PlanEvent
from songyan.plan_checks.claim_check import (
    AnchoredClaimJudge,
    ClaimAnchor,
    ClaimCheckError,
    LlmClaimJudge,
    parse_claim_judgment,
    verify_chapter_claims,
)


def _event() -> PlanEvent:
    return PlanEvent(
        event_id="evt-1",
        project_id="p1",
        ch=2,
        claims=[
            PlanClaim(claim_id="claim-scratch", text="刮痕方向为右向左"),
        ],
    )


class TestClaimCheck:
    async def test_verbatim_claim_is_supported_without_an_anchor(self) -> None:
        verdicts = await verify_chapter_claims(
            [_event()],
            2,
            "报告写明：刮痕方向为右向左。",
        )

        assert verdicts[0].status == "supported"
        assert verdicts[0].citation == "刮痕方向为右向左"
        assert verdicts[0].event_id == "evt-1"
        assert "刮痕方向为右向左" in "报告写明：刮痕方向为右向左。"

    async def test_absent_verbatim_claim_is_unmentioned(self) -> None:
        verdicts = await verify_chapter_claims([_event()], 2, "报告只写了门闩。")

        assert verdicts[0].status == "unmentioned"
        assert verdicts[0].citation == ""

    async def test_contradict_term_wins_over_a_support_term(self) -> None:
        judge = AnchoredClaimJudge(
            [
                ClaimAnchor(
                    claim_id="claim-scratch",
                    support_terms=["刮痕"],
                    contradict_terms=["自内向外"],
                )
            ]
        )
        chapter = "横杆刮痕走向自内向外。"

        verdicts = await verify_chapter_claims([_event()], 2, chapter, judge=judge)

        assert verdicts[0].status == "contradicted"
        assert "自内向外" in verdicts[0].citation
        assert verdicts[0].citation in chapter

    async def test_pending_event_is_skipped(self) -> None:
        pending = _event().model_copy(update={"approval_status": "pending"})

        assert await verify_chapter_claims([pending], 2, "刮痕方向为右向左。") == []

    def test_parser_accepts_fenced_json(self) -> None:
        status, citation = parse_claim_judgment(
            '```json\n{"status":"contradicted","citation":"自内向外"}\n```'
        )

        assert status == "contradicted"
        assert citation == "自内向外"

    def test_parser_rejects_an_unknown_status(self) -> None:
        with pytest.raises(ClaimCheckError):
            parse_claim_judgment('{"status":"maybe","citation":""}')

    async def test_llm_judge_uses_injected_complete_and_drops_a_foreign_citation(self) -> None:
        seen: list[str] = []

        async def complete(prompt: str) -> str:
            seen.append(prompt)
            return '{"status":"supported","citation":"不在正文里的句子"}'

        judge = LlmClaimJudge(complete=complete)
        verdicts = await verify_chapter_claims([_event()], 2, "正文没有那句。", judge=judge)

        assert "刮痕方向为右向左" in seen[0]
        assert "正文没有那句。" in seen[0]
        assert verdicts[0].status == "supported"
        assert verdicts[0].citation == ""

    async def test_llm_judge_keeps_a_citation_that_is_in_the_chapter(self) -> None:
        async def complete(prompt: str) -> str:
            return '{"status":"contradicted","citation":"自内向外"}'

        judge = LlmClaimJudge(complete=complete)
        chapter = "横杆刮痕走向自内向外。"
        verdicts = await verify_chapter_claims([_event()], 2, chapter, judge=judge)

        assert verdicts[0].status == "contradicted"
        assert verdicts[0].citation == "自内向外"
        assert verdicts[0].citation in chapter
