"""Pydantic Settings 配置管理."""

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

    # Token 预算
    context_total_budget: int = 32_000
    context_generation_reserve: int = 8_000

    # 日志
    log_level: str = "INFO"

    # 数据库
    database_url: str = "sqlite:///songyan.db"


# 全局单例
settings = Settings()
