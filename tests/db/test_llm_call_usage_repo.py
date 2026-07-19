"""Tests for V9 Task 175 — llm_call_usage 表与 LlmCallUsageRepository."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
from structlog.testing import capture_logs

from songyan.db.llm_call_usage_repo import (
    CostSource,
    LlmCallUsageRepository,
    TokenSource,
)
from songyan.db.migrations import init_schema, run_migrations, verify_schema

pytestmark = pytest.mark.asyncio

_EXPECTED_INDEXES = {"idx_llm_call_usage_run", "idx_llm_call_usage_run_chapter"}


async def _index_names(conn: aiosqlite.Connection) -> set[str]:
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    )
    return {row[0] for row in await cursor.fetchall()}


class TestMigration:
    """schema / migration 层：新库与旧库路径都能得到 llm_call_usage."""

    async def test_init_schema_creates_table_and_verify_passes(
        self, tmp_path: Path
    ) -> None:
        """新库 init_schema 后 llm_call_usage 存在且 verify_schema 不 missing."""
        db_path = tmp_path / "init.db"
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            names = {row[0] for row in await cursor.fetchall()}
            assert "llm_call_usage" in names
            assert _EXPECTED_INDEXES <= await _index_names(conn)
            assert await verify_schema(conn) == []

    async def test_run_migrations_backfills_old_db(self, tmp_path: Path) -> None:
        """旧库（缺新表）跑 run_migrations 后 llm_call_usage 出现."""
        db_path = tmp_path / "old.db"
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            # 模拟旧库：删掉新表
            await conn.execute("DROP TABLE llm_call_usage")
            await conn.commit()

            await run_migrations(conn)
            await conn.commit()

            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            names = {row[0] for row in await cursor.fetchall()}
            assert "llm_call_usage" in names
            assert _EXPECTED_INDEXES <= await _index_names(conn)
            assert await verify_schema(conn) == []


class TestRecord:
    """record 单行写入与失败容错."""

    async def _fetch_rows(self, db_file: Path) -> list[dict]:
        async with aiosqlite.connect(str(db_file)) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM llm_call_usage ORDER BY id"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def test_record_writes_full_row(self, test_db: Path) -> None:
        """record 正常写入一行，各字段正确."""
        repo = LlmCallUsageRepository()
        await repo.record(
            run_id="run-1",
            project_id="proj-1",
            chapter_number=3,
            agent="writer",
            stage="write",
            version_id="v-1",
            model="kimi-k2",
            prompt_tokens=1200,
            completion_tokens=800,
            cost_cny=0.12,
            token_source="response",
            cost_source="provider_cost",
            cached_tokens=100,
            cache_miss_tokens=1100,
            latency_ms=2500,
            retry_attempt=1,
            success=True,
            error=None,
        )

        rows = await self._fetch_rows(test_db)
        assert len(rows) == 1
        row = rows[0]
        assert row["run_id"] == "run-1"
        assert row["project_id"] == "proj-1"
        assert row["chapter_number"] == 3
        assert row["agent"] == "writer"
        assert row["stage"] == "write"
        assert row["version_id"] == "v-1"
        assert row["model"] == "kimi-k2"
        assert row["prompt_tokens"] == 1200
        assert row["completion_tokens"] == 800
        assert row["cost_cny"] == pytest.approx(0.12)
        assert row["token_source"] == "response"
        assert row["cost_source"] == "provider_cost"
        assert row["cached_tokens"] == 100
        assert row["cache_miss_tokens"] == 1100
        assert row["latency_ms"] == 2500
        assert row["retry_attempt"] == 1
        assert row["success"] == 1
        assert row["error"] is None
        assert row["created_at"]

    async def test_record_minimal_row_allows_nulls(self, test_db: Path) -> None:
        """非 run 上下文：可空字段写 NULL，agent 默认 'unknown'."""
        repo = LlmCallUsageRepository()
        await repo.record(
            model="kimi-k2",
            token_source="estimate",
            cost_source="pricing_estimate",
        )

        rows = await self._fetch_rows(test_db)
        assert len(rows) == 1
        row = rows[0]
        assert row["run_id"] is None
        assert row["project_id"] is None
        assert row["chapter_number"] is None
        assert row["agent"] == "unknown"
        assert row["stage"] is None
        assert row["version_id"] is None
        assert row["prompt_tokens"] == 0
        assert row["completion_tokens"] == 0
        assert row["cost_cny"] == pytest.approx(0.0)
        assert row["cached_tokens"] is None
        assert row["cache_miss_tokens"] is None
        assert row["latency_ms"] == 0
        assert row["retry_attempt"] == 0
        assert row["success"] == 1

    async def test_record_failure_only_warns(self, test_db: Path) -> None:
        """record 在表缺失等异常时不抛异常，只 warning."""
        async with aiosqlite.connect(str(test_db)) as conn:
            await conn.execute("DROP TABLE llm_call_usage")
            await conn.commit()

        repo = LlmCallUsageRepository()
        with capture_logs() as logs:
            await repo.record(
                run_id="run-1",
                model="kimi-k2",
                token_source="response",
                cost_source="provider_cost",
            )

        warnings = [entry for entry in logs if entry.get("log_level") == "warning"]
        assert warnings, "record 失败应产生 structlog warning"


class TestSumCostForRun:
    """sum_cost_for_run 合计."""

    async def test_sum_cost_for_run(self, test_db: Path) -> None:
        """按 run 合计 cost_cny；其他 run 不计入."""
        repo = LlmCallUsageRepository()
        for run_id, cost in (("run-a", 0.5), ("run-a", 1.5), ("run-b", 2.0)):
            await repo.record(
                run_id=run_id,
                model="kimi-k2",
                cost_cny=cost,
                token_source="response",
                cost_source="provider_cost",
            )

        assert await repo.sum_cost_for_run("run-a") == pytest.approx(2.0)
        assert await repo.sum_cost_for_run("run-b") == pytest.approx(2.0)

    async def test_sum_cost_for_empty_run_returns_zero(self, test_db: Path) -> None:
        """无记录的 run 返回 0.0."""
        repo = LlmCallUsageRepository()
        assert await repo.sum_cost_for_run("no-such-run") == 0.0


class TestAggregateForRun:
    """aggregate_for_run 按 chapter / agent 分组聚合."""

    async def test_aggregate_groups_by_chapter_and_agent(self, test_db: Path) -> None:
        repo = LlmCallUsageRepository()
        rows = [
            ("run-a", 1, "writer", 100, 200, 1.0),
            ("run-a", 1, "writer", 50, 50, 0.5),
            ("run-a", 2, "llm_auditor", 10, 20, 0.1),
            # 其他 run 的噪声行，不应计入
            ("run-b", 1, "writer", 999, 999, 9.9),
        ]
        for run_id, chapter, agent, prompt, completion, cost in rows:
            await repo.record(
                run_id=run_id,
                chapter_number=chapter,
                agent=agent,
                model="kimi-k2",
                prompt_tokens=prompt,
                completion_tokens=completion,
                cost_cny=cost,
                token_source="response",
                cost_source="provider_cost",
            )

        result = await repo.aggregate_for_run("run-a")

        per_chapter = result["per_chapter"]
        assert len(per_chapter) == 2
        ch1, ch2 = per_chapter
        assert ch1["chapter_number"] == 1
        assert ch1["call_count"] == 2
        assert ch1["prompt_tokens"] == 150
        assert ch1["completion_tokens"] == 250
        assert ch1["cost_cny"] == pytest.approx(1.5)
        assert ch2["chapter_number"] == 2
        assert ch2["call_count"] == 1
        assert ch2["prompt_tokens"] == 10
        assert ch2["completion_tokens"] == 20
        assert ch2["cost_cny"] == pytest.approx(0.1)

        per_agent = result["per_agent"]
        assert len(per_agent) == 2
        by_agent = {entry["agent"]: entry for entry in per_agent}
        writer = by_agent["writer"]
        assert writer["call_count"] == 2
        assert writer["prompt_tokens"] == 150
        assert writer["completion_tokens"] == 250
        assert writer["cost_cny"] == pytest.approx(1.5)
        auditor = by_agent["llm_auditor"]
        assert auditor["call_count"] == 1
        assert auditor["cost_cny"] == pytest.approx(0.1)

    async def test_aggregate_for_empty_run(self, test_db: Path) -> None:
        """无记录的 run 返回空分组."""
        repo = LlmCallUsageRepository()
        result = await repo.aggregate_for_run("no-such-run")
        assert result == {"per_chapter": [], "per_agent": []}


class TestSourceStatsForRun:
    """source_stats_for_run：token_source / cost_source 分布计数（report 估算占比的分子分母）."""

    async def test_mixed_sources_counts_numerators_and_denominator(
        self, test_db: Path
    ) -> None:
        """混合 token_source / cost_source 行：两个占比的分子分母都正确，其他 run 不计入."""
        repo = LlmCallUsageRepository()
        rows: list[tuple[str, TokenSource, CostSource]] = [
            ("run-a", "response", "provider_cost"),
            ("run-a", "estimate", "pricing_estimate"),
            ("run-a", "response", "pricing_estimate"),
            # 两个维度独立计数：estimate 的 token 也可能拿到 provider_cost
            ("run-a", "estimate", "provider_cost"),
            # 其他 run 的噪声行，不应计入
            ("run-b", "estimate", "pricing_estimate"),
        ]
        for run_id, token_source, cost_source in rows:
            await repo.record(
                run_id=run_id,
                model="kimi-k2",
                token_source=token_source,
                cost_source=cost_source,
            )
        # 失败尝试（success=0）默认 estimate 标记，但不应计入估算占比（只统计成功调用）
        await repo.record(
            run_id="run-a",
            model="kimi-k2",
            token_source="estimate",
            cost_source="pricing_estimate",
            success=0,
            error="cancelled/timeout",
        )

        stats = await repo.source_stats_for_run("run-a")

        assert stats["total_calls"] == 4
        assert stats["token_estimate_calls"] == 2
        assert stats["cost_pricing_estimate_calls"] == 2

    async def test_empty_run_returns_zeros(self, test_db: Path) -> None:
        """无 usage 行的旧 run 返回零值（分子分母均为 0），不报错."""
        repo = LlmCallUsageRepository()
        stats = await repo.source_stats_for_run("no-such-run")
        assert stats == {
            "total_calls": 0,
            "token_estimate_calls": 0,
            "cost_pricing_estimate_calls": 0,
        }
