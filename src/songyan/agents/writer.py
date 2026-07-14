"""Writer Agent — 接收 ContextPackage，生成章节正文."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import structlog

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.llm.client import call_llm
from songyan.models import ChapterHead, ChapterVersion, ContextPackage
from songyan.models.human_instruction import normalize_human_instruction
from songyan.prompts import get_prompt_loader
from songyan.utils.scene_parser import parse_scenes as _parse_scenes
from songyan.utils.truncation import enforce_word_count as _enforce_word_count
from songyan.utils.truncation import hard_truncate_at_boundary
from songyan.utils.word_count import count_chinese_words as _count_chinese_words

logger = structlog.get_logger(__name__)

WORD_COUNT_TOLERANCE = 0.10  # ±10%

_SCENE_MARKER_TOKEN = r"(?:\d+|[A-Z]|[一二三四五六七八九十]+)"
_SCENE_MARKER_LINE_PATTERNS: tuple[str, ...] = (
    rf"(?im)^\s*#{{1,6}}\s*Scene\s+{_SCENE_MARKER_TOKEN}.*$",
    rf"(?im)^\s*Scene\s+{_SCENE_MARKER_TOKEN}(?:\s*[:：].*)?\s*$",
    rf"(?im)^\s*\*\*Scene\s+{_SCENE_MARKER_TOKEN}\*\*.*$",
    rf"(?im)^\s*#{{1,6}}\s*场景\s*{_SCENE_MARKER_TOKEN}.*$",
    rf"(?im)^\s*场景\s*{_SCENE_MARKER_TOKEN}(?:\s*[:：].*)?\s*$",
    rf"(?im)^\s*\*\*场景\s*{_SCENE_MARKER_TOKEN}\*\*.*$",
)


def _hard_truncate_at_boundary(content: str, max_words: int) -> str:
    """兼容旧 Writer 测试的硬截断入口."""
    return hard_truncate_at_boundary(content, max_words)


def _strip_scene_marker_lines(text: str) -> str:
    """去除正文中泄漏的显式场景编号行."""
    for pattern in _SCENE_MARKER_LINE_PATTERNS:
        text = re.sub(pattern, "", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def _compute_scene_budget(word_count_target: int, chapter_type: str) -> str:
    """Task 092+093: 场景字数预算 — 只给场景数量建议和篇幅比例指导，不给具体数字.

    避免 LLM 被具体数字束缚导致系统性偏差（要么全部取低值，要么全部超标）。
    返回格式化的场景分配文本，注入 Writer Prompt。
    """
    w = word_count_target
    if chapter_type in ("conflict", "climax", "tech_revelation"):
        return (
            f"本章目标 {w} 字，建议 2-3 个场景。核心场景应占主要篇幅，"
            f"转折场景承上启下，收尾场景简洁有力、留下钩子。"
        )
    elif chapter_type in ("transition", "exposition"):
        return (
            f"本章目标 {w} 字，建议 2 个场景。第一场景铺陈引入，第二场景推进或收束。"
        )
    else:
        return (
            f"本章目标 {w} 字，建议 2-3 个场景。引入场景建立情境，"
            f"发展场景推进冲突，收尾场景落下钩子。"
        )


def _render_prompt(ctx: ContextPackage) -> str:
    """将 ContextPackage 渲染为 Writer Prompt."""
    from songyan.prompts import get_prompt_loader

    loader = get_prompt_loader()
    card = loader.load_card("writer")

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

    # Task 074: 角色对话风格卡
    dialogue_style_cards_text = "（无）"
    if ctx.dialogue_style_cards:
        lines = []
        for dsc in ctx.dialogue_style_cards:
            lines.append(f"### {dsc.character_id}")
            if dsc.common_openers:
                lines.append(f"- 口头禅：{' / '.join(dsc.common_openers)}")
            lines.append(f"- 句式偏好：{dsc.sentence_length_preference}")
            if dsc.anger_expression:
                lines.append(f"- 愤怒时：{dsc.anger_expression}")
            if dsc.fear_expression:
                lines.append(f"- 恐惧时：{dsc.fear_expression}")
            if dsc.joy_expression:
                lines.append(f"- 喜悦时：{dsc.joy_expression}")
            if dsc.sadness_expression:
                lines.append(f"- 悲伤时：{dsc.sadness_expression}")
            if dsc.pause_habit:
                lines.append(f"- 停顿习惯：{dsc.pause_habit}")
            irony_usage = "是" if dsc.irony_usage else "否"
            lines.append(f"- 隐喻频率：{dsc.metaphor_frequency}，反讽：{irony_usage}")
            lines.append(f"- 打断频率：{dsc.interrupt_frequency}")
            if dsc.education_level_hint:
                lines.append(f"- 语言背景：{dsc.education_level_hint}")
            if dsc.social_role_speech_pattern:
                lines.append(f"- 社会角色语气：{dsc.social_role_speech_pattern}")
            lines.append("")
        dialogue_style_cards_text = "\n".join(lines)

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

    # Phase 5: 风格基线
    style_baseline = None
    if ctx.genre_rules and ctx.genre_rules.style_baseline:
        sb = ctx.genre_rules.style_baseline
        style_baseline = {
            "sentence_rhythm": sb.sentence_rhythm,
            "description_density": sb.description_density,
            "dialogue_ratio": sb.dialogue_ratio,
            "inner_monologue": sb.inner_monologue,
            "pov_depth": sb.pov_depth,
        }

    # Phase 5: 风格样本（从 soft_references 提取）
    import json as _json

    style_samples = []
    for ref in ctx.soft_references:
        if ref.type == "style_sample":
            try:
                data = _json.loads(ref.content)
                style_samples.append({
                    "work_name": data.get("work_name", ""),
                    "author": data.get("author", ""),
                    "excerpt": data.get("excerpt", ""),
                    "analysis": data.get("analysis", ""),
                })
            except (json.JSONDecodeError, TypeError, ValueError):
                style_samples.append({
                    "work_name": "",
                    "author": "",
                    "excerpt": ref.content[:200],
                    "analysis": "",
                })

    # Phase 5: 当前章节匹配的 pacing_template
    pacing_template = None
    if ctx.genre_rules and ctx.genre_rules.pacing_templates:
        chapter_type = goal.chapter_type or ""
        for pt in ctx.genre_rules.pacing_templates:
            chapter_types = pt.get("chapter_types", [])
            if chapter_type in chapter_types or not chapter_type:
                pacing_template = {
                    "emotion_arc": pt.get("emotion_arc", ""),
                    "punch_density": pt.get("punch_density", 0.0),
                    "info_release_strategy": pt.get("info_release_strategy", ""),
                }
                break
        # 如果没有匹配，使用第一个
        if pacing_template is None:
            pt = ctx.genre_rules.pacing_templates[0]
            pacing_template = {
                "emotion_arc": pt.get("emotion_arc", ""),
                "punch_density": pt.get("punch_density", 0.0),
                "info_release_strategy": pt.get("info_release_strategy", ""),
            }

    # Phase 5: 感官描写侧重
    sensory_focus = []
    if ctx.genre_rules and ctx.genre_rules.sensory_templates:
        for st in ctx.genre_rules.sensory_templates:
            sensory_focus.append({
                "sense": st.get("sense", ""),
                "intensity_target": st.get("intensity_target", 0.0),
                "description_density": st.get("description_density", 0.0),
                "example_phrases": st.get("example_phrases", []),
            })

    mode_rules = "（无）"
    if ctx.mode_rules:
        mr = ctx.mode_rules
        lines = [f"- 修订策略：{mr.revision_policy}"]
        lines.append(f"- AI腔容忍：{mr.tolerance_max_ai_tells}")
        lines.append(f"- 疲劳词容忍：{mr.tolerance_max_fatigue_words}")
        mode_rules = "\n".join(lines)

    # Task 170j: 文学优化插件（仅当 mode_profile 配置了插件时加载）
    literary_plugins = ""
    if ctx.mode_profile and ctx.mode_profile.literary_optimization_plugins:
        from songyan.literary_optimization.plugin_loader import load_strategy_plugins

        fragments = load_strategy_plugins(
            ctx.mode_profile.literary_optimization_plugins, "writer"
        )
        if fragments:
            literary_plugins = "\n\n".join(fragments)

    # Task 170j: 极简声纹锚定
    voice_anchors = ""
    if brief and brief.voice_anchors:
        lines = ["## 极简声纹锚定"]
        for va in brief.voice_anchors:
            lines.append(
                f"- {va.character_id}：情绪基调={va.emotional_register}，"
                f"口头禅={va.verbal_tick}，禁忌={va.taboo_phrase}"
            )
        voice_anchors = "\n".join(lines)

    # Task 170l: 少样本声纹锚定
    voice_samples = ""
    if brief and brief.voice_samples:
        lines = ["## 少样本声纹锚定"]
        for vs in brief.voice_samples:
            lines.append(
                f"- {vs.character_name}（{vs.character_id}）：情绪基调={vs.mood_anchor}"
            )
            for line in vs.sample_lines:
                lines.append(f"  示例：{line}")
            if vs.forbidden_patterns:
                lines.append(f"  禁用：{', '.join(vs.forbidden_patterns)}")
        voice_samples = "\n".join(lines)

    # 刺激点执行清单（Punch Engine）
    punch_points = []
    if brief and brief.punch_points:
        for p in brief.punch_points:
            punch_points.append({
                "punch_type": p.punch_type,
                "target_scene": p.target_scene,
                "description": p.description,
                "intensity": p.intensity,
                "dominant_sense": p.dominant_sense,
            })

    # 情绪曲线
    emotion_arc = []
    if brief and brief.emotion_arc:
        for a in brief.emotion_arc:
            emotion_arc.append({
                "scene": a.scene,
                "from_emotion": a.from_emotion,
                "to_emotion": a.to_emotion,
            })

    # Phase 4: 分层上下文格式化
    arc_context = None
    if ctx.arc_context:
        arc = ctx.arc_context
        arc_context = {
            "arc_title": arc.arc_title,
            "arc_summary": arc.arc_summary,
            "key_events": arc.key_events,
            "character_arcs": arc.character_arcs,
        }

    volume_context = None
    if ctx.volume_context:
        vol = ctx.volume_context
        volume_context = {
            "volume_title": vol.volume_title,
            "volume_summary": vol.volume_summary,
            "major_revelations": vol.major_revelations,
            "world_state": vol.world_state,
        }

    permanent_scenes = []
    for ps in ctx.permanent_scenes:
        permanent_scenes.append({
            "chapter_number": ps.chapter_number,
            "scene_number": ps.scene_number,
            "excerpt": ps.excerpt,
            "impact_tags": ps.impact_tags,
        })

    # Phase 8b: RAG 检索结果
    rag_results = []
    for ref in ctx.soft_references:
        if ref.type == "rag_retrieval":
            rag_results.append({
                "chapter_number": ref.source_chapter,
                "text": ref.content,
                "metadata": {
                    "chunk_type": "narrative",  # 简化，实际可从 content 推断
                },
            })

    open_threads = []
    for ot in ctx.open_threads:
        open_threads.append({
            "thread_id": ot.thread_id,
            "description": ot.description,
            "source_type": ot.source_type,
            "source_chapter": ot.source_chapter,
            "priority": ot.priority,
        })

    # Phase 7/054: human_marks 渲染
    human_marks = []
    for hm in ctx.human_marks:
        human_marks.append({
            "mark_type": hm.mark_type,
            "target_key": hm.target_key,
            "note": hm.note,
            "priority": hm.priority,
            "source": hm.source,
        })

    # Task 138h: mandatory_references 渲染
    mandatory_references_text = "（无）"
    if ctx.mandatory_references:
        lines = []
        lines.append(
            "以下设定已沉寂 ≥3 章且属于 critical 级别，"
            "本章必须明确提及、使用、或给出无法回收的剧情原因："
        )
        for mref in ctx.mandatory_references:
            name = mref.get("setting_name") or mref.get("setting_key") or "未命名设定"
            key = mref.get("setting_key") or ""
            silent = mref.get("silent_chapters", 0)
            hint = mref.get("recycle_hint", "")
            hint_line = f"\n  【建议】{hint}" if hint else ""
            lines.append(f"- {name}（{key}）：已沉寂 {silent} 章{hint_line}")
        mandatory_references_text = "\n".join(lines)

    # Task 092: 计算场景字数预算
    scene_budget_text = _compute_scene_budget(
        goal.word_count_target,
        goal.chapter_type or "",
    )

    variables = {
        "chapter_number": goal.chapter_number,
        "chapter_type": goal.chapter_type or "（未指定）",
        "word_count_target": goal.word_count_target,
        "scene_budget": scene_budget_text,
        "target_events": target_events,
        "emotional_arc": goal.emotional_arc or "（未指定）",
        "hooks": hooks,
        "obligations": obligations,
        "creative_intent": creative_intent,
        "required_tensions": tensions,
        "forbidden_patterns": forbidden,
        "allowed_fissures": fissures,
        "style_constraints": style,
        "reader_contract": reader_contract,
        "hard_constraints": hard_constraints,
        "character_states": character_states,
        "recent_plot": recent_plot,
        "foreshadowing": foreshadowing,
        "genre_rules": genre_rules,
        "mode_rules": mode_rules,
        "punch_points": punch_points,
        "emotion_arc": emotion_arc,
        "human_instructions": [
            normalize_human_instruction(inst).model_dump(mode="json")
            for inst in ctx.human_instructions
            if isinstance(inst, dict)
        ],
        "arc_context": arc_context,
        "volume_context": volume_context,
        "permanent_scenes": permanent_scenes,
        "open_threads": open_threads,
        "style_baseline": style_baseline,
        "style_samples": style_samples,
        "pacing_template": pacing_template,
        "sensory_focus": sensory_focus,
        "rag_results": rag_results,
        "human_marks": human_marks,
        "dialogue_style_cards": dialogue_style_cards_text,
        "mandatory_references": mandatory_references_text,
        "literary_plugins": literary_plugins,
        "voice_anchors": voice_anchors,
        "voice_samples": voice_samples,
    }

    tags: list[str] = []
    if goal.chapter_number <= 3:
        tags.append("chapter_early")

    rendered = loader.render_card(card, variables, tags=tags)
    return rendered.full_prompt


def _extract_body(llm_response: str, strip_scene_markers: bool = True) -> str:
    """从 LLM 响应中提取正文.

    去除 markdown 代码块标记、前后说明文字、场景清单、核心事件等元数据。
    Args:
        strip_scene_markers: 为 True 时同时去除 `### Scene N` 等显式场景编号。
    """
    text = llm_response.strip()

    # 去除 markdown 代码块
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 去除常见的首尾说明
    text = re.sub(r"^(以下是|以下是第.*章|正文[：:]\s*)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(完|——完|THE END)\s*$", "", text, flags=re.IGNORECASE)

    # 去除 LLM 偶尔输出的 `# 第一章` / `## 第一章` / `# 第1章` 等 Markdown 章节标题行
    text = re.sub(
        r"^#+\s*第\s*[一二三四五六七八九十百千万零〇两\d]+\s*章\s*\n?",
        "",
        text,
        flags=re.MULTILINE,
    )

    # 去除场景清单（从 # 场景清单 到 --- 或下一个 ### Scene）
    text = re.sub(
        r"(?i)^#\s*场景清单.*?\n---\s*\n",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"(?i)^#\s*场景清单.*?(?=\n###\s*Scene\s+\d+)",
        "",
        text,
        flags=re.DOTALL,
    )

    # 将 `# Scene N` / `## Scene N` 转换为 `### Scene N`，供显式保留模式解析。
    if not strip_scene_markers:
        text = re.sub(
            r"^#{1,2}\s*(Scene\s+\d+)",
            r"### \1",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

    # 默认去除所有显式场景编号，使最终入库正文只使用空行分隔场景。
    if strip_scene_markers:
        text = _strip_scene_marker_lines(text)
    else:
        # 兼容旧路径：占位符标题无法被 scene_parser 解析，直接清理。
        text = re.sub(
            r"^###\s*Scene\s+(?!\d).*$\n?",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

    # 去除以 "核心事件："、"时间："、"地点：" 开头的段落（但保留 ### Scene 后的第一行）
    lines = text.splitlines()
    filtered_lines: list[str] = []
    prev_was_scene_header = False
    for line in lines:
        stripped = line.strip()
        # 显式保留模式下，Scene 标题行供内部 parser 使用。
        if (
            not strip_scene_markers
            and re.match(r"^###\s*Scene\s+\d+", stripped, re.IGNORECASE)
        ):
            filtered_lines.append(line)
            prev_was_scene_header = True
            continue
        # Scene 标题后的第一行允许保留（通常是时间/地点/事件描述）
        if prev_was_scene_header:
            filtered_lines.append(line)
            prev_was_scene_header = False
            continue
        # 过滤元数据格式
        if re.match(r"^(核心事件|时间|地点)[：:]\s*", stripped):
            continue
        if re.match(r"^\*\*Scene\s+\d+\*\*[:：]", stripped):
            continue
        if re.match(r"^Scene\s+\d+[:：]", stripped):
            continue
        filtered_lines.append(line)

    text = "\n".join(filtered_lines).strip()

    # 去除多余的空行（连续3行以上空行压缩为2行）
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # 去除所有 HTML 注释（兜底清理元标记泄漏）
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 去除旧版可见标记 [[新设定:...]]（兜底）
    text = re.sub(r"\[\[新设定:[^\]]+\]\]", "", text)

    return text.strip()


def _build_creative_brief_snapshot(ctx: ContextPackage) -> dict[str, Any]:
    """生成精简 CreativeBrief 快照，供版本 metadata 回放."""
    brief = ctx.creative_brief
    if brief is None:
        return {}
    return {
        "creative_intent": brief.creative_intent,
        "required_tensions": [
            tension.model_dump(mode="json") for tension in brief.required_tensions
        ],
        "forbidden_patterns": brief.forbidden_patterns,
        "allowed_fissures": brief.allowed_fissures,
        "style_constraints": brief.style_constraints,
        "reader_contract": brief.reader_contract,
        "punch_points": [point.model_dump(mode="json") for point in brief.punch_points],
        "emotion_arc": [item.model_dump(mode="json") for item in brief.emotion_arc],
        "narrative_fullness": brief.narrative_fullness,
        "character_focus": brief.character_focus,
        "foreshadowing_due": brief.foreshadowing_due,
        "focal_distance": brief.focal_distance,
        "protagonist_active_choice": (
            brief.protagonist_active_choice.model_dump(mode="json")
            if brief.protagonist_active_choice is not None
            else None
        ),
        "new_concept_budget": (
            brief.new_concept_budget.model_dump(mode="json")
            if brief.new_concept_budget is not None
            else None
        ),
        "fatigue_motif_replacements": [
            item.model_dump(mode="json") for item in brief.fatigue_motif_replacements
        ],
        "supporting_character_goal": (
            brief.supporting_character_goal.model_dump(mode="json")
            if brief.supporting_character_goal is not None
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def write_chapter(
    db_version: ChapterVersionRepository,
    db_head: ChapterHeadRepository,
    project_id: str,
    context_package: ContextPackage,
    creative_brief_id: str | None = None,
    context_snapshot_id: str | None = None,
    temperature: float = 0.8,
) -> ChapterVersion:
    """生成章节正文并保存为 ChapterVersion.

    Args:
        db_version: ChapterVersion 仓库
        db_head: ChapterHead 仓库
        project_id: 项目 ID
        context_package: 上下文包（来自 ContextManager）
        creative_brief_id: CreativeBrief ID（写入版本外键）
        context_snapshot_id: ContextManager 写入的上下文快照 ID
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

    # 确定当前 Writer 工艺卡版本，以启用 1.2.0+ 的多场景结构处理
    loader = get_prompt_loader()
    writer_card = loader.load_card("writer")
    writer_version = writer_card.metadata.version
    strict_scenes = writer_version >= "1.2.0"

    # 渲染 Prompt
    prompt = _render_prompt(context_package)

    # 调用 LLM
    llm_response = await call_llm(prompt, temperature=temperature, max_tokens=6000)

    # 提取正文：最终入库正文禁止出现场景编号；内部解析可保留标题恢复 scene 边界。
    parse_content = _extract_body(llm_response, strip_scene_markers=False)
    content = _extract_body(llm_response)

    # 解析场景：仅当内部文本保留了 scene_parser 可识别的数字标题时使用它，
    # 避免不可解析的加粗/中文标题残留进 scenes metadata。
    has_parseable_scene_markers = bool(
        re.search(r"(?im)^\s*###\s*Scene\s+\d+", parse_content)
    )
    scene_source = parse_content if has_parseable_scene_markers else content
    # Writer 1.2.0+ 使用严格多场景结构参数。
    if strict_scenes:
        scenes = _parse_scenes(
            scene_source,
            min_scene_chars=600,
            max_scene_chars=2400,
            target_scene_chars=1800,
        )
    else:
        scenes = _parse_scenes(scene_source)
    if len(scenes) < 2:
        logger.warning(
            "writer.scenes_count_low",
            project_id=project_id,
            chapter_number=chapter_number,
            scenes_count=len(scenes),
            expected_min=2,
        )
        # 不阻塞 pipeline，将 scene 不足标记为 warning
        # 由 LLMAuditor 在审查阶段捕获并进入 revision 流程

    # 字数统计
    word_count = _count_chinese_words(content)
    word_count_target = goal.word_count_target

    # 字数达标校验
    if word_count_target > 0:
        deviation = abs(word_count - word_count_target) / word_count_target
        if deviation > WORD_COUNT_TOLERANCE:
            logger.warning(
                "writer.word_count_mismatch",
                project_id=project_id,
                chapter_number=chapter_number,
                word_count=word_count,
                word_count_target=word_count_target,
                deviation=round(deviation, 2),
            )

    # 076: Writer 强制字数截断
    original_word_count = word_count
    _chapter_type = (
        context_package.chapter_goal.chapter_type
        if context_package.chapter_goal
        else None
    )
    (
        _trunc_content,
        _trunc_scenes,
        _trunc_wc,
        _was_truncated,
        _trunc_reason,
    ) = _enforce_word_count(
        content, scenes, word_count_target, word_count,
        chapter_type=_chapter_type
    )
    _is_disallowed = _trunc_reason in ("_disallowed_by_scene_structure", "_no_scenes_found")
    _is_no_headers = _trunc_reason == "no_scene_headers_found"
    _actually_truncated = _was_truncated and not _is_disallowed and not _is_no_headers
    if _actually_truncated:
        content = _trunc_content
        scenes = _trunc_scenes
        word_count = _trunc_wc
        logger.warning(
            "writer.word_count_truncated",
            project_id=project_id,
            chapter_number=chapter_number,
            original_word_count=original_word_count,
            new_word_count=word_count,
            truncation_reason=_trunc_reason,
        )
    elif word_count_target > 0 and word_count > int(word_count_target * 1.20):
        # 修复 A: scene 边界截断失败时，追加硬截断回退
        _hard_max = int(word_count_target * 1.20)
        _hard_content = _hard_truncate_at_boundary(content, _hard_max)
        if _hard_content != content:
            content = _hard_content
            scenes = _parse_scenes(content)
            word_count = _count_chinese_words(content)
            _actually_truncated = True
            _trunc_reason = "hard_truncated_at_boundary"
            logger.warning(
                "writer.word_count_hard_truncated",
                project_id=project_id,
                chapter_number=chapter_number,
                original_word_count=original_word_count,
                new_word_count=word_count,
                max_words=_hard_max,
            )

    # 确定版本号（包含废弃版本，避免编号冲突）
    version_number = await db_version.get_next_version_number(project_id, chapter_number)

    # 创建 version_id
    version_id = f"v-{chapter_number}-{version_number}-{uuid.uuid4().hex[:8]}"

    # 构建 generation_metadata
    generation_metadata = {
        "context_snapshot_id": context_snapshot_id,
        "context_snapshot": {
            "estimated_tokens": context_package.estimated_tokens,
            "budget_used": context_package.budget_used,
            "character_states_loaded": len(context_package.character_states),
            "soft_refs_loaded": len(context_package.soft_references),
            "context_emergency": context_package.context_emergency,
            "budget_used_before_emergency": getattr(
                context_package, "budget_used_before_emergency", None
            ),
            "assembled_at": context_package.assembled_at.isoformat()
            if hasattr(context_package.assembled_at, "isoformat")
            else str(context_package.assembled_at),
        },
        "_word_count_truncated": _actually_truncated,
        "_word_count_original": original_word_count if _actually_truncated else word_count,
        "_scene_count_after_truncation": len(scenes),
        "_truncation_reason": _trunc_reason if _was_truncated else "",
        "_disallowed_by_scene_structure": _is_disallowed,
        "prompt_length": len(prompt),
        "scenes_count": len(scenes),
        # Task 100c: 上下文压力指标
        "context_pressure": getattr(context_package, "context_pressure", {}) or {},
        "creative_brief_snapshot": _build_creative_brief_snapshot(context_package),
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
        # 新草稿使旧 accepted 版本失效，避免 dangling FK
        head.accepted_version_id = None
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

