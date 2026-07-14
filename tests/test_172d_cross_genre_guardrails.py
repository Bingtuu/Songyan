"""Task 172d: cross-genre literary guardrail lexicon + protagonist name.

Proves the guardrail is no longer sci-fi-hardcoded:
- xuanhuan lexicon detects a xuanhuan-style active choice that the sci-fi
  default lexicon would MISS (the core bug: xuanhuan chapters falsely judged
  MISSING because the observer looked for 按下/启动/林渊).
- sci-fi fallback (empty genre lexicon) preserves old behavior.
- protagonist_name is required (no "林渊" default).
"""

from __future__ import annotations

import inspect

from songyan.evals.literary_guardrail_observe import (
    GuardrailLexicon,
    observe_active_choice,
    observe_supporting_character_goal,
)
from songyan.genres.loader import load_genre_profile


def test_protagonist_name_has_no_default() -> None:
    # 172d: 主角名不再有 "林渊" 硬编码默认
    sig = inspect.signature(observe_active_choice)
    assert sig.parameters["protagonist_name"].default is inspect.Parameter.empty


def test_scifi_default_lexicon_matches_legacy_behavior() -> None:
    # 空 genre lexicon -> 回退科幻默认组；科幻正文仍能命中
    scifi_profile = load_genre_profile("scifi")
    lex = GuardrailLexicon.from_genre_profile(scifi_profile)
    obs = observe_active_choice(
        "林渊主动切断供能，代价是暴露位置。", "林渊", lexicon=lex
    )
    assert obs.passed
    assert obs.cost_evidence


def test_xuanhuan_lexicon_detects_xuanhuan_active_choice() -> None:
    xuanhuan_profile = load_genre_profile("xuanhuan")
    lex = GuardrailLexicon.from_genre_profile(xuanhuan_profile)
    # 玄幻主动选择：闭关 + 折寿代价。用玄幻主角名。
    text = "萧焱决定闭关冲击境界，代价是折寿三十年也在所不惜。"
    obs = observe_active_choice(text, "萧焱", lexicon=lex)
    assert obs.passed, "xuanhuan lexicon should detect 闭关 as active choice"
    assert obs.cost_evidence, "折寿 should be recognized as cost"


def test_scifi_lexicon_would_miss_xuanhuan_choice() -> None:
    # 关键回归证明：用科幻默认 lexicon 判定玄幻正文 -> MISSING（这正是 172d 修复的 bug）
    scifi_lex = GuardrailLexicon()  # 科幻默认组
    text = "萧焱闭关冲击境界，折寿三十年。"
    obs = observe_active_choice(text, "萧焱", lexicon=scifi_lex)
    # 科幻 lexicon 没有 "闭关"，且无 "主动/选择/决定" 等词 -> 判定 MISSING
    assert not obs.passed


def test_xuanhuan_supporting_goal_with_genre_lexicon() -> None:
    xuanhuan_profile = load_genre_profile("xuanhuan")
    lex = GuardrailLexicon.from_genre_profile(xuanhuan_profile)
    text = "青玄真人拒绝交出法宝，迫使萧焱改变路线，付出不小代价。"
    obs = observe_supporting_character_goal(
        text, {"character": "青玄真人", "goal": "夺取法宝"}, lexicon=lex
    )
    assert obs.character_present
    assert obs.action_evidence
    assert obs.passed


def test_lexicon_from_none_is_scifi_default() -> None:
    lex = GuardrailLexicon.from_genre_profile(None)
    assert "按下" in lex.active_verbs  # 科幻默认词
