"""CreativeModeProfile 注册表 — 从 JSON 配置加载创作模式规则."""

from __future__ import annotations

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from songyan.models.creative_mode import CreativeModeProfile
from songyan.models.review import ReviewCategory
from songyan.utils.json_schema import JsonSchemaResourceError, load_schema, validate_json_data


class CreativeModeProfileError(ValueError):
    """CreativeModeProfile 加载或校验失败."""


class CreativeModeProfileNotFoundError(CreativeModeProfileError):
    """请求的 mode_id 不存在."""


# 默认从包内 creative_modes/data 加载
_DEFAULT_MODES_DIR = files("songyan.creative_modes") / "data"
_SCHEMA_PATH = _DEFAULT_MODES_DIR / "_schema.json"

# 运行时可通过 monkeypatch 覆盖
_MODES_DIR: Traversable | Path = _DEFAULT_MODES_DIR

# 内存缓存: mode_id -> CreativeModeProfile
_CACHE: dict[str, CreativeModeProfile] = {}


def set_modes_dir(path: Traversable | Path) -> None:
    """设置 creative mode 配置目录（测试用途）.

    Args:
        path: 新的 mode JSON 目录路径.
    """
    global _MODES_DIR
    _MODES_DIR = path
    clear_cache()


def _get_available_modes() -> list[str]:
    """扫描当前 mode 目录，返回可用的 mode_id 列表（字母序）."""
    if not _MODES_DIR.is_dir():
        return []
    return sorted(
        p.name.removesuffix(".json")
        for p in _MODES_DIR.iterdir()
        if p.is_file() and p.name.endswith(".json") and not p.name.startswith("_")
    )


def _validate_active_audit_dimensions(profile: CreativeModeProfile) -> None:
    """校验 active_audit_dimensions 是否全部来自 ReviewCategory."""
    valid_values = {c.value for c in ReviewCategory}
    invalid = [d for d in profile.active_audit_dimensions if d not in valid_values]
    if invalid:
        raise CreativeModeProfileError(
            f"Mode '{profile.id}' 包含无效的 active_audit_dimensions: {invalid}. "
            f"允许值: {sorted(valid_values)}"
        )


def load_creative_mode_profile(mode_id: str) -> CreativeModeProfile:
    """按 mode_id 从当前资源目录加载创作模式配置.

    Args:
        mode_id: 创作模式标识符，例如 "webnovel".

    Returns:
        校验通过的 CreativeModeProfile 实例.

    Raises:
        CreativeModeProfileNotFoundError: mode_id 不存在.
        CreativeModeProfileError: JSON 解析失败或字段校验失败.
    """
    if mode_id in _CACHE:
        return _CACHE[mode_id]

    file_path = _MODES_DIR / f"{mode_id}.json"
    if not file_path.is_file():
        available = _get_available_modes()
        msg = (
            f"CreativeMode profile '{mode_id}' not found in {_MODES_DIR}. "
            f"Available modes: {available or 'none'}"
        )
        raise CreativeModeProfileNotFoundError(msg)

    try:
        with file_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CreativeModeProfileError(
            f"Failed to parse JSON for mode '{mode_id}': {exc}"
        ) from exc

    try:
        validate_json_data(
            data,
            load_schema(_SCHEMA_PATH),
            resource_name=f"mode '{mode_id}' ({file_path.name})",
        )
    except JsonSchemaResourceError as exc:
        raise CreativeModeProfileError(
            f"Failed to validate mode '{mode_id}': {exc}"
        ) from exc

    try:
        profile = CreativeModeProfile.from_dict(data)
    except (ValueError, TypeError, KeyError) as exc:
        raise CreativeModeProfileError(
            f"Failed to validate mode '{mode_id}': {exc}"
        ) from exc

    _validate_active_audit_dimensions(profile)

    _CACHE[mode_id] = profile
    return profile


def list_creative_mode_profiles() -> list[str]:
    """列出当前资源目录下可用的模式 ID，按字母序返回."""
    return _get_available_modes()


def clear_cache() -> None:
    """清空 CreativeModeProfile 内存缓存."""
    _CACHE.clear()


class CreativeModeProfileLoader:
    """带缓存的 CreativeModeProfile 加载器."""

    @classmethod
    def load(cls, mode_id: str) -> CreativeModeProfile:
        """加载指定 mode_id 的 CreativeModeProfile."""
        return load_creative_mode_profile(mode_id)

    @classmethod
    def list_modes(cls) -> list[str]:
        """列出所有可用的 mode_id."""
        return list_creative_mode_profiles()

    @classmethod
    def clear_cache(cls) -> None:
        """清空内部缓存."""
        clear_cache()
