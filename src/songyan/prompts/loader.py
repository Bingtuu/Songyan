"""Craft Card loader — module-level singleton with caching."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import structlog
import yaml
from jinja2 import Template

from songyan.prompts._models import (
    CraftCard,
    Manifest,
    RenderedPrompt,
    VersionInfo,
)

logger = structlog.get_logger()

_CARDS_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "cards"


class PromptLoader:
    """Load and render craft cards from YAML files.

    Use :func:`get_prompt_loader` to obtain the singleton instance.
    """

    def __init__(self, cards_dir: Path | None = None) -> None:
        self._cards_dir = cards_dir or _CARDS_DIR
        self._manifests: dict[str, Manifest] = {}
        self._cache: dict[str, CraftCard] = {}
        self._render_cache: dict[str, tuple[RenderedPrompt, float]] = {}
        self._cache_ttl: float = 60.0
        self._scan()

    def _scan(self) -> None:
        """Scan cards/ directory and load all manifests."""
        if not self._cards_dir.exists():
            logger.warning("cards_dir_not_found", path=str(self._cards_dir))
            return
        for agent_dir in self._cards_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            manifest_path = agent_dir / "_manifest.yaml"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    manifest = Manifest(**data)
                    self._manifests[manifest.agent] = manifest
                    logger.debug("manifest_loaded", agent=manifest.agent)
                except Exception:
                    logger.warning("manifest_load_failed", path=str(manifest_path))

    def _card_path(self, agent: str, version: str) -> Path:
        return self._cards_dir / agent / f"{version}.yaml"

    def _load_card_file(self, agent: str, version: str) -> CraftCard:
        path = self._card_path(agent, version)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return CraftCard(**data)

    def load_card(
        self,
        agent: str,
        version: str | None = None,
        tags: list[str] | None = None,
    ) -> CraftCard:
        """Load a craft card for *agent*.

        Args:
            agent: Agent identifier (e.g. "writer").
            version: Specific version to load.  If ``None``, uses the
                manifest's ``default_version``.
            tags: Optional tags used by :meth:`get_active_sections`.
                Not used during loading, but stored for convenience.

        Raises:
            KeyError: If the agent or version is not found.
        """
        manifest = self._manifests.get(agent)
        if manifest is None:
            raise KeyError(f"No craft cards found for agent '{agent}'")

        version = version or manifest.default_version
        cache_key = f"{agent}:{version}"

        if cache_key not in self._cache:
            self._cache[cache_key] = self._load_card_file(agent, version)
            logger.debug("card_loaded", agent=agent, version=version)

        return self._cache[cache_key]

    def list_versions(self, agent: str) -> list[VersionInfo]:
        """Return all registered versions for *agent*."""
        manifest = self._manifests.get(agent)
        if manifest is None:
            raise KeyError(f"No craft cards found for agent '{agent}'")
        return manifest.versions

    def get_active_sections(
        self,
        card: CraftCard,
        tags: list[str] | None = None,
    ) -> list[str]:
        """Return IDs of sections that match *tags*.

        A section is active when:
        - It has no tags (unconditional), OR
        - At least one of its tags is in *tags*.

        Sections are returned sorted by descending weight.
        """
        tags_set = set(tags or [])
        active: list[tuple[float, str]] = []
        for section in card.sections:
            if not section.tags or any(t in tags_set for t in section.tags):
                active.append((section.weight, section.id))
        active.sort(key=lambda x: (-x[0], x[1]))
        return [sid for _, sid in active]

    def render_card(
        self,
        card: CraftCard,
        variables: dict[str, Any],
        tags: list[str] | None = None,
    ) -> RenderedPrompt:
        """Render *card* with *variables* into a final prompt string.

        Args:
            card: The craft card to render.
            variables: Values for Jinja2 template variables.
            tags: Tags to filter active sections.

        Returns:
            A :class:`RenderedPrompt` with ``system_prompt``,
            ``sections_content``, ``full_prompt``, and ``active_sections``.
        """
        # Cache key based on card version + sorted variables + tags
        var_key = hashlib.sha256(
            json.dumps(variables, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        tag_key = ",".join(sorted(tags or []))
        cache_key = f"{card.metadata.agent}:{card.metadata.version}:{var_key}:{tag_key}"

        now = time.time()
        if cache_key in self._render_cache:
            cached, cached_at = self._render_cache[cache_key]
            if now - cached_at < self._cache_ttl:
                logger.debug("render_cache_hit", key=cache_key)
                return cached

        active_ids = self.get_active_sections(card, tags)
        active_sections = [s for s in card.sections if s.id in active_ids]

        # Render system prompt
        system = ""
        if card.system_prompt:
            system = Template(card.system_prompt).render(**variables)

        # Render active sections
        parts: list[str] = []
        for section in active_sections:
            rendered = Template(section.content).render(**variables)
            parts.append(f"## {section.name}\n\n{rendered}")
        sections_content = "\n\n".join(parts)

        # Assemble full prompt
        full_parts: list[str] = []
        if system:
            full_parts.append(system)
        if sections_content:
            full_parts.append(sections_content)
        full_prompt = "\n\n".join(full_parts)

        result = RenderedPrompt(
            system_prompt=system,
            sections_content=sections_content,
            full_prompt=full_prompt,
            active_sections=active_ids,
        )

        self._render_cache[cache_key] = (result, now)
        logger.info(
            "craft_card_rendered",
            agent=card.metadata.agent,
            version=card.metadata.version,
            active_sections=active_ids,
            rendered_length=len(full_prompt),
        )
        return result


_loader_instance: PromptLoader | None = None


def get_prompt_loader(cards_dir: Path | None = None) -> PromptLoader:
    """Return the module-level singleton :class:`PromptLoader`.

    The first call scans the ``prompts/cards/`` directory and caches
    manifests.  Subsequent calls return the same instance.
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = PromptLoader(cards_dir=cards_dir)
    return _loader_instance


def reset_prompt_loader() -> None:
    """Reset the singleton (mainly for testing)."""
    global _loader_instance
    _loader_instance = None
