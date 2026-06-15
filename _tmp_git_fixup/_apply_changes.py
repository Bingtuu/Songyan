import pathlib

fp = pathlib.Path(r'c:\Vibe Project\Songyan\src\songyan\workflows\_nodes.py')
content = fp.read_text(encoding='utf-8')

# 1. Import
old = 'from songyan.models import (\n    ChapterHead,\n    ChapterVersion,\n    HumanInstruction,\n    ReviewIssue,\n)'
new = 'from songyan.models import (\n    ChapterHead,\n    ChapterSummary,\n    ChapterVersion,\n    HumanInstruction,\n    ReviewIssue,\n)'
if old in content:
    content = content.replace(old, new)
    print('[OK] Import')
else:
    print('[SKIP] Import')

# 2. settlement_extractor_node
old = '''async def settlement_extractor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "settlement_extractor"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None

    # 067: 加载 chapter_goal 以按需过滤 genre_rules
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))

    settlement = None
    settlement_needs_review = False

    # 1. 提取并应用 settlement（核心操作）
    try:
        settlement = await extract_settlement(
            content=version.content,
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_id=version.version_id,
            genre_rules=_build_genre_rules(genre, project, goal) if genre else None,
        )
        async with get_db() as conn:
            await apply_settlement(
                settlement=settlement,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                version_id=version.version_id,
                conn=conn,
            )
            await conn.commit()
        if settlement is not None:
            logger.info(
                "settlement_extractor_node.settlement_applied",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                version_id=version.version_id,
                character_updates=len(settlement.character_updates),
                new_settings=len(settlement.new_settings),
                foreshadowing_updates=len(settlement.foreshadowing_updates),
                numerical_updates=len(settlement.numerical_updates),
            )
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "settlement_extractor_node.settlement_failed_needs_review",
            error=str(exc),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        settlement_needs_review = True

    # V4.0: 生命周期清理 — 统一调度所有表的 archive 策略（Task 087）
    await _run_lifecycle_cleanup(state["project_id"], state["chapter_number"])

    # 2. 生成章节摘要（非阻塞：失败不导致 settlement 回滚）
    summary_id = None
    if settlement is not None:
        try:
            await write_chapter_summary(
                content=version.content,
                settlement=settlement,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                db=SummaryRepository(),
            )
            summary_id = new_id("sum")
        except (LLMError, LLMResponseParseError) as exc:
            logger.warning(
                "settlement_extractor_node.summary_failed",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )'''

new = '''async def settlement_extractor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "settlement_extractor"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None

    # 067: 加载 chapter_goal 以按需过滤 genre_rules
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))

    settlement = None
    settlement_needs_review = False

    # Task 108: 支持跳过 settlement（如 convergence_failed 路径）
    if state.get("_skip_settlement", False):
        logger.info(
            "settlement_extractor_node.skipping_settlement",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_id=version.version_id,
        )
        # Fallback inline summary
        summary_id = new_id("sum")
        _content = version.content
        _summary_text = _content[:300] + "..." if len(_content) > 300 else _content
        fallback_summary = ChapterSummary(
            summary=_summary_text,
            chapter_number=state["chapter_number"],
            key_events=[],
            characters_appeared=[],
            emotional_tone="",
            impact_score=0.0,
        )
        try:
            await SummaryRepository().create(fallback_summary, state["project_id"], summary_id)
        except Exception as exc:
            logger.warning(
                "settlement_extractor_node.fallback_summary_failed",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            summary_id = None

        # V4.0: 生命周期清理（无条件执行）
        await _run_lifecycle_cleanup(state["project_id"], state["chapter_number"])
    else:
        # 1. 提取并应用 settlement（核心操作）
        try:
            settlement = await extract_settlement(
                content=version.content,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                version_id=version.version_id,
                genre_rules=_build_genre_rules(genre, project, goal) if genre else None,
            )
            async with get_db() as conn:
                await apply_settlement(
                    settlement=settlement,
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_id=version.version_id,
                    conn=conn,
                )
                await conn.commit()
            if settlement is not None:
                logger.info(
                    "settlement_extractor_node.settlement_applied",
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_id=version.version_id,
                    character_updates=len(settlement.character_updates),
                    new_settings=len(settlement.new_settings),
                    foreshadowing_updates=len(settlement.foreshadowing_updates),
                    numerical_updates=len(settlement.numerical_updates),
                )
        except (LLMError, LLMResponseParseError) as exc:
            logger.warning(
                "settlement_extractor_node.settlement_failed_needs_review",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            settlement_needs_review = True

        # V4.0: 生命周期清理 — 统一调度所有表的 archive 策略（Task 087）
        await _run_lifecycle_cleanup(state["project_id"], state["chapter_number"])

        # 2. 生成章节摘要（非阻塞：失败不导致 settlement 回滚）
        summary_id = None
        if settlement is not None:
            try:
                await write_chapter_summary(
                    content=version.content,
                    settlement=settlement,
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    db=SummaryRepository(),
                )
                summary_id = new_id("sum")
            except (LLMError, LLMResponseParseError) as exc:
                logger.warning(
                    "settlement_extractor_node.summary_failed",
                    error=str(exc),
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                )'''

