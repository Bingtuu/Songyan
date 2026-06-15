path = r'c:\Vibe Project\Songyan\src\songyan\workflows\phase1_graph.py'
content = open(path, 'r', encoding='utf-8').read()

# Edit 1: Add _best_score_card to TypedDict
content = content.replace(
    '    _best_report_id: str | None\n    _current_issues_count: int | None',
    '    _best_report_id: str | None\n    _best_score_card: dict | None\n    _current_issues_count: int | None'
)

# Edit 2: Remove _skip_settlement special branch
content = content.replace(
    '    decision = state.get("human_decision")\n    # Task 107: 收敛失败时跳过 settlement\n    if (decision == "accept" or decision is None) and state.get("_skip_settlement"):\n        return "skip_settlement"\n    if decision == "accept" or decision is None:',
    '    decision = state.get("human_decision")\n    if decision == "accept" or decision is None:'
)

# Edit 3: revision_router use state
content = content.replace(
    '    # 073: 2 轮不收敛 → 触发整章重写（最多 1 次）\n    if needs and rround >= _MAX_REVISION_ROUNDS:\n        return "rewrite"\n\n    if needs and rround < _MAX_REVISION_ROUNDS:\n        return "revise"',
    '    # 073: 2 轮不收敛 → 触发整章重写（最多 1 次）\n    max_r = state.get("_max_revision_rounds", 2)\n    if needs and rround >= max_r:\n        return "rewrite"\n\n    if needs and rround < max_r:\n        return "revise"'
)

# Edit 4: run_chapter_pipeline signature
content = content.replace(
    'async def run_chapter_pipeline(\n    project_id: str,\n    chapter_number: int,\n    mode_id: str = "webnovel",\n    thread_id: str | None = None,\n    previous_summary: str = "",\n) -> Phase1State:',
    'async def run_chapter_pipeline(\n    project_id: str,\n    chapter_number: int,\n    mode_id: str = "webnovel",\n    thread_id: str | None = None,\n    previous_summary: str = "",\n    max_revision_rounds: int = 2,\n) -> Phase1State:'
)

# Edit 5: initial_state _max_revision_rounds
content = content.replace(
    '        "_score_card": None,\n        "_convergence_failed": False,\n        "_skip_settlement": False,\n    }',
    '        "_score_card": None,\n        "_convergence_failed": False,\n        "_skip_settlement": False,\n        "_max_revision_rounds": max_revision_rounds,\n    }'
)

open(path, 'w', encoding='utf-8').write(content)
print('Done')
