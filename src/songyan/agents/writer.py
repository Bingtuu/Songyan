"""Writer Agent — 接收 ContextPackage，生成章节正文."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import structlog

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.llm.client import call_llm
from songyan.models import ChapterHead, ChapterVersion, ContextPackage

logger = structlog.get_logger(__name__)

SCENE_PATTERN = re.compile(r"^###\s*Scene\s+(\d+)", re.IGNORECASE | re.MULTILINE)
WORD_COUNT_TOLERANCE = 0.10  # ±10%


def _load_prompt_template() -> str:
    """加载 Writer Prompt 模板."""
    template_path = Path(__file__).parents[3] / "prompts" / "writer.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    # 回退：返回简化模板
    return (
        "撰写第 {{ chapter_number }} 章。"
        "目标事件：{{ target_events }}。"
        "字数目标：{{ word_count_target }}。"
        "创作意图：{{ creative_intent }}。"
        "禁忌：{{ forbidden_patterns }}。"
        "使用 ### Scene N 标记场景。"
    )


def _render_prompt(ctx: ContextPackage) -> str:
    """将 ContextPackage 渲染为 Writer Prompt."""
    template = _load_prompt_template()

    goal = ctx.chapter_goal
    brief = ctx.creative_brief

    # 构建各分区文本
    target_events = "\n".join(f"- {e}" for e in goal.target_events) or "（无）"
    hooks = "\n".join(f"- {h}" for h in goal.hooks) or "（无）"
    obligations = "\n".join(f"- {o}" for o in goal.obligations) or "（无）"

    creative_intent = brief.creative_intent if brief else "（无）"

    tensions = "（无）"
    if brief and brief.required_tensions:
        lines = []
        for t in brief.required_tensions:
            lines.append(
                f"- [{t.tension_type}] {t.description} (强度: {t.intensity})"
            )
        tensions = "\n".join(lines)

    forbidden = "（无）"
    if brief and brief.forbidden_patterns:
        forbidden = "\n".join(f"- {p}" for p in brief.forbidden_patterns)

    fissures = "（无）"
    if brief and brief.allowed_fissures:
        fissures = "\n".join(f"- {f}" for f in brief.allowed_fissures)

    style = "（无）"
    if brief and brief.style_constraints:
        style = "\n".join(f"- {s}" for s in brief.style_constraints)

    reader_contract = brief.reader_contract if brief else "（无）"

    hard_constraints = "（无）"
    if ctx.hard_constraints:
        lines = []
        for hc in ctx.hard_constraints:
            lines.append(f"- [{hc.type}] {hc.description}")
        hard_constraints = "\n".join(lines)

    character_states = "（无）"
    if ctx.character_states:
        lines = []
        for cs in ctx.character_states:
            parts = [f"**{cs.name}** (重要性: {cs.importance_score})"]
            if cs.current_location:
                parts.append(f"位置: {cs.current_location}")
            if cs.emotional_state:
                parts.append(f"情绪: {cs.emotional_state}")
            if cs.active_relationships:
                parts.append(f"关系: {', '.join(cs.active_relationships)}")
            lines.append("- " + "；".join(parts))
        character_states = "\n".join(lines)

    recent_plot = "（无）"
    if ctx.recent_plot.summaries or ctx.recent_plot.last_chapter_ending:
        lines = []
        if ctx.recent_plot.last_chapter_ending:
            lines.append(f"上一章结尾：{ctx.recent_plot.last_chapter_ending}")
        for s in ctx.recent_plot.summaries:
            lines.append(f"- 第{s.chapter_number}章：{s.summary}")
        if ctx.recent_plot.open_threads:
            lines.append(f"未完结线索：{', '.join(ctx.recent_plot.open_threads)}")
        recent_plot = "\n".join(lines)

    foreshadowing = "（无）"
    if ctx.foreshadowing:
        lines = []
        for f in ctx.foreshadowing:
            status_tag = f"[{f.status}]"
            lines.append(f"- {status_tag} {f.description}（埋设于第{f.planted_in_chapter}章）")
        foreshadowing = "\n".join(lines)

    genre_rules = "（无）"
    if ctx.genre_rules:
        gr = ctx.genre_rules
        lines = []
        if gr.pacing_rule:
            lines.append(f"- 节奏规则：{gr.pacing_rule}")
        if gr.writer_rules:
            lines.append(f"- 写作规则：{', '.join(gr.writer_rules)}")
        if gr.fatigue_words:
            lines.append(f"- 疲劳词：{', '.join(gr.fatigue_words)}")
        genre_rules = "\n".join(lines)

    mode_rules = "（无）"
    if ctx.mode_rules:
        mr = ctx.mode_rules
        lines = [f"- 修订策略：{mr.revision_policy}"]
        lines.append(f"- AI腔容忍：{mr.tolerance_max_ai_tells}")
        lines.append(f"- 疲劳词容忍：{mr.tolerance_max_fatigue_words}")
        mode_rules = "\n".join(lines)

    # 变量替换
    prompt = template
    replacements = {
        "{{ chapter_number }}": str(goal.chapter_number),
        "{{ chapter_type }}": goal.chapter_type or "（未指定）",
        "{{ word_count_target }}": str(goal.word_count_target),
        "{{ target_events }}": target_events,
        "{{ emotional_arc }}": goal.emotional_arc or "（未指定）",
        "{{ hooks }}": hooks,
        "{{ obligations }}": obligations,
        "{{ creative_intent }}": creative_intent,
        "{{ required_tensions }}": tensions,
        "{{ forbidden_patterns }}": forbidden,
        "{{ allowed_fissures }}": fissures,
        "{{ style_constraints }}": style,
        "{{ reader_contract }}": reader_contract,
        "{{ hard_constraints }}": hard_constraints,
        "{{ character_states }}": character_states,
        "{{ recent_plot }}": recent_plot,
        "{{ foreshadowing }}": foreshadowing,
        "{{ genre_rules }}": genre_rules,
        "{{ mode_rules }}": mode_rules,
    }
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)
    return prompt


def _parse_scenes(content: str) -> list[dict]:
    """按 ### Scene N 标记分割场景.

    返回 [{"scene_number": int, "content": str}, ...]
    """
    if not content.strip():
        return []

    matches = list(SCENE_PATTERN.finditer(content))
    if not matches:
        # 无场景标记，整章作为一个场景
        return [{"scene_number": 1, "content": content.strip()}]

    scenes: list[dict] = []
    for i, match in enumerate(matches):
        scene_number = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        scene_content = content[start:end].strip()
        scenes.append({"scene_number": scene_number, "content": scene_content})
    return scenes


def _count_chinese_words(text: str) -> int:
    """统计中文字数（中文字符 + 连续英文/数字词）."""
    if not text:
        return 0
    # 中文字符
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # 英文/数字词
    other_words = len(re.findall(r"[a-zA-Z0-9]+", text))
    return chinese_chars + other_words


def _extract_body(llm_response: str) -> str:
    """从 LLM 响应中提取正文.

    去除 markdown 代码块标记和前后说明文字。
    """
    text = llm_response.strip()

    # 去除 markdown 代码块
    if text.startswith("```"):
        # 找到第一个换行后的内容和最后的 ```
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 去除常见的首尾说明
    text = re.sub(r"^(以下是|以下是第.*章|正文[：:]\s*)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(完|——完|THE END)\s*$", "", text, flags=re.IGNORECASE)

    return text.strip()


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def write_chapter(
    db_version: ChapterVersionRepository,
    db_head: ChapterHeadRepository,
    project_id: str,
    context_package: ContextPackage,
    creative_brief_id: str | None = None,
    temperature: float = 0.8,
) -> ChapterVersion:
    """生成章节正文并保存为 ChapterVersion.

    Args:
        db_version: ChapterVersion 仓库
        db_head: ChapterHead 仓库
        project_id: 项目 ID
        context_package: 上下文包（来自 ContextManager）
        creative_brief_id: CreativeBrief ID（写入版本外键）
        temperature: LLM 温度（默认 0.8）

    Returns:
        新创建的 ChapterVersion
    """
    goal = context_package.chapter_goal
    chapter_number = goal.chapter_number

    logger.info(
        "writer.start",
        project_id=project_id,
        chapter_number=chapter_number,
        word_count_target=goal.word_count_target,
    )

    # 渲染 Prompt
    prompt = _render_prompt(context_package)

    # 调用 LLM
    llm_response = await call_llm(prompt, temperature=temperature)

    # 提取正文
    content = _extract_body(llm_response)

    # 解析场景
    scenes = _parse_scenes(content)

    # 字数统计
    word_count = _count_chinese_words(content)

    # 确定版本号
    existing_versions = await db_version.list_by_chapter(project_id, chapter_number)
    version_number = len(existing_versions) + 1

    # 创建 version_id
    version_id = f"v-{chapter_number}-{version_number}-{uuid.uuid4().hex[:8]}"

    # 构建 generation_metadata
    generation_metadata = {
        "context_snapshot": {
            "estimated_tokens": context_package.estimated_tokens,
            "budget_used": context_package.budget_used,
            "assembled_at": context_package.assembled_at.isoformat()
            if hasattr(context_package.assembled_at, "isoformat")
            else str(context_package.assembled_at),
        },
        "prompt_length": len(prompt),
        "scenes_count": len(scenes),
    }

    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=version_number,
        version_type="draft",
        content=content,
        word_count=word_count,
        scenes=scenes,
        generation_metadata=generation_metadata,
        creative_brief_id=creative_brief_id,
    )

    # 保存版本
    await db_version.create(version)

    # 更新 ChapterHead
    head = await db_head.get(project_id, chapter_number)
    if head is None:
        head = ChapterHead(
            project_id=project_id,
            chapter_number=chapter_number,
            current_version_id=version_id,
            status="draft",
        )
    else:
        head.current_version_id = version_id
        head.status = "draft"
    await db_head.update(head)

    logger.info(
        "writer.done",
        project_id=project_id,
        chapter_number=chapter_number,
        version_id=version_id,
        version_number=version_number,
        word_count=word_count,
        scenes_count=len(scenes),
    )
    return version
