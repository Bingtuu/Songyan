from __future__ import annotations

from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger(__name__)

PLUGINS_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "literary_plugins"


def load_strategy_plugins(strategy_ids: list[str], agent: str) -> list[str]:
    """加载指定 Strategy 在某个 Agent 下的 prompt 插件片段."""
    fragments: list[str] = []
    for sid in strategy_ids:
        plugin_file = PLUGINS_DIR / sid / f"{agent}.yaml"
        if not plugin_file.exists():
            logger.warning(
                "literary_plugin.missing",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        try:
            data = yaml.safe_load(plugin_file.read_text(encoding="utf-8")) or {}
        except Exception:
            logger.warning(
                "literary_plugin.load_failed",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        content = data.get("content", "")
        if content:
            fragments.append(str(content))
    return fragments
