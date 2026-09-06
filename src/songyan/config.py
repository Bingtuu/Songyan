"""Pydantic Settings 配置管理."""

import os
import re
from collections.abc import Mapping

from dotenv import dotenv_values
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class RoleLlmOverride(BaseModel):
    """单个路由角色的 LLM 覆盖配置（V14 Task 231）.

    三个字段均可选；未设置的字段在解析时回落到全局默认。
    """

    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


_LLM_ROLE_OVERRIDE_PATTERN = re.compile(r"^LLM_(.+)_(MODEL|BASE_URL|API_KEY)$")


def collect_llm_role_overrides(
    *sources: Mapping[str, str | None],
) -> dict[str, RoleLlmOverride]:
    """从配置源收集 ``LLM_<ROLE>_{MODEL,BASE_URL,API_KEY}`` 覆盖项.

    靠前的 source 优先级更高（先传 os.environ 再传 .env）；角色名小写归一。
    不校验角色合法性——未知角色由 doctor / preflight 提示，配置加载期不 fail。
    """
    collected: dict[str, dict[str, str]] = {}
    for source in reversed(sources):  # 低优先级先写，高优先级后写覆盖
        for key, value in source.items():
            if not value:
                continue
            match = _LLM_ROLE_OVERRIDE_PATTERN.match(key)
            if match is None:
                continue
            role = match.group(1).lower()
            field_name = match.group(2).lower()
            collected.setdefault(role, {})[field_name] = value
    return {role: RoleLlmOverride(**fields) for role, fields in collected.items()}


class Settings(BaseSettings):
    """Songyan 全局配置，从 .env 文件加载."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # LLM 配置
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_retries: int = 3
    llm_rate_limit_max_wait: float = 60.0
    llm_run_call_budget: int = 0  # 0 = 不启用单 run 调用预算
    # 0 = 不启用单 run 成本预算（CNY）；启用后超预算立即熔断暂停 run，可 --resume 续跑
    run_cost_budget: float = Field(
        default=0.0,
        validation_alias=AliasChoices("SONGYAN_RUN_COST_BUDGET", "RUN_COST_BUDGET"),
    )

    # V14 Task 231: per-role LLM 覆盖（LLM_<ROLE>_{MODEL,BASE_URL,API_KEY}），
    # 由 _collect_llm_role_overrides 从 env/.env 收集，非 env 直接映射
    llm_role_overrides: dict[str, RoleLlmOverride] = Field(default_factory=dict)

    # Token 预算
    context_total_budget: int = 32_000
    context_generation_reserve: int = 8_000

    # 日志
    log_level: str = "INFO"
    log_file_level: str = "DEBUG"
    force_exit_after_run: bool = Field(
        default=False,
        validation_alias=AliasChoices("SONGYAN_FORCE_EXIT", "FORCE_EXIT_AFTER_RUN"),
    )

    # 数据库
    database_url: str = "sqlite:///songyan.db"

    # Checkpointer 模式（测试/Windows 验证环境建议用 "memory"）
    checkpointer_mode: str = "sqlite"

    @field_validator("run_cost_budget", mode="before")
    @classmethod
    def _coerce_run_cost_budget(cls, value: object) -> float:
        if value in (None, ""):
            return 0.0
        if not isinstance(value, str | int | float):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @model_validator(mode="after")
    def _collect_llm_role_overrides(self) -> "Settings":
        """收集 per-role LLM 覆盖（env 优先于 .env）；不在加载期校验合法性."""
        env_file = self.model_config.get("env_file", ".env")
        dotenv_map = dotenv_values(env_file) if env_file else {}
        self.llm_role_overrides = collect_llm_role_overrides(os.environ, dotenv_map)
        return self


_SETTINGS_LOAD_ERROR: ValidationError | None = None


def _default_settings() -> Settings:
    """Build a validated default settings object without relying on env values."""
    return Settings(
        llm_api_key="",
        llm_base_url="https://api.deepseek.com",
        llm_model="deepseek-chat",
        llm_temperature=0.7,
        llm_max_retries=3,
        llm_rate_limit_max_wait=60.0,
        llm_run_call_budget=0,
        run_cost_budget=0.0,
        context_total_budget=32_000,
        context_generation_reserve=8_000,
        log_level="INFO",
        log_file_level="DEBUG",
        force_exit_after_run=False,
        database_url="sqlite:///songyan.db",
        checkpointer_mode="sqlite",
    )


def load_settings_safely() -> Settings:
    """Load settings for module-level runtime use without import-time traceback."""
    global _SETTINGS_LOAD_ERROR
    try:
        _SETTINGS_LOAD_ERROR = None
        return Settings()
    except ValidationError as exc:
        _SETTINGS_LOAD_ERROR = exc
        return _default_settings()


def get_settings_load_error() -> ValidationError | None:
    """Return the latest module-level settings load error, if any."""
    return _SETTINGS_LOAD_ERROR


# 全局单例
settings = load_settings_safely()
