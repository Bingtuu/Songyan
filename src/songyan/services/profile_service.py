"""Service helpers for the ``songyan profile`` tuning CLI."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import ValidationError

from songyan.db.connection import get_db_path
from songyan.db.genre_runtime_profile_repo import (
    GenreRuntimeProfileHistoryRow,
    GenreRuntimeProfileRepository,
    load_profile_from_registry,
)
from songyan.exceptions import SongyanError
from songyan.models import GenreRuntimeProfile

ProfileSource: TypeAlias = Literal["registry", "db_override"]
ValidationLevel: TypeAlias = Literal["info", "warn", "error"]
ValidationStatus: TypeAlias = Literal["pass", "warn", "fail"]


class ProfileServiceError(SongyanError):
    """Profile CLI service error."""


@dataclass(frozen=True)
class ProfileFieldRow:
    """One flattened profile field across registry / DB / effective values."""

    field: str
    registry_value: Any
    db_override_value: Any
    db_override_present: bool
    effective_value: Any
    source: ProfileSource
    nested_replacement: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "field": self.field,
            "registry_value": self.registry_value,
            "db_override_value": self.db_override_value if self.db_override_present else None,
            "db_override_present": self.db_override_present,
            "effective_value": self.effective_value,
            "source": self.source,
            "nested_replacement": self.nested_replacement,
        }


@dataclass(frozen=True)
class ProfileView:
    """Three-column profile view for CLI rendering."""

    genre: str
    registry_genre: str
    db_available: bool
    db_error: str | None
    rows: tuple[ProfileFieldRow, ...]

    @property
    def diff_rows(self) -> tuple[ProfileFieldRow, ...]:
        """Rows where DB override changes effective values or explicitly replaces a subtree."""
        return tuple(
            row
            for row in self.rows
            if row.db_override_present or row.registry_value != row.effective_value
        )

    def to_dict(self, *, diff_only: bool = False) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        rows = self.diff_rows if diff_only else self.rows
        return {
            "genre": self.genre,
            "registry_genre": self.registry_genre,
            "db_available": self.db_available,
            "db_error": self.db_error,
            "rows": [row.to_dict() for row in rows],
        }


@dataclass(frozen=True)
class ProfileValidationIssue:
    """One profile validation issue."""

    level: ValidationLevel
    field: str
    message: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "field": self.field,
            "message": self.message,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class ProfileValidationReport:
    """Validation result for a current or pending profile."""

    genre: str
    status: ValidationStatus
    issues: tuple[ProfileValidationIssue, ...]
    target: str

    @property
    def has_errors(self) -> bool:
        return any(issue.level == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "genre": self.genre,
            "status": self.status,
            "target": self.target,
            "summary": {
                "info": sum(1 for issue in self.issues if issue.level == "info"),
                "warn": sum(1 for issue in self.issues if issue.level == "warn"),
                "error": sum(1 for issue in self.issues if issue.level == "error"),
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class ProfileMutationResult:
    """Result of a profile write or dry-run."""

    view: ProfileView
    validation: ProfileValidationReport
    history: GenreRuntimeProfileHistoryRow | None
    dry_run: bool

    def to_dict(self, *, diff_only: bool = True) -> dict[str, Any]:
        data = self.view.to_dict(diff_only=diff_only)
        data["validation"] = self.validation.to_dict()
        data["history"] = self.history.to_dict() if self.history else None
        data["dry_run"] = self.dry_run
        return data


def parse_set_expression(expr: str) -> tuple[str, Any]:
    """Parse a ``key=value`` CLI override expression."""
    if "=" not in expr:
        msg = f"invalid --set expression, expected key=value: {expr}"
        raise ProfileServiceError(msg)
    key, raw_value = expr.split("=", 1)
    key = key.strip()
    if not key:
        msg = f"invalid --set expression, empty key: {expr}"
        raise ProfileServiceError(msg)
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value
    return key, value


def merge_override_inputs(
    json_overrides: Mapping[str, Any] | None,
    set_items: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Merge JSON and CLI override inputs, rejecting ambiguous duplicate fields."""
    merged: dict[str, Any] = dict(json_overrides or {})
    paths = set(_flatten_override_paths(merged))
    for path, value in set_items:
        if _has_path_conflict(path, paths):
            msg = f"duplicate override field: {path}"
            raise ProfileServiceError(msg)
        _assign_partial_path(merged, path, value)
        paths.add(path)
    return merged


