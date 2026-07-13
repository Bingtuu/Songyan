"""Repository for literary-quality / exposition-carrier keyword extraction."""

from __future__ import annotations

from sqlite3 import Row

import structlog

from songyan.db.connection import get_db

logger = structlog.get_logger(__name__)

# Heuristic markers that suggest a setting name refers to a non-human entity
# or in-world "speaker" that may deliver exposition directly.
_NON_CHARACTER_INDICATORS: set[str] = {
    "建造者",
    "织网者",
    "残影",
    "前代",
    "碎片",
    "守门人",
    "舰队",
    "意识",
    "协议",
    "锁",
    "核心",
    "装置",
    "方舟",
    "节点",
    "网络",
    "深渊",
    "社",
    "组织",
    "计划",
    "工程",
    "系统",
    "舰",
    "船",
    "艇",
    "基地",
    "站",
    "门",
    "通道",
    "层",
    "域",
    "界",
    "信号",
    "日志",
    "记录",
    "文明",
    "矩阵",
    "图谱",
    "序列",
    "基因",
    "共鸣",
    "密钥",
    "钥匙",
    "封印",
    "算法",
    "模型",
    "数据",
    "接口",
    "权限",
    "命令",
}


class LiteraryKeywordRepository:
    """Extract project-specific keywords for RuleAuditor exposition-carrier detection."""

    async def get_project_character_names(self, project_id: str) -> set[str]:
        """Return all character names for a project, falling back to protagonist_name."""
        names: set[str] = set()
        async with get_db() as conn:
            conn.row_factory = Row
            cur = await conn.execute(
                "SELECT name FROM characters WHERE project_id = ?",
                (project_id,),
            )
            rows = await cur.fetchall()
        for row in rows:
            if row["name"]:
                names.add(row["name"])

        if not names:
            # No characters row yet; use the project seed.
            async with get_db() as conn:
                conn.row_factory = Row
                cur = await conn.execute(
                    "SELECT protagonist_name FROM projects WHERE project_id = ?",
                    (project_id,),
                )
                project_row: Row | None = await cur.fetchone()
            if project_row and project_row["protagonist_name"]:
                names.add(project_row["protagonist_name"])
        return names

    async def get_project_setting_keywords(
        self,
        project_id: str,
        min_length: int = 2,
    ) -> set[str]:
        """Return setting names and key segments likely to appear in prose."""
        keywords: set[str] = set()
        async with get_db() as conn:
            conn.row_factory = Row
            cur = await conn.execute(
                """
                SELECT setting_key, setting_name
                FROM setting_snapshots
                WHERE project_id = ? AND lifecycle_status = 'active'
                """,
                (project_id,),
            )
            rows = await cur.fetchall()
        for row in rows:
            name = (row["setting_name"] or "").strip()
            if name and len(name) >= min_length:
                keywords.add(name)

            key = row["setting_key"] or ""
            if key:
                # The last dotted segment is most likely to be reused as a term.
                last = key.split(".")[-1]
                if last and len(last) >= min_length:
                    keywords.add(last)
                # Undotted keys are also usable aliases.
                if "." not in key and len(key) >= min_length:
                    keywords.add(key)
        return keywords

    async def get_project_non_character_entities(
        self,
        project_id: str,
        setting_keywords: set[str] | None = None,
    ) -> set[str]:
        """Return setting names that look like non-human entities/speakers."""
        candidates = setting_keywords
        if candidates is None:
            candidates = await self.get_project_setting_keywords(project_id)

        entities: set[str] = set()
        for kw in candidates:
            for indicator in _NON_CHARACTER_INDICATORS:
                if indicator in kw:
                    entities.add(kw)
                    break
        return entities

    async def load_exposition_keywords(
        self,
        project_id: str,
    ) -> dict[str, set[str]]:
        """Load all keyword sets needed by ``detect_exposition_carriers``."""
        characters = await self.get_project_character_names(project_id)
        settings = await self.get_project_setting_keywords(project_id)
        non_char = await self.get_project_non_character_entities(project_id, settings)
        logger.info(
            "literary_keywords.loaded",
            project_id=project_id,
            character_count=len(characters),
            setting_keyword_count=len(settings),
            non_character_entity_count=len(non_char),
        )
        return {
            "character_names": characters,
            "setting_keywords": settings,
            "non_character_keywords": non_char,
        }
