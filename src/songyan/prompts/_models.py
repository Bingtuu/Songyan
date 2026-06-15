"""Pydantic models for Craft Card system."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CraftCardMetadata(BaseModel):
    """Metadata for a craft card."""

    agent: str
    version: str
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    author: str = ""
    created_at: str = ""
    updated_at: str = ""


class CraftCardSection(BaseModel):
    """A single craft instruction section."""

    id: str
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    weight: float = 1.0
    content: str = ""


class CraftCardVariable(BaseModel):
    """Variable declaration for template rendering."""

    name: str
    type: str = "str"
    required: bool = True
    description: str = ""


class CraftCard(BaseModel):
    """A complete craft card for an agent."""

    metadata: CraftCardMetadata
    system_prompt: str = ""
    sections: list[CraftCardSection] = Field(default_factory=list)
    variables: list[CraftCardVariable] = Field(default_factory=list)


class VersionInfo(BaseModel):
    """Version entry in a manifest."""

    version: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class Manifest(BaseModel):
    """Manifest for an agent's craft cards."""

    agent: str
    default_version: str
    versions: list[VersionInfo] = Field(default_factory=list)


class RenderedPrompt(BaseModel):
    """Result of rendering a craft card."""

    system_prompt: str
    sections_content: str = ""
    full_prompt: str = ""
    active_sections: list[str] = Field(default_factory=list)
