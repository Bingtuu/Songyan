"""Narrow plan-first checkers.

These functions compare one chapter to approved plan cards. They do not
write canon and do not read settlement tables. ``run_plan_fact_gate`` is
the read-only entry the chapter review path calls.
``load_chapter_plan_bible`` is the read the writer and revision prompts
use. SettlementExtractor remains the writer of the old settlement database.
"""

from songyan.plan_checks.bible import (
    ChapterPlanBible,
    load_chapter_plan_bible,
    plan_fact_gate_failure_lines,
    wrap_writing_prompt,
)
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
from songyan.plan_checks.observe import observe_plan_review_inputs
from songyan.plan_checks.roadmap_recall import (
    RecallScoreboard,
    blocked_rerun_scoreboard,
    score_chapters,
    score_reports,
)
from songyan.plan_checks.typed_attributes import (
    AttributeExtract,
    AttributeMismatch,
    compare_typed_attributes,
)

__all__ = [
    "AnchoredClaimJudge",
    "AttributeExtract",
    "ChapterPlanBible",
    "AttributeMismatch",
    "ClaimAnchor",
    "ClaimCheckError",
    "ClaimJudge",
    "ClaimVerdict",
    "LlmClaimJudge",
    "MissingMention",
    "PlanFactGateReport",
    "RecallScoreboard",
    "blocked_rerun_scoreboard",
    "check_must_mention",
    "compare_typed_attributes",
    "load_chapter_plan_bible",
    "plan_fact_gate_failure_lines",
    "observe_plan_review_inputs",
    "parse_claim_judgment",
    "run_plan_fact_gate",
    "score_chapters",
    "score_reports",
    "verify_chapter_claims",
    "wrap_writing_prompt",
]
