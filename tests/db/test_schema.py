"""Schema 验证测试 — 表存在、约束生效、外键生效."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from songyan.db.migrations import init_schema, verify_schema

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_conn(tmp_path: Path):
    """提供已初始化 schema 的数据库连接."""
    import aiosqlite

    db_path = tmp_path / "test.db"
    await init_schema(db_path)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn


class TestSchemaInit:
    """Schema 初始化基础测试."""

    async def test_init_schema_creates_all_tables(self, tmp_path: Path) -> None:
        """初始化后 13 张表全部存在."""
        import aiosqlite

        db_path = tmp_path / "test.db"
        await init_schema(db_path)

        async with aiosqlite.connect(db_path) as conn:
            missing = await verify_schema(conn)

        assert missing == [], f"Missing tables: {missing}"

    async def test_init_schema_is_idempotent(self, tmp_path: Path) -> None:
        """多次初始化不报错（IF NOT EXISTS 幂等）."""
        db_path = tmp_path / "test.db"
        await init_schema(db_path)
        await init_schema(db_path)  # 第二次不应抛错

        import aiosqlite

        async with aiosqlite.connect(db_path) as conn:
            missing = await verify_schema(conn)
        assert missing == []

    async def test_verify_schema_returns_missing(self, tmp_path: Path) -> None:
        """verify_schema 在未初始化 DB 上返回全部 13 个表名."""
        import aiosqlite

        db_path = tmp_path / "test.db"
        async with aiosqlite.connect(db_path) as conn:
            missing = await verify_schema(conn)
        assert len(missing) == 13

    async def test_wal_mode_enabled(self, db_conn) -> None:
        """schema.sql 设置了 WAL 模式."""
        cursor = await db_conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0].lower() == "wal"

    async def test_foreign_keys_enabled(self, db_conn) -> None:
        """schema.sql 设置了外键."""
        cursor = await db_conn.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1


class TestConstraints:
    """唯一约束与外键约束测试."""

    async def test_chapter_versions_unique_constraint(self, db_conn) -> None:
        """UNIQUE(project_id, chapter_number, version_number) 生效."""
        pid = str(uuid.uuid4())
        # 先插入 project
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        await db_conn.commit()

        # 插入第一个 version
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), pid, 1, 1),
        )
        await db_conn.commit()

        # 重复插入应抛 IntegrityError
        with pytest.raises(Exception):  # aiosqlite.IntegrityError
            await db_conn.execute(
                "INSERT INTO chapter_versions"
                " (version_id, project_id, chapter_number, version_number)"
                " VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, 1, 1),
            )
            await db_conn.commit()

    async def test_foreign_key_project_cascade(self, db_conn) -> None:
        """删除 project 级联删除关联 character."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        cid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO characters (character_id, project_id, name) VALUES (?, ?, ?)",
            (cid, pid, "Hero"),
        )
        await db_conn.commit()

        # 删除 project
        await db_conn.execute("DELETE FROM projects WHERE project_id = ?", (pid,))
        await db_conn.commit()

        # character 应被级联删除
        cursor = await db_conn.execute(
            "SELECT 1 FROM characters WHERE character_id = ?", (cid,)
        )
        row = await cursor.fetchone()
        assert row is None

    async def test_foreign_key_violation(self, db_conn) -> None:
        """插入违反外键的行应抛 IntegrityError."""
        with pytest.raises(Exception):
            await db_conn.execute(
                "INSERT INTO characters (character_id, project_id, name) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), "nonexistent_project", "Hero"),
            )
            await db_conn.commit()

    async def test_chapter_versions_parent_self_ref(self, db_conn) -> None:
        """chapter_versions 自引用外键（parent_version_id）生效."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        await db_conn.commit()

        v1 = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (v1, pid, 1, 1),
        )
        v2 = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number, parent_version_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (v2, pid, 1, 2, v1),
        )
        await db_conn.commit()

        # 验证版本链
        cursor = await db_conn.execute(
            "SELECT parent_version_id FROM chapter_versions WHERE version_id = ?",
            (v2,),
        )
        row = await cursor.fetchone()
        assert row[0] == v1


class TestSnapshotTables:
    """快照表行为测试."""

    async def test_character_states_multiple_insert(self, db_conn) -> None:
        """character_states 可多次 INSERT，模拟快照行为."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        cid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO characters (character_id, project_id, name) VALUES (?, ?, ?)",
            (cid, pid, "Hero"),
        )
        vid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (vid, pid, 1, 1),
        )
        await db_conn.commit()

        # 同一角色多次状态变更，每条都 INSERT
        for i in range(3):
            await db_conn.execute(
                "INSERT INTO character_states"
            " (character_id, field, value, source_version_id)"
            " VALUES (?, ?, ?, ?)",
                (cid, "power_level", str(100 + i * 10), vid),
            )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT COUNT(*) FROM character_states WHERE character_id = ?",
            (cid,),
        )
        row = await cursor.fetchone()
        assert row[0] == 3

    async def test_chapter_versions_immutable_semantic(self, db_conn) -> None:
        """chapter_versions 技术上可 UPDATE，但语义上禁止覆盖（由 Repository 层保证）."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        vid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number, content)"
            " VALUES (?, ?, ?, ?, ?)",
            (vid, pid, 1, 1, "old content"),
        )
        await db_conn.commit()

        # 技术上 SQLite 允许 UPDATE（这里仅验证表结构，不测试业务规则）
        await db_conn.execute(
            "UPDATE chapter_versions SET content = ? WHERE version_id = ?",
            ("new content", vid),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT content FROM chapter_versions WHERE version_id = ?", (vid,)
        )
        row = await cursor.fetchone()
        assert row[0] == "new content"


class TestCreativeBriefsAndLiterary:
    """V2 新增表测试."""

    async def test_creative_briefs_insert(self, db_conn) -> None:
        """creative_briefs 可正常插入（含 JSON 字段）."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        await db_conn.commit()

        bid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO creative_briefs (
                brief_id, project_id, chapter_number, mode_id,
                creative_intent, required_tensions, forbidden_patterns
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (bid, pid, 1, "webnovel", "test intent", '[{"tension_id":"t1"}]', '["no cliche"]'),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT required_tensions, forbidden_patterns FROM creative_briefs WHERE brief_id = ?",
            (bid,),
        )
        row = await cursor.fetchone()
        assert "t1" in row[0]
        assert "no cliche" in row[1]

    async def test_literary_observations_insert(self, db_conn) -> None:
        """literary_observations 可正常插入."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        vid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (vid, pid, 1, 1),
        )
        await db_conn.commit()

        oid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO literary_observations (
                observation_id, version_id, observations, literary_quality_score
            ) VALUES (?, ?, ?, ?)""",
            (oid, vid, '[{"observation_id":"o1","type":"cliche_risk"}]', 7.5),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT literary_quality_score FROM literary_observations WHERE observation_id = ?",
            (oid,),
        )
        row = await cursor.fetchone()
        assert row[0] == 7.5

    async def test_review_reports_audit_fields(self, db_conn) -> None:
        """review_reports 含 audit_type + rule_audit_result + llm_audit_result."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        vid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (vid, pid, 1, 1),
        )
        await db_conn.commit()

        rid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO review_reports (
                report_id, chapter_version_id, audit_type,
                rule_audit_result, llm_audit_result, issues
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                rid,
                vid,
                "merged",
                '{"ai_tell_count": 2}',
                '{"cliche_risk_score": 3.5}',
                '[{"issue_id":"i1","severity":"major"}]',
            ),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT audit_type, rule_audit_result, llm_audit_result"
            " FROM review_reports WHERE report_id = ?",
            (rid,),
        )
        row = await cursor.fetchone()
        assert row[0] == "merged"
        assert "ai_tell_count" in row[1]
        assert "cliche_risk_score" in row[2]


class TestForeshadowingsAndSettings:
    """伏笔与设定表测试."""

    async def test_foreshadowings_source_version_id(self, db_conn) -> None:
        """foreshadowings 含 source_version_id 字段."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        vid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO chapter_versions"
            " (version_id, project_id, chapter_number, version_number)"
            " VALUES (?, ?, ?, ?)",
            (vid, pid, 1, 1),
        )
        await db_conn.commit()

        fid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO foreshadowings (
                foreshadowing_id, project_id, description, planted_in_chapter, source_version_id
            ) VALUES (?, ?, ?, ?, ?)""",
            (fid, pid, "A mysterious artifact", 1, vid),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT source_version_id FROM foreshadowings WHERE foreshadowing_id = ?",
            (fid,),
        )
        row = await cursor.fetchone()
        assert row[0] == vid

    async def test_setting_snapshots_setting_key(self, db_conn) -> None:
        """setting_snapshots 含 setting_key 字段."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        await db_conn.commit()

        sid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO setting_snapshots (
                setting_id, project_id, setting_name, description, source_quote, setting_key
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (sid, pid, "青玄宗", "四大宗门之首", "青玄宗立于云端", "sect_qingxuan"),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT setting_key FROM setting_snapshots WHERE setting_id = ?",
            (sid,),
        )
        row = await cursor.fetchone()
        assert row[0] == "sect_qingxuan"


