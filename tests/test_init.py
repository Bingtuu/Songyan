"""Task 001 验收测试：验证项目可正确导入."""

import songyan
from songyan.config import Settings


def test_import_songyan() -> None:
    """项目可正确导入."""
    assert hasattr(songyan, "__version__")
    assert songyan.__version__ == "0.1.0"


def test_settings_defaults() -> None:
    """Settings 有正确的默认值."""
    s = Settings()
    assert s.llm_base_url == "https://api.deepseek.com"
    assert s.llm_model == "deepseek-chat"
    assert s.llm_temperature == 0.7
    assert s.context_total_budget == 32_000
    assert s.context_generation_reserve == 8_000
    assert s.log_level == "INFO"
    assert s.database_url == "sqlite:///songyan.db"


def test_cli_entry_exists() -> None:
    """CLI 入口可被引用."""
    from songyan.cli.main import cli
    assert cli is not None