if old in content:
    content = content.replace(old, new)
    print('[OK] settlement_extractor_node')
else:
    print('[SKIP] settlement_extractor_node')

# 3. rewrite_node
old = '''    # 重置 revision 状态，标记已重写
    return {
        "current_version_id": version.version_id,
        "revision_round": 0,
        "_was_rewritten": True,
        "_rewrite_reason": "2轮revision不收敛",
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
        "status": "rule_auditing",
    }'''
new = '''    # 重置 revision 状态，标记已重写
    return {
        "current_version_id": version.version_id,
        "revision_round": 0,
        "_was_rewritten": True,
        "_rewrite_reason": "2轮revision不收敛",
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
        "_best_version_id": version.version_id,
        "_best_score_card": None,
        "status": "rule_auditing",
    }'''
if old in content:
    content = content.replace(old, new)
    print('[OK] rewrite_node')
else:
    print('[SKIP] rewrite_node')

# 4. review_merger_node literary
old = '''    # 使用 score_card flags 作为 needs_revision 的增强判定（优先）
    needs_revision = score_card.flags.needs_revision
    has_critical = score_card.flags.coherence_critical
    has_major = score_card.flags.coherence_major'''
new = '''    # 使用 score_card flags 作为 needs_revision 的增强判定（优先）
    needs_revision = score_card.flags.needs_revision
    has_critical = score_card.flags.coherence_critical
    has_major = score_card.flags.coherence_major

    # Task 108: 合并 literary auditor 的 revision 需求
    literary_needs_revision = state.get("_needs_revision", False)
    needs_revision = needs_revision or literary_needs_revision'''
if old in content:
    content = content.replace(old, new)
    print('[OK] review_merger_node literary')
else:
    print('[SKIP] review_merger_node literary')

# 5. review_merger_node best_save
old = '''    if needs_revision and rround == 0:
        result["_best_issues_count"] = current_issues
        result["_best_overall_score"] = current_score
        result["_best_version_id"] = version.version_id
        result["_best_report_id"] = report_id
        result["_best_score_card"] = score_card.model_dump()
    return result'''
new = '''    if (needs_revision and rround == 0) or (state.get("_best_score_card") is None and version.version_id):
        result["_best_issues_count"] = current_issues
        result["_best_overall_score"] = current_score
        result["_best_version_id"] = version.version_id
        result["_best_report_id"] = report_id
        result["_best_score_card"] = score_card.model_dump()
    return result'''
if old in content:
    content = content.replace(old, new)
    print('[OK] review_merger_node best_save')
else:
    print('[SKIP] review_merger_node best_save')

# 6. human_gate_node
old = '''    if decision == "accept":
        # Task 098: Accept 路径字数守卫
        goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
        _rround = state.get("revision_round", 0)
        _was_rewritten = state.get("_was_rewritten", False)
        if goal and goal.word_count_target > 0 and _rround < 2 and not _was_rewritten:
            _ratio = version.word_count / goal.word_count_target
            if _ratio > 1.40:
                logger.warning(
                    "human_gate.word_count_guard_triggered",
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    word_count=version.word_count,
                    target=goal.word_count_target,
                    ratio=round(_ratio, 3),
                    revision_round=_rround,
                )
                return {
                    "human_decision": "word_count_guard",
                    "human_instructions": existing_instructions,
                    "_revision_rebound": state.get("_revision_rebound", False),
                    "status": "rewrite",
                }

        await ChapterHeadRepository().update('''
new = '''    if decision == "accept":
        await ChapterHeadRepository().update('''
if old in content:
    content = content.replace(old, new)
    print('[OK] human_gate_node')
else:
    print('[SKIP] human_gate_node')

# 7. _load_chapter_repair_state
old = 'revision_count = sum(1 for version in versions if version.version_type == "revision")'
new = 'revision_count = sum(1 for version in versions if version.version_type == "revision" and not version.is_abandoned)'
if old in content:
    content = content.replace(old, new)
    print('[OK] _load_chapter_repair_state')
else:
    print('[SKIP] _load_chapter_repair_state')

fp.write_text(content, encoding='utf-8')
print('Saved.')
