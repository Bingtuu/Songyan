"""Narrow claim check: one event-card proposition against one chapter.

The deterministic judge only looks for phrases supplied with that claim.
The LLM judge sends that same pair (claim text + chapter) and must return
a status plus a citation snippet. Neither judge searches the book for
other contradictions.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from songyan.exceptions import SongyanError
from songyan.models.plan_facts import PlanClaim, PlanEvent

ClaimStatus = Literal["supported", "contradicted", "unmentioned"]
_STATUSES: frozenset[str] = frozenset({"supported", "contradicted", "unmentioned"})


class ClaimCheckError(SongyanError):
    """A claim judgment was not the narrow JSON this checker accepts."""


class ClaimVerdict(BaseModel):
    """Judgment of one claim, with a citation that is a substring of the chapter."""

    claim_id: str
    text: str
    status: ClaimStatus
    citation: str = ""
    event_id: str | None = None
    chapter: int | None = None


class ClaimAnchor(BaseModel):
    """Phrases the deterministic judge may use for one claim.

    ``contradict_terms`` are checked first. They are part of the fixture
    for that claim, not a list of things to hunt for in other chapters.
    """

    claim_id: str
    support_terms: list[str] = Field(default_factory=list)
    contradict_terms: list[str] = Field(default_factory=list)

    @field_validator("support_terms", "contradict_terms")
    @classmethod
    def terms_are_non_empty(cls, value: list[str]) -> list[str]:
        """An empty phrase matches every string."""
        if any(not term for term in value):
            raise ValueError("anchor terms must be non-empty")
        return value


class ClaimJudge(Protocol):
    """Judge one claim against one chapter."""

    async def judge(self, claim: PlanClaim, chapter_text: str) -> ClaimVerdict:
        """Return supported, contradicted, or unmentioned."""


class AnchoredClaimJudge:
    """Deterministic judge. No model call.

    With an anchor, a contradicting phrase wins, then a supporting phrase.
    With no anchor, the claim text itself must appear verbatim to count
    as supported. Anything else is unmentioned.
    """

    def __init__(self, anchors: list[ClaimAnchor] | None = None) -> None:
        self._anchors: dict[str, ClaimAnchor] = {}
        for anchor in anchors or []:
            if anchor.claim_id in self._anchors:
                raise ClaimCheckError(f"duplicate claim anchor: {anchor.claim_id}")
            self._anchors[anchor.claim_id] = anchor

    async def judge(self, claim: PlanClaim, chapter_text: str) -> ClaimVerdict:
        """Classify ``claim`` using its anchor, or the claim text verbatim."""
        anchor = self._anchors.get(claim.claim_id)
        if anchor is None:
            if claim.text in chapter_text:
                return _verdict(claim, "supported", claim.text)
            return _verdict(claim, "unmentioned", "")

        for term in anchor.contradict_terms:
            if term in chapter_text:
                return _verdict(claim, "contradicted", _snippet(chapter_text, term))
        for term in anchor.support_terms:
            if term in chapter_text:
                return _verdict(claim, "supported", _snippet(chapter_text, term))
        return _verdict(claim, "unmentioned", "")


class LlmClaimJudge:
    """Ask the project LLM to classify one claim. Tests inject ``complete``."""

    def __init__(self, complete: Callable[[str], Awaitable[str]] | None = None) -> None:
        self._complete = complete

    async def judge(self, claim: PlanClaim, chapter_text: str) -> ClaimVerdict:
        """Classify ``claim`` and drop a citation that is not in the chapter."""
        complete = self._complete or _default_complete
        raw = await complete(_prompt(claim.text, chapter_text))
        status, citation = parse_claim_judgment(raw)
        if citation not in chapter_text:
            citation = ""
        return _verdict(claim, status, citation)


def parse_claim_judgment(raw: str) -> tuple[ClaimStatus, str]:
    """Parse ``{"status", "citation"}`` from a model reply.

    A fenced block is accepted. ``citation`` may be empty.
    """
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ClaimCheckError("claim judgment is not JSON")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ClaimCheckError("claim judgment JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise ClaimCheckError("claim judgment JSON is not an object")
    status = payload.get("status")
    if status not in _STATUSES:
        raise ClaimCheckError(f"claim judgment status is invalid: {status!r}")
    citation = payload.get("citation", "")
    if citation is None:
        citation = ""
    if not isinstance(citation, str):
        raise ClaimCheckError("claim judgment citation is not text")
    if status == "supported":
        return "supported", citation
    if status == "contradicted":
        return "contradicted", citation
    return "unmentioned", citation


async def verify_chapter_claims(
    events: list[PlanEvent],
    chapter: int,
    chapter_text: str,
    *,
    judge: ClaimJudge | None = None,
) -> list[ClaimVerdict]:
    """Judge approved claims whose event is in ``chapter``.

    The default judge is deterministic and does not call a model.
    Pending events are skipped.
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")
    active: ClaimJudge = judge if judge is not None else AnchoredClaimJudge()
    verdicts: list[ClaimVerdict] = []
    for event in events:
        if event.approval_status != "approved" or event.ch != chapter:
            continue
        for claim in event.claims:
            verdict = await active.judge(claim, chapter_text)
            verdicts.append(
                verdict.model_copy(update={"event_id": event.event_id, "chapter": chapter})
            )
    return verdicts


def _verdict(claim: PlanClaim, status: ClaimStatus, citation: str) -> ClaimVerdict:
    return ClaimVerdict(
        claim_id=claim.claim_id,
        text=claim.text,
        status=status,
        citation=citation,
    )


def _snippet(text: str, needle: str, radius: int = 40) -> str:
    index = text.find(needle)
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return text[start:end]


def _prompt(claim: str, chapter_text: str) -> str:
    return (
        "你只判断下面这一条主张和这一章正文是否一致。"
        "不要寻找主张以外的矛盾，也不要评价文笔。\n"
        f"主张：{claim}\n"
        "正文：\n"
        f"{chapter_text}\n"
        "只输出 JSON，不要其它文字："
        '{"status":"supported"|"contradicted"|"unmentioned","citation":"正文中的连续原文，没有则为空字符串"}\n'
        "supported 表示正文支持该主张；contradicted 表示正文写出了与主张相反的内容；"
        "unmentioned 表示正文没有写到。citation 必须是正文的连续子串。"
    )


async def _default_complete(prompt: str) -> str:
    from songyan.llm.client import call_llm

    return await call_llm(prompt, temperature=0.0, max_tokens=512)
