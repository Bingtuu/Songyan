"""Revision models — Patch-based revision output."""

from pydantic import BaseModel, Field

from songyan.models.review import ReviewIssue


class Patch(BaseModel):
    """局部修订补丁."""

    issue_id: str
    original_text: str
    revised_text: str
    location: str


class RevisionInput(BaseModel):
    """RevisionHandler 输入."""

    version_id: str
    issues: list[ReviewIssue] = Field(default_factory=list)
    max_rounds: int = 2


class RevisionOutput(BaseModel):
    """RevisionHandler 输出 — 含回归检测."""

    new_version_id: str = ""
    patches_applied: list[Patch] = Field(default_factory=list)
    issues_fixed: list[str] = Field(default_factory=list)
    issues_remaining: list[str] = Field(default_factory=list)
    new_issues_introduced: list[ReviewIssue] = Field(default_factory=list)
    content_preservation_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    # 079: 分段修订元数据
    segmented: bool = False
    scenes_modified: int = 0
    scenes_fallback_count: int = 0
