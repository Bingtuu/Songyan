import re
path = r'c:\Vibe Project\Songyan\tests\test_106_scoring_system.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line 312 pattern
content = content.replace(
    '        best = ScoreAggregator.aggregate("v1", _make_rule_result(word_count=3000), _make_llm_result())',
    '        best = ScoreAggregator.aggregate(\n            "v1", _make_rule_result(word_count=3000), _make_llm_result()\n        )'
)

# Fix line 334 pattern  
content = content.replace(
    '        current = ScoreAggregator.aggregate("v2", _make_rule_result(), _make_llm_result(issues=issues))',
    '        current = ScoreAggregator.aggregate(\n            "v2", _make_rule_result(), _make_llm_result(issues=issues)\n        )'
)

# Fix line 303 pattern
content = content.replace(
    '        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(issues=issues), budget_used=0.85)',
    '        card = ScoreAggregator.aggregate(\n            "v1", rule, _make_llm_result(issues=issues), budget_used=0.85\n        )'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('done')
