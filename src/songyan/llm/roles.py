"""LLM 路由角色清单（V14 Task 231）.

角色名与遥测归因（``bind_contextvars(agent=...)``）使用的名字一致，
因此 per-role 路由生效后可直接在 ``llm_call_usage`` 的 ``agent``/``model``
字段上验证（V14 验收矩阵 B）。

本模块不 import 任何 songyan 模块，config.py 与 client.py 均可安全引用。
"""

from __future__ import annotations

#: 可路由角色清单（10 个）。rule_auditor / continuity_auditor 为纯代码检测不调 LLM，
#: embedding 走本地模型，均不在清单内。
LLM_ROLE_NAMES: frozenset[str] = frozenset(
    {
        "writer",
        "revision_handler",
        "llm_auditor",
        "literary_auditor",
        "settlement_extractor",
        "summary_writer",
        "goal_planner",
        "creative_director",
        "arc_summary_generator",
        "volume_summary_generator",
    }
)

#: per-role 可覆盖字段（环境变量后缀）。temperature 等调用参数保持调用点签名控制。
LLM_ROLE_OVERRIDE_FIELDS: frozenset[str] = frozenset({"MODEL", "BASE_URL", "API_KEY"})
