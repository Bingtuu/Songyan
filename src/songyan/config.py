"""Pydantic Settings 配置管理."""

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