def load_override_json(path: Path) -> dict[str, Any]:
    """Load a JSON object containing override intent."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"failed to read override JSON: {path}"
        raise ProfileServiceError(msg) from exc
    if not isinstance(raw, dict):
        msg = "--from-json must contain a JSON object"
        raise ProfileServiceError(msg)
    return raw


def build_db_override_profile(
    genre: str,
    overrides: Mapping[str, Any],
    *,
    reset: bool = False,
) -> GenreRuntimeProfile:
    """Build a DB profile row from code defaults plus explicit override intent."""
    key = _normalize_genre(genre)
    _require_known_registry_genre(key)
    data = GenreRuntimeProfile(genre=key).model_dump(mode="json")
    if not reset:
        for field, value in overrides.items():
            _assign_model_path(data, field, value)
    try:
        return GenreRuntimeProfile.model_validate(data)
    except ValidationError as exc:
        msg = f"invalid profile override for genre={key}: {exc}"
        raise ProfileServiceError(msg) from exc


async def get_profile_view(genre: str) -> ProfileView:
    """Build a registry / DB override / effective profile view without mutating DB."""
    key = _normalize_genre(genre)
    registry = load_profile_from_registry(key)
    db_profile, db_error = _read_db_profile_if_available(key)
    effective = merge_effective_profile(registry, db_profile)
    return build_profile_view(
        genre=key,
        registry=registry,
        db_profile=db_profile,
        effective=effective,
        db_available=db_error is None,
        db_error=db_error,
    )


async def validate_profile_overrides(
    genre: str,
    overrides: Mapping[str, Any] | None = None,
    *,
    reset: bool = False,
) -> ProfileValidationReport:
    """Validate current or pending profile overrides without mutating DB."""
    key = _normalize_genre(genre)
    _require_known_registry_genre(key)
    registry = load_profile_from_registry(key)
    if overrides is None and not reset:
        db_profile, db_error = _read_db_profile_if_available(key)
        target = "effective"
        if db_error:
            issue = _issue(
                "error",
                "db_override",
                f"stored DB override is unreadable: {db_error}",
                (
                    "请使用 profile history / rollback 恢复到已知安全状态，"
                    "或修复 DB 中的 profile_json。"
                ),
            )
            return _build_validation_report(key, [issue], target=target)
    else:
        target = "pending"
        try:
            db_profile = build_db_override_profile(key, overrides or {}, reset=reset)
        except ProfileServiceError as exc:
            issue = _issue(
                "error",
                "profile_override",
                str(exc),
                "请修正 override 字段名、类型或 Pydantic 约束后重新运行 validate。",
            )
            return _build_validation_report(key, [issue], target=target)
    effective = merge_effective_profile(registry, db_profile)
    db_diff = explicit_override_diff(db_profile) if db_profile is not None else {}
    issues = _validate_effective_profile(effective)
    issues.extend(_validate_override_shape(db_diff))
    return _build_validation_report(key, issues, target=target)


async def upsert_profile_overrides(
    genre: str,
    overrides: Mapping[str, Any],
    *,
    reset: bool = False,
    dry_run: bool = False,
) -> ProfileMutationResult:
    """Write DB override intent and return the resulting profile view."""
    profile = build_db_override_profile(genre, overrides, reset=reset)
    validation = await validate_profile_overrides(
        profile.genre,
        overrides,
        reset=reset,
    )
    if validation.has_errors:
        msg = "profile validation failed: " + "; ".join(
            f"{issue.field}: {issue.message}"
            for issue in validation.issues
            if issue.level == "error"
        )
        raise ProfileServiceError(msg)

    repo = GenreRuntimeProfileRepository()
    history = None
    if not dry_run:
        history = await repo.upsert_with_history(
            profile,
            action="reset" if reset else "upsert",
            diff=explicit_override_diff(profile),
            validation=validation.to_dict(),
        )
    view = (
        await get_profile_view(profile.genre)
        if not dry_run
        else _dry_run_view(profile.genre, profile)
    )
    return ProfileMutationResult(
        view=view,
        validation=validation,
        history=history,
        dry_run=dry_run,
    )


async def list_profile_history(
    genre: str,
    *,
    limit: int = 20,
) -> list[GenreRuntimeProfileHistoryRow]:
    """List recent profile history rows."""
    key = _normalize_genre(genre)
    _require_known_registry_genre(key)
    return await GenreRuntimeProfileRepository().list_history(key, limit=limit)


async def rollback_profile_override(
    genre: str,
    history_id: str,
) -> ProfileMutationResult:
    """Rollback a profile override to the state before a history row."""
    key = _normalize_genre(genre)
    _require_known_registry_genre(key)
    repo = GenreRuntimeProfileRepository()
    target = await repo.get_history(history_id)
    if target is None or target.genre != key:
        msg = f"profile history not found for genre={key}: {history_id}"
        raise ProfileServiceError(msg)

    rollback_profile = target.before_profile or GenreRuntimeProfile(genre=key)
    validation = await validate_profile_overrides(
        key,
        explicit_override_diff(rollback_profile),
    )
    if validation.has_errors:
        msg = "rollback target failed profile validation"
        raise ProfileServiceError(msg)

    history = await repo.upsert_with_history(
        rollback_profile,
        action=f"rollback:{history_id}",
        diff=explicit_override_diff(rollback_profile),
        validation=validation.to_dict(),
    )
    view = await get_profile_view(key)
    return ProfileMutationResult(
        view=view,
        validation=validation,
        history=history,
        dry_run=False,
    )


def merge_effective_profile(
    registry: GenreRuntimeProfile,
    db_profile: GenreRuntimeProfile | None,
) -> GenreRuntimeProfile:
    """Merge DB explicit diff over registry baseline using load_profile semantics."""
    if db_profile is None:
        return registry.model_copy(deep=True)
    base_data = registry.model_dump(mode="json")
    diff = explicit_override_diff(db_profile)
    merged = {**base_data, **diff}
    return GenreRuntimeProfile.model_validate(merged)


def explicit_override_diff(profile: GenreRuntimeProfile) -> dict[str, Any]:
    """Return top-level fields explicitly represented by a DB profile row."""
    default = GenreRuntimeProfile(genre=profile.genre).model_dump(mode="json")
    data = profile.model_dump(mode="json")
    return {
        field: value
        for field, value in data.items()
        if field != "genre" and value != default.get(field)
    }


def build_profile_view(
    *,
    genre: str,
    registry: GenreRuntimeProfile,
    db_profile: GenreRuntimeProfile | None,
    effective: GenreRuntimeProfile,
    db_available: bool,
    db_error: str | None,
) -> ProfileView:
    """Create rows for registry / DB / effective display."""
    registry_flat = flatten_profile(registry)
    effective_flat = flatten_profile(effective)
    db_diff = explicit_override_diff(db_profile) if db_profile is not None else {}
    db_flat = flatten_mapping(db_diff)

    fields = tuple(sorted(set(registry_flat) | set(effective_flat) | set(db_flat)))
    rows = []
    for field in fields:
        top = field.split(".", 1)[0]
        override_present = top in db_diff
        nested_replacement = override_present and isinstance(db_diff.get(top), dict)
        rows.append(
            ProfileFieldRow(
                field=field,
                registry_value=registry_flat.get(field),
                db_override_value=db_flat.get(field),
                db_override_present=override_present and field in db_flat,
                effective_value=effective_flat.get(field),
                source="db_override" if override_present else "registry",
                nested_replacement=nested_replacement,
            )
        )
    return ProfileView(
        genre=genre,
        registry_genre=registry.genre,
        db_available=db_available,
        db_error=db_error,
        rows=tuple(rows),
    )


def flatten_profile(profile: GenreRuntimeProfile) -> dict[str, Any]:
    """Flatten a profile model into dot-path fields."""
    return flatten_mapping(profile.model_dump(mode="json"))


def flatten_mapping(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested mapping into dot-path keys."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten_mapping(value, path))
        else:
            out[path] = value
    return out


def render_profile_view(view: ProfileView, *, diff_only: bool = False) -> str:
    """Render a human-readable profile table."""
    rows = view.diff_rows if diff_only else view.rows
    if diff_only and not rows:
        return f"profile {view.genre}: no DB override; effective == registry"

    lines = [
        f"profile {view.genre}",
        f"registry_genre: {view.registry_genre}",
    ]
    if view.db_error:
        lines.append(f"db_override: unavailable ({view.db_error})")
    header = f"{'field':<42} {'registry':<24} {'db_override':<24} {'effective':<24} source"
    lines.extend([header, "-" * len(header)])
    for row in rows:
        suffix = " (nested replacement)" if row.nested_replacement else ""
        lines.append(
            f"{row.field:<42} {_render_value(row.registry_value):<24} "
            f"{_render_value(row.db_override_value) if row.db_override_present else '-':<24} "
            f"{_render_value(row.effective_value):<24} {row.source}{suffix}"
        )
    return "\n".join(lines)


def render_profile_validation(report: ProfileValidationReport) -> str:
    """Render profile validation result."""
    lines = [
        f"profile validation: {report.genre}",
        f"target: {report.target}",
        f"status: {report.status}",
    ]
    if not report.issues:
        lines.append("issues: none")
        return "\n".join(lines)
    lines.append("issues:")
    for issue in report.issues:
        lines.append(f"- [{issue.level}] {issue.field}: {issue.message}")
        lines.append(f"  recommendation: {issue.recommendation}")
    return "\n".join(lines)


def render_profile_history(rows: list[GenreRuntimeProfileHistoryRow]) -> str:
    """Render profile history rows."""
    if not rows:
        return "profile history: no entries"
    lines = [
        f"{'history_id':<16} {'genre':<10} {'action':<18} {'created_at'}",
        "-" * 72,
    ]
    for row in rows:
        lines.append(
            f"{row.history_id:<16} {row.genre:<10} {row.action:<18} {row.created_at}"
        )
    return "\n".join(lines)


def _dry_run_view(genre: str, db_profile: GenreRuntimeProfile) -> ProfileView:
    registry = load_profile_from_registry(genre)
    effective = merge_effective_profile(registry, db_profile)
    return build_profile_view(
        genre=genre,
        registry=registry,
        db_profile=db_profile,
        effective=effective,
        db_available=True,
        db_error=None,
    )


def _build_validation_report(
    genre: str,
    issues: list[ProfileValidationIssue],
    *,
    target: str,
) -> ProfileValidationReport:
    status: ValidationStatus
    if any(issue.level == "error" for issue in issues):
        status = "fail"
    elif any(issue.level == "warn" for issue in issues):
        status = "warn"
    else:
        status = "pass"
    return ProfileValidationReport(
        genre=genre,
        status=status,
        issues=tuple(issues),
        target=target,
    )


def _issue(
    level: ValidationLevel,
    field: str,
    message: str,
    recommendation: str,
) -> ProfileValidationIssue:
    return ProfileValidationIssue(
        level=level,
        field=field,
        message=message,
        recommendation=recommendation,
    )


def _validate_effective_profile(profile: GenreRuntimeProfile) -> list[ProfileValidationIssue]:
    """Validate an effective profile against V11 safety recommendations."""
    issues: list[ProfileValidationIssue] = []
    issues.extend(_validate_finite_profile_values(profile))

    if profile.base_budget < 6000:
        issues.append(
            _issue(
                "warn",
                "base_budget",
                f"base_budget is low: {profile.base_budget}",
                "建议保持 >= 8000；低预算更容易触发 ContextEmergency。",
            )
        )
    if profile.base_budget > 50000:
        issues.append(
            _issue(
                "warn",
                "base_budget",
                f"base_budget is unusually high: {profile.base_budget}",
                "建议先用短窗口验证成本与上下文压力，不要直接长跑。",
            )
        )
    if profile.ramp_per_chapter > 1000:
        issues.append(
            _issue(
                "warn",
                "ramp_per_chapter",
                f"ramp_per_chapter is high: {profile.ramp_per_chapter}",
                "建议保持 <= 1000；过高会快速放大上下文和成本。",
            )
        )
    if profile.min_budget > profile.base_budget:
        issues.append(
            _issue(
                "error",
                "min_budget",
                f"min_budget ({profile.min_budget}) > base_budget ({profile.base_budget})",
                "请让 min_budget <= base_budget。",
            )
        )

    issues.extend(_validate_ratio_map("partition_ratios", profile.partition_ratios))

    for field, limit_value, recommended_min in (
        ("max_soft_refs", profile.max_soft_refs, 2),
        ("max_foreshadowing", profile.max_foreshadowing, 2),
        ("max_character_states", profile.max_character_states, 2),
        ("max_setting_input", profile.max_setting_input, 2),
    ):
        if limit_value < recommended_min:
            issues.append(
                _issue(
                    "warn",
                    field,
                    f"{field} is very low: {limit_value}",
                    "过低可能让上下文事实不足；建议先用短窗口验证。",
                )
            )

    for field, ratio_value in (
        ("hard_enforce_ratio", profile.hard_enforce_ratio),
        ("emergency_halt_ratio", profile.emergency_halt_ratio),
    ):
        if ratio_value < 1.05:
            issues.append(
                _issue(
                    "warn",
                    field,
                    f"{field} is close to 1.0: {ratio_value}",
                    "过低会让预算波动更容易触发裁剪或 halt。",
                )
            )
        if ratio_value > 2.0:
            issues.append(
                _issue(
                    "warn",
                    field,
                    f"{field} is high: {ratio_value}",
                    "过高会削弱预算异常保护；建议先用短窗口验证。",
                )
            )

    if profile.context_emergency_trigger_ratio < 0.8:
        issues.append(
            _issue(
                "warn",
                "context_emergency_trigger_ratio",
                (
                    "context_emergency_trigger_ratio is low: "
                    f"{profile.context_emergency_trigger_ratio}"
                ),
                "过低会让正常预算波动频繁进入 emergency。",
            )
        )

    cd = profile.character_decay
    if cd.archive_window <= cd.dormant_window:
        issues.append(
            _issue(
                "error",
                "character_decay.archive_window",
                "archive_window must be greater than dormant_window",
                "请保持 archive_window > dormant_window。",
            )
        )
    if cd.functional_window > cd.dormant_window:
        issues.append(
            _issue(
                "warn",
                "character_decay.functional_window",
                "functional_window is greater than dormant_window",
                "功能性角色窗口通常应不大于 dormant_window。",
            )
        )

    continuity = profile.continuity
    if continuity.forgotten_threshold < 2:
        issues.append(
            _issue(
                "warn",
                "continuity.forgotten_threshold",
                f"forgotten_threshold is low: {continuity.forgotten_threshold}",
                "过低会增加 continuity 噪声，建议先短窗口验证。",
            )
        )
    if continuity.state_mismatch_window < 1:
        issues.append(
            _issue(
                "error",
                "continuity.state_mismatch_window",
                "state_mismatch_window must be >= 1",
                "请设置为正整数。",
            )
        )
    if continuity.health_overdue_weight > 1.0:
        issues.append(
            _issue(
                "error",
                "continuity.health_overdue_weight",
                f"health_overdue_weight is too high: {continuity.health_overdue_weight}",
                "请保持 <= 1.0；过高会放大 overdue 对 health 的影响。",
            )
        )
    elif continuity.health_overdue_weight > 0.5:
        issues.append(
            _issue(
                "warn",
                "continuity.health_overdue_weight",
                f"health_overdue_weight is high: {continuity.health_overdue_weight}",
                "建议保持 <= 0.5，或提供短窗口证据。",
            )
        )

    return issues


def _validate_ratio_map(
    field: str,
    values: Mapping[str, float],
) -> list[ProfileValidationIssue]:
    issues: list[ProfileValidationIssue] = []
    total = 0.0
    for key, value in values.items():
        item_field = f"{field}.{key}"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            issues.append(
                _issue(
                    "error",
                    item_field,
                    f"{item_field} is not numeric: {value}",
                    "请设置为 0 到 1 之间的小数。",
                )
            )
            continue
        total += numeric
        if not math.isfinite(numeric):
            issues.append(
                _issue(
                    "error",
                    item_field,
                    f"{item_field} must be finite: {value}",
                    "请设置为有限数值，不能使用 NaN 或 Infinity。",
                )
            )
            continue
        if numeric < 0:
            issues.append(
                _issue(
                    "error",
                    item_field,
                    f"{item_field} must be non-negative: {numeric}",
                    "请设置为 0 到 1 之间的小数。",
                )
            )
        if numeric > 0.6:
            issues.append(
                _issue(
                    "warn",
                    item_field,
                    f"{item_field} is high: {numeric}",
                    "单个可裁分区比例过高可能挤压其他事实源。",
                )
            )
    if total > 0.95:
        issues.append(
            _issue(
                "warn",
                field,
                f"{field} sum is high: {total:.2f}",
                "建议总和 <= 0.95，避免可裁分区互相挤压。",
            )
        )
    return issues


def _validate_finite_profile_values(
    profile: GenreRuntimeProfile,
) -> list[ProfileValidationIssue]:
    issues: list[ProfileValidationIssue] = []
    for field, value in flatten_profile(profile).items():
        if isinstance(value, float) and not math.isfinite(value):
            issues.append(
                _issue(
                    "error",
                    field,
                    f"{field} must be finite: {value}",
                    "请设置为有限数值，不能使用 NaN 或 Infinity。",
                )
            )
    return issues


def _validate_override_shape(db_diff: Mapping[str, Any]) -> list[ProfileValidationIssue]:
    """Validate risks introduced by override shape, especially nested replacement."""
    issues: list[ProfileValidationIssue] = []
    nested_fields = {
        "setting_evaporation",
        "foreshadowing_evaporation",
        "character_decay",
        "continuity",
    }
    for field, value in db_diff.items():
        if field in nested_fields and isinstance(value, dict):
            issues.append(
                _issue(
                    "warn",
                    field,
                    f"{field} override replaces the whole nested profile",
                    "确认该子模型所有字段都符合预期；当前加载语义不是字段级深合并。",
                )
            )
    return issues


def _normalize_genre(genre: str) -> str:
    key = genre.strip().lower()
    if not key:
        msg = "genre must not be empty"
        raise ProfileServiceError(msg)
    return key


def _require_known_registry_genre(genre: str) -> None:
    registry = load_profile_from_registry(genre)
    if registry.genre != genre:
        msg = (
            f"unknown genre for profile upsert: {genre}; "
            "DB overrides for unknown genres cannot load under current fallback semantics"
        )
        raise ProfileServiceError(msg)


def _read_db_profile_if_available(
    genre: str,
) -> tuple[GenreRuntimeProfile | None, str | None]:
    try:
        db_path = get_db_path().resolve()
    except Exception as exc:  # noqa: BLE001 - rendered as unavailable DB override
        return None, str(exc)
    if not db_path.is_file():
        return None, None
    uri = f"{db_path.as_uri()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='genre_runtime_profiles' LIMIT 1"
            )
            if cursor.fetchone() is None:
                return None, None
            cursor = conn.execute(
                "SELECT profile_json FROM genre_runtime_profiles WHERE genre = ?",
                (genre,),
            )
            row = cursor.fetchone()
    except sqlite3.Error as exc:
        return None, str(exc)
    if row is None or not row[0]:
        return None, None
    try:
        raw = json.loads(str(row[0]))
        return GenreRuntimeProfile.model_validate(raw), None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, str(exc)


def _assign_model_path(data: dict[str, Any], path: str, value: Any) -> None:
    _assign_model_parts(data, path.split("."), value, path)


def _assign_model_parts(
    current: dict[str, Any],
    parts: list[str],
    value: Any,
    original_path: str,
) -> None:
    key = parts[0]
    if key not in current:
        msg = f"unknown profile field: {original_path}"
        raise ProfileServiceError(msg)
    if len(parts) > 1:
        child = current[key]
        if not isinstance(child, dict):
            msg = f"profile field is not nested: {original_path}"
            raise ProfileServiceError(msg)
        _assign_model_parts(child, parts[1:], value, original_path)
        return

    existing = current[key]
    if isinstance(value, dict) and isinstance(existing, dict):
        for child_key, child_value in value.items():
            child_path = f"{original_path}.{child_key}"
            _assign_model_parts(existing, [str(child_key)], child_value, child_path)
    else:
        current[key] = value


def _assign_partial_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            existing = {}
            current[part] = existing
        if not isinstance(existing, dict):
            msg = f"override path conflicts with scalar field: {path}"
            raise ProfileServiceError(msg)
        current = existing
    current[parts[-1]] = value


def _flatten_override_paths(data: Mapping[str, Any], prefix: str = "") -> list[str]:
    out: list[str] = []
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.extend(_flatten_override_paths(value, path))
        else:
            out.append(path)
    return out


def _has_path_conflict(path: str, existing_paths: set[str]) -> bool:
    return any(
        existing == path
        or existing.startswith(f"{path}.")
        or path.startswith(f"{existing}.")
        for existing in existing_paths
    )


def _render_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)
