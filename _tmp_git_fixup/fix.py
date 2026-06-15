import sys

file_path = 'src/songyan/workflows/phase1_graph.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old1 = (
    '    max_r = state.get(_max_revision_rounds, 2)\n'
    '    if needs and rround >= _MAX_REVISION_ROUNDS:\n\n\n'
    '    if needs and rround < _MAX_REVISION_ROUNDS:\n'
    '        return "revise"\n'
    '    return "pass"'
)
new1 = (
    '    max_r = state.get("_max_revision_rounds", _MAX_REVISION_ROUNDS)\n'
    '    if needs and rround >= max_r:\n'
    '        return "rewrite"\n'
    '    if needs and rround < max_r:\n'
    '        return "revise"\n'
    '    return "pass"'
)

if old1 in content:
    content = content.replace(old1, new1)
    print('Fixed revision_router')
else:
    print('revision_router pattern not found')

old2 = (
    'def human_confirm_router(state: Phase1State) -> str:\n'
    '    """human_confirm 后路由."""\n'
    '    if decision == "accept" or decision is None:'
)
new2 = (
    'def human_confirm_router(state: Phase1State) -> str:\n'
    '    """human_confirm 后路由."""\n'
    '    decision = state.get("human_decision")\n'
    '    if decision == "accept" or decision is None:'
)

if old2 in content:
    content = content.replace(old2, new2)
    print('Fixed human_confirm_router')
else:
    print('human_confirm_router pattern not found')

old3 = '        _max_revision_rounds: max_revision_rounds,'
new3 = '        "_max_revision_rounds": max_revision_rounds,'

if old3 in content:
    content = content.replace(old3, new3)
    print('Fixed initial state')
else:
    print('initial state pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
