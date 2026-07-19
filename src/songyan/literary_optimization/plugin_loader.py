from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger(__name__)

_DEFAULT_PLUGINS_DIR = files("songyan.prompts") / "literary_plugins"
PLUGINS_DIR = _DEFAULT_PLUGINS_DIR


def set_plugins_dir(path: Traversable | Path) -> None:
    """Override literary plugin directory for tests or experiments."""
    global PLUGINS_DIR
    PLUGINS_DIR = path


def reset_plugins_dir() -> None:
    """Restore packaged literary plugin directory."""
    global PLUGINS_DIR
    PLUGINS_DIR = _DEFAULT_PLUGINS_DIR


def load_strategy_plugins(
    strategy_ids: list[str],
    agent: str,
    plugins_dir: Traversable | Path | None = None,
) -> list[str]:
    """加载指定 Strategy 在某个 Agent 下的 prompt 插件片段."""
    base_dir = plugins_dir or PLUGINS_DIR
    fragments: list[str] = []
    for sid in strategy_ids:
        plugin_file = base_dir / sid / f"{agent}.yaml"
        if not plugin_file.is_file():
            logger.warning(
                "literary_plugin.missing",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        try:
            raw_data = yaml.safe_load(plugin_file.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            logger.warning(
                "literary_plugin.load_failed",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        if not isinstance(raw_data, dict):
            logger.warning(
                "literary_plugin.invalid",
                strategy_id=sid,
                agent=agent,
                path=str(plugin_file),
            )
            continue
        content = raw_data.get("content", "")
        if content:
            fragments.append(str(content))
    return fragments
