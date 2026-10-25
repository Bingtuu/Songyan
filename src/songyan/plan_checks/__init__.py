"""Narrow plan-first checkers.

These functions compare one chapter to approved plan cards. They do not
write canon and do not read settlement tables. ``run_plan_fact_gate`` is
the read-only entry the chapter review path calls. SettlementExtractor
remains the writer of the old settlement database.
"""

from songyan.plan_checks.claim_check import (
    AnchoredClaimJudge,
    ClaimAnchor,
    ClaimCheckError,
    ClaimJudge,
    ClaimVerdict,
    LlmClaimJudge,
    parse_claim_judgment,
    verify_chapter_claims,
)
from songyan.plan_checks.gate import PlanFactGateReport, run_plan_fact_gate
from songyan.plan_checks.must_mention import MissingMention, check_must_mention
from songyan.plan_checks.typed_attributes import (
    AttributeExtract,
    AttributeMismatch,
    compare_typed_attributes,
)

__all__ = [
    "AnchoredClaimJudge",
    "AttributeExtract",
    "AttributeMismatch",
    "ClaimAnchor",
    "ClaimCheckError",
    "ClaimJudge",
    "ClaimVerdict",
    "LlmClaimJudge",
    "MissingMention",
    "PlanFactGateReport",
    "check_must_mention",
    "compare_typed_attributes",
    "parse_claim_judgment",
    "run_plan_fact_gate",
    "verify_chapter_claims",
]
