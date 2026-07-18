"""Repository for LLM call usage telemetry (V9 Task 175)."""

from __future__ import annotations

from sqlite3 import Row
from typing import TYPE_CHECKING, Any, Literal

import structlog

from songyan.db.connection import get_db

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)

TokenSource = Literal["response", "estimate"]
CostSource = Literal["provider_cost", "pricing_estimate"]


class LlmCallUsageRepository:
    """读写 llm_call_usage 表：单次 LLM 调用的 token / 成本遥测.

    record 失败只 warning 不抛异常——telemetry 丢失可接受，生成不可断。
    """

    async def record(
        self,
        *,
        model: str,
        token_source: TokenSource,
        cost_source: CostSource,
        run_id: str | None = None,
        project_id: str | None = None,
        chapter_number: int | None = None,
        agent: str = "unknown",
        stage: str | None = None,
        version_id: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_cny: float = 0.0,
        cached_tokens: int | None = None,
        cache_miss_tokens: int | None = None,
        latency_ms: int = 0,
        retry_attempt: int = 0,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """写入一行调用记录。任何异常都只记 warning，不向外抛."""
        try:
            async with get_db() as conn:
                await conn.execute(
                    """INSERT INTO llm_call_usage (
                        run_id, project_id, chapter_number, agent, stage,
                        version_id, model, prompt_tokens, completion_tokens,
                        cost_cny, token_source, cost_source,
                        cached_tokens, cache_miss_tokens,
                        latency_ms, retry_attempt, success, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        project_id,
                        chapter_number,
                        agent,
                        stage,
                        version_id,
                        model,
                        prompt_tokens,
                        completion_tokens,
                        cost_cny,
                        token_source,
                        cost_source,
                        cached_tokens,
                        cache_miss_tokens,
                        latency_ms,
                        retry_attempt,
                        int(success),
                        error,
                    ),
                )
                await conn.commit()
        except Exception as exc:  # telemetry 丢失可接受，生成不可断（任务书明确要求全捕获）
            logger.warning(
                "llm_call_usage.record_failed",
                error=str(exc),
                run_id=run_id,
                model=model,
            )

    async def sum_cost_for_run(self, run_id: str) -> float:
        """该 run 的 cost_cny 合计；无记录返回 0.0."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(cost_cny), 0.0) FROM llm_call_usage "
                "WHERE run_id = ?",
                (run_id,),
            )
            row = await cursor.fetchone()
            return float(row[0]) if row else 0.0

    async def aggregate_for_run(self, run_id: str) -> dict[str, list[dict[str, Any]]]:
        """按 chapter_number / agent 分组聚合（供 report 成本视图）.

        Returns:
            {"per_chapter": [...], "per_agent": [...]}，每项含
            chapter_number/agent、call_count、prompt_tokens、completion_tokens、
            cost_cny 合计。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            per_chapter = await self._group_by(conn, run_id, "chapter_number")
            per_agent = await self._group_by(conn, run_id, "agent")
        return {"per_chapter": per_chapter, "per_agent": per_agent}

    async def _group_by(
        self,
        conn: aiosqlite.Connection,
        run_id: str,
        column: Literal["chapter_number", "agent"],
    ) -> list[dict[str, Any]]:
        cursor = await conn.execute(
            f"""SELECT {column}, COUNT(*) AS call_count,
                       SUM(prompt_tokens) AS prompt_tokens,
                       SUM(completion_tokens) AS completion_tokens,
                       SUM(cost_cny) AS cost_cny
                FROM llm_call_usage
                WHERE run_id = ?
                GROUP BY {column}
                ORDER BY {column}""",
            (run_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