class TestProjectsAndCharacters:
    """基础表 CRUD 测试."""

    async def test_projects_crud(self, db_conn) -> None:
        """projects 基础 INSERT / SELECT."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO projects (
                project_id, title, genre_id, mode_id, protagonist_name,
                taboos, target_word_count, tone
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, "Test Novel", "xuanhuan", "webnovel", "Lin Feng", '["ntr"]', 200000, "热血"),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT title, genre_id, mode_id, taboos, target_word_count"
            " FROM projects WHERE project_id = ?",
            (pid,),
        )
        row = await cursor.fetchone()
        assert row[0] == "Test Novel"
        assert row[1] == "xuanhuan"
        assert row[2] == "webnovel"
        assert "ntr" in row[3]
        assert row[4] == 200000

    async def test_characters_json_fields(self, db_conn) -> None:
        """characters 的 JSON 字段可正确存储."""
        pid = str(uuid.uuid4())
        await db_conn.execute(
            "INSERT INTO projects (project_id, genre_id, protagonist_name) VALUES (?, ?, ?)",
            (pid, "xuanhuan", "Test"),
        )
        await db_conn.commit()

        cid = str(uuid.uuid4())
        await db_conn.execute(
            """INSERT INTO characters (
                character_id, project_id, name, role_type,
                personality_traits, goals, relationships
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                pid,
                "Lin Feng",
                "protagonist",
                '["brave", "stubborn"]',
                '["revenge", "protect family"]',
                '{"master": " Elder Wang"}',
            ),
        )
        await db_conn.commit()

        cursor = await db_conn.execute(
            "SELECT personality_traits, goals, relationships"
            " FROM characters WHERE character_id = ?",
            (cid,),
        )
        row = await cursor.fetchone()
        assert "brave" in row[0]
        assert "revenge" in row[1]
        assert "Elder Wang" in row[2]
