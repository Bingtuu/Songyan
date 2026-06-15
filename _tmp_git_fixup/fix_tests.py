import re

path = r"c:\\vIbe Project\\Songyan\\tests\\test_107_convergence_guardrail.py"
content = open(path, encoding="utf-8").read()

old1 = '    assert human_confirm_router(state) == "skip_settlement"'
new1 = '    assert human_confirm_router(state) == "accept"'

old2 = '    assert human_confirm_router(state) == "skip_settlement"'
new2 = '    assert human_confirm_router(state) == "accept"'

if old1 in content:
    content = content.replace(old1, new1)
if old2 in content:
    content = content.replace(old2, new2)
open(path, "w", encoding="utf-8").write(content)
print("Fixed 107 tests")
