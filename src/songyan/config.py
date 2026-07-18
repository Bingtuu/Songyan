"""Pydantic Settings 配置管理."""

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Songyan 全局配置，从 .env 文件加载."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM 配置
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_retries: int = 3
    llm_rate_limit_max_wait: float = 60.0
    llm_run_call_budget: int = 0  # 0 = 不启用单 run 调用预算

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
    checkpointer_mode: Literal["memory", "sqlite"] = "sqlite"


# 全局单例
settings = Settings()
