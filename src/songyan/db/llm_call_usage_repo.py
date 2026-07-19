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

# _group_by 的运行时列名白名单（Literal 类型守卫之外的运行时守卫，
# 防止 f-string SQL 拼接被非白名单列名注入）
_GROUP_BY_COLUMNS: dict[str, str] = {
    "chapter_number": "chapter_number",
    "agent": "agent",
}


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

        per_chapter 的 NULL 分组语义：chapter_number 可空，run 级调用（未绑定
        章节）会聚成一章 chapter_number=None 的分组，且在 ORDER BY 下排最前；
        report 层可自行把 None 映射为「run 级」标签展示。

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
        group_column = _GROUP_BY_COLUMNS[column]
        cursor = await conn.execute(
            f"""SELECT {group_column}, COUNT(*) AS call_count,
                       SUM(prompt_tokens) AS prompt_tokens,
                       SUM(completion_tokens) AS completion_tokens,
                       SUM(cost_cny) AS cost_cny
                FROM llm_call_usage
                WHERE run_id = ?
                GROUP BY {group_column}
                ORDER BY {group_column}""",
            (run_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def source_stats_for_run(self, run_id: str) -> dict[str, int]:
        """token_source / cost_source 分布计数（report 成本段的估算占比分子分母）.

        只统计 `success = 1` 的调用：失败/取消尝试以默认 estimate 标记落库，
        计入会把"瞬态失败率"误读成"usage 提取失败率"（阶段 D 判据 estimate
        占比 <20% 的口径）。

        Returns:
            {"total_usage_rows": 全部尝试行数（含失败/取消）,
             "total_calls": 成功调用行数（分母）,
             "token_estimate_calls": token_source='estimate' 行数（分子）,
             "cost_pricing_estimate_calls": cost_source='pricing_estimate' 行数（分子）}
            无记录的 run 四个值全为 0，不报错（旧 run 无 usage 数据的常态路径）。
        """
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT COUNT(*) AS total_usage_rows,
                          COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0)
                              AS total_calls,
                          COALESCE(
                              SUM(
                                  CASE
                                      WHEN success = 1 AND token_source = 'estimate'
                                      THEN 1 ELSE 0
                                  END
                              ),
                              0
                          ) AS token_estimate_calls,
                          COALESCE(
                              SUM(
                                  CASE
                                      WHEN success = 1 AND cost_source = 'pricing_estimate'
                                      THEN 1 ELSE 0
                                  END
                              ),
                              0
                          ) AS cost_pricing_estimate_calls
                   FROM llm_call_usage
                   WHERE run_id = ?""",
                (run_id,),
            )
            row = await cursor.fetchone()
        # 聚合查询无 GROUP BY 必返回一行；row 为 None 只是防御性兜底
        if row is None:
            return {
                "total_usage_rows": 0,
                "total_calls": 0,
                "token_estimate_calls": 0,
                "cost_pricing_estimate_calls": 0,
            }
        return {
            "total_usage_rows": int(row[0]),
            "total_calls": int(row[1]),
            "token_estimate_calls": int(row[2]),
            "cost_pricing_estimate_calls": int(row[3]),
        }
