"""CLI 入口（Click 框架）."""

import click


@click.group()
def cli() -> None:
    """Songyan（松烟）— 多 Agent 中文小说写作系统."""
    pass


if __name__ == "__main__":
    cli()
