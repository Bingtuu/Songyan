"""分批运行多章验证 — 每章独立进程，避免心跳超时."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.llm.client import call_llm
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline
from evals.runner import import_seed_chapter, import_seed_project
from songyan.utils.cost_estimator import estimate_cost_from_calls, format_cost_estimate

SEED_CONFIGS = {
    "scifi": ("evals/seeds/scifi_new_weird.json", "evals/seeds/chapters/scifi_new_weird_ch1.md"),
    "xuanhuan": ("evals/seeds/xuanhuan_webnovel.json", "evals/seeds/chapters/xuanhuan_ch1.md"),
    "urban": ("evals/seeds/urban_hybrid.json", "evals/seeds/chapters/urban_ch1.md"),
}

LLM_CALLS: list[dict] = []


async def _wrapped_call_llm(prompt, *, temperature=0.7, max_retries=3, _agent_name="unknown"):
    t0 = time.perf_counter()
    try:
        response = await call_llm(prompt=prompt, temperature=temperature, max_retries=max_retries)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        LLM_CALLS.append({
            "agent": _agent_name, "timestamp": datetime.now().isoformat(),
            "elapsed_ms": elapsed_ms, "prompt_chars": len(prompt),
            "response_chars": 0, "error": str(exc), "temperature": temperature,
        })
        raise
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    LLM_CALLS.append({
        "agent": _agent_name, "timestamp": datetime.now().isoformat(),
        "elapsed_ms": elapsed_ms, "prompt_chars": len(prompt),
        "response_chars": len(response), "temperature": temperature,
    })
    return response


# =============================================================================
# Markdown 导出 helpers
# =============================================================================


async def _export_chapter_markdown(
    project_id: str,
    chapter_number: int,
    md_dir: Path,
    extra_meta: dict | None = None,
) -> Path | None:
    """从数据库读取章节最终版本，导出为 Markdown 文件.

    Returns:
        写入的文件路径，或 None（无可用版本）
    """
    from sqlite3 import Row
    from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository

    # 读取 chapter_head 获取 accepted_version
    head_repo = ChapterHeadRepository()
    head = await head_repo.get(project_id, chapter_number)
    if head is None or not head.accepted_version_id:
        return None

    # 读取版本内容
    version_repo = ChapterVersionRepository()
    version = await version_repo.get(head.accepted_version_id)
    if version is None or not version.content:
        return None

    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"chapter_{chapter_number:02d}.md"

    # YAML frontmatter — 只保留与阅读相关的字段，排除运行态数据
    meta = {
        "title": f"第{chapter_number}章",
        "word_count": version.word_count,
        "scenes": len(version.scenes),
        "version": version.version_number,
    }
    # extra_meta 中的运行态数据（elapsed_sec / llm_calls / cost）不写入 frontmatter
    # 避免干扰读者阅读体验

    frontmatter_lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            frontmatter_lines.append(f"{k}:")
            for item in v:
                frontmatter_lines.append(f"  - {item}")
        else:
            frontmatter_lines.append(f"{k}: {v}")
    frontmatter_lines.append("---")

    md_content = "\n".join(frontmatter_lines) + "\n\n" + version.content.strip() + "\n"
    md_path.write_text(md_content, encoding="utf-8")
    return md_path


async def _export_project_index(
    project_id: str,
    chapters: list[int],
    md_dir: Path,
    total_cost: str = "",
    total_time_sec: float = 0.0,
) -> Path:
    """生成项目索引 README.md，列出所有章节."""
    from songyan.db.repository import ProjectRepository

    proj_repo = ProjectRepository()
    project = await proj_repo.get(project_id)
    title = project.title if project else "未知项目"
    genre = project.genre_id if project else ""
    mode = project.mode_id if project else ""

    lines = [
        f"# {title}",
        "",
        f"- **项目 ID**: `{project_id}`",
        f"- **题材**: {genre}",
        f"- **模式**: {mode}",
        f"- **总章节数**: {len(chapters)}",
    ]
    if total_cost:
        lines.append(f"- **预估成本**: {total_cost}")
    if total_time_sec:
        lines.append(f"- **总耗时**: {total_time_sec / 60:.1f} 分钟")
    lines.extend([
        "",
        "## 章节列表",
        "",
    ])

    for ch in sorted(chapters):
        md_file = md_dir / f"chapter_{ch:02d}.md"
        if md_file.exists():
            # 尝试提取字数
            wc = ""
            try:
                content = md_file.read_text(encoding="utf-8")
                for line in content.splitlines()[:15]:
                    if line.startswith("word_count:"):
                        wc = line.split(":", 1)[1].strip()
                        break
            except Exception:
                pass
            info = f"（{wc} 字）" if wc else ""
            lines.append(f"- [第{ch}章](chapters/chapter_{ch:02d}.md){info}")
        else:
            lines.append(f"- 第{ch}章（待生成）")

    lines.append("")

    readme_path = md_dir.parent / "README.md"
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    return readme_path


# =============================================================================
# 核心运行逻辑
# =============================================================================


async def _run_batch_inner(seed: str, project_id: str | None, chapter: int, output_dir: Path) -> dict:
    """运行单章（在 db_path patch 内部）."""
    global LLM_CALLS
    LLM_CALLS = []

    seed_config_path, seed_chapter_path = SEED_CONFIGS[seed]
    db_path = output_dir / "test.db"

    if project_id is None:
        # 第一次：导入种子
        await init_schema(db_path=db_path)
        project_id = await import_seed_project(seed_config_path)
        await import_seed_chapter(project_id, seed_chapter_path)
        print(f"   项目 ID: {project_id}")
        print("seed chapter imported")

    # 重置 LangGraph checkpointer（避免 asyncio Lock 跨事件循环绑定问题）
    await reset_checkpointer()

    # 运行单章
    with patch("songyan.llm.client.call_llm", _wrapped_call_llm):
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(chapter, chapter),
            auto_confirm=True,
            on_failure="retry",
            max_revision_rounds=1,
        )

    return {
        "project_id": project_id,
        "chapter": chapter,
        "success": chapter not in result.chapters_failed,
        "llm_calls": len(LLM_CALLS),
        "cost": format_cost_estimate(estimate_cost_from_calls(LLM_CALLS)),
        "raw_cost": estimate_cost_from_calls(LLM_CALLS),
    }


async def run_batch(seed: str, project_id: str | None, chapter: int, output_dir: Path) -> dict:
    """运行单章，统一 patch db_path."""
    db_path = output_dir / "test.db"
    with patch("songyan.db.connection.get_db_path", return_value=db_path):
        return await _run_batch_inner(seed, project_id, chapter, output_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", choices=["scifi", "xuanhuan", "urban"], default="scifi")
    parser.add_argument("--chapters", type=int, default=10)
    parser.add_argument("--start", type=int, default=2, help="起始章节（默认2）")
    parser.add_argument("--project-id", help="已有项目ID（ resume 模式）")
    parser.add_argument("--output-dir", help="输出目录（ resume 模式）")
    parser.add_argument("--md-dir", help="Markdown 导出目录（默认 projects/<seed>_novel/chapters/）")
    args = parser.parse_args()

    if not settings.llm_api_key:
        print("❌ LLM API Key 未配置"); sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else None
    project_id = args.project_id

    # Markdown 导出目录
    if args.md_dir:
        md_dir = Path(args.md_dir)
    else:
        md_dir = Path(f"projects/{args.seed}_novel/chapters")
    md_dir.mkdir(parents=True, exist_ok=True)

    total_llm_calls = 0
    total_cost_usd = 0.0
    completed_chapters: list[int] = []

    for ch in range(args.start, args.start + args.chapters):
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(f"evals/output/multi_chapter_{args.seed}_{timestamp}")
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"🚀 Chapter {ch} / {args.start + args.chapters - 1}")
        print(f"{'='*60}")

        t0 = time.monotonic()
        result = asyncio.run(run_batch(args.seed, project_id, ch, output_dir))
        elapsed = time.monotonic() - t0
        project_id = result["project_id"]

        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"\n{status} | {elapsed:.1f}s | {result['llm_calls']} calls | {result['cost']}")

        # 保存进度
        progress_file = output_dir / "progress.json"
        progress = []
        if progress_file.exists():
            progress = json.loads(progress_file.read_text(encoding="utf-8"))
        progress.append({
            "chapter": ch, "success": result["success"],
            "elapsed_sec": elapsed, "llm_calls": result["llm_calls"],
            "cost": result["cost"],
        })
        progress_file.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")

        # 导出 Markdown（必须 patch db_path 连接到验证数据库）
        db_path = output_dir / "test.db"
        with patch("songyan.db.connection.get_db_path", return_value=db_path):
            if result["success"]:
                md_path = asyncio.run(_export_chapter_markdown(
                    project_id=project_id,
                    chapter_number=ch,
                    md_dir=md_dir,
                    extra_meta={"elapsed_sec": round(elapsed, 1), "llm_calls": result["llm_calls"], "cost": result["cost"]},
                ))
                if md_path:
                    print(f"   📝 Markdown 已导出: {md_path}")
                completed_chapters.append(ch)
                total_llm_calls += result["llm_calls"]
                total_cost_usd += result["raw_cost"].get("total_usd", 0.0) if isinstance(result["raw_cost"], dict) else 0.0

            # 更新项目索引
            asyncio.run(_export_project_index(
                project_id=project_id,
                chapters=completed_chapters,
                md_dir=md_dir,
                total_cost=f"~¥{total_cost_usd * 7.2:.2f}" if total_cost_usd else "",
                total_time_sec=sum(p["elapsed_sec"] for p in progress),
            ))
        print(f"   📑 项目索引已更新: {md_dir.parent / 'README.md'}")

        if not result["success"]:
            print(f"\n⚠️ Chapter {ch} 失败，停止后续章节")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("🎉 全部完成！")
    print(f"   项目 ID: {project_id}")
    print(f"   输出目录: {output_dir}")
    print(f"   Markdown 目录: {md_dir}")
    print(f"   总 LLM 调用: {total_llm_calls}")
    if total_cost_usd:
        print(f"   预估总成本: ~¥{total_cost_usd * 7.2:.2f}")


if __name__ == "__main__":
    main()
