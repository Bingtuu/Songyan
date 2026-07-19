"""Genre Profile 加载器 — 从 JSON 配置加载题材规则."""

from __future__ import annotations

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from songyan.models.genre import GenreProfile
from songyan.models.review import ReviewCategory


class GenreProfileError(ValueError):
    """Genre Profile 加载或校验失败."""


class GenreProfileNotFoundError(GenreProfileError):
    """请求的 genre_id 不存在."""


# 默认从包内 genres/data 加载
_DEFAULT_GENRES_DIR = files("songyan.genres") / "data"

# 运行时可通过 monkeypatch 覆盖
_GENRES_DIR: Traversable | Path = _DEFAULT_GENRES_DIR

# 内存缓存: genre_id -> GenreProfile
_CACHE: dict[str, GenreProfile] = {}


def set_genres_dir(path: Traversable | Path) -> None:
    """设置 genre 配置目录（测试用途）.

    Args:
        path: 新的 genre JSON 目录路径.
    """
    global _GENRES_DIR
    _GENRES_DIR = path
    clear_cache()


def _get_available_genres() -> list[str]:
    """扫描当前 genre 目录，返回可用的 genre_id 列表（字母序）."""
    if not _GENRES_DIR.is_dir():
        return []
    return sorted(
        p.name.removesuffix(".json")
        for p in _GENRES_DIR.iterdir()
        if p.is_file() and p.name.endswith(".json")
    )


def _validate_active_audit_dimensions(profile: GenreProfile) -> None:
    """校验 active_audit_dimensions 是否全部来自 ReviewCategory."""
    valid_values = {c.value for c in ReviewCategory}
    invalid = [d for d in profile.active_audit_dimensions if d not in valid_values]
    if invalid:
        raise GenreProfileError(
            f"Genre '{profile.id}' 包含无效的 active_audit_dimensions: {invalid}. "
            f"允许值: {sorted(valid_values)}"
        )


def load_genre_profile(genre_id: str) -> GenreProfile:
    """按 genre_id 从当前资源目录加载题材配置.

    Args:
        genre_id: 题材标识符，例如 "xuanhuan".

    Returns:
        校验通过的 GenreProfile 实例.

    Raises:
        GenreProfileNotFoundError: genre_id 不存在.
        GenreProfileError: JSON 解析失败或字段校验失败.
    """
    if genre_id in _CACHE:
        return _CACHE[genre_id]

    file_path = _GENRES_DIR / f"{genre_id}.json"
    if not file_path.is_file():
        available = _get_available_genres()
        msg = (
            f"Genre profile '{genre_id}' not found in {_GENRES_DIR}. "
            f"Available genres: {available or 'none'}"
        )
        raise GenreProfileNotFoundError(msg)

    try:
        with file_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise GenreProfileError(
            f"Failed to parse JSON for genre '{genre_id}': {exc}"
        ) from exc

    try:
        profile = GenreProfile.from_dict(data)
    except (ValueError, TypeError, KeyError) as exc:
        raise GenreProfileError(
            f"Failed to validate genre '{genre_id}': {exc}"
        ) from exc

    _validate_active_audit_dimensions(profile)

    _CACHE[genre_id] = profile
    return profile


def list_genre_profiles() -> list[str]:
    """列出当前资源目录下可用的题材 ID，按字母序返回."""
    return _get_available_genres()


def clear_cache() -> None:
    """清空 GenreProfile 内存缓存."""
    _CACHE.clear()
