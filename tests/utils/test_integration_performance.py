"""Integration performance test — total elapsed time for all quality utils."""

from __future__ import annotations

import time

from songyan.models.settlement import Increment, NumericalUpdate
from songyan.utils import (
    analyze_paragraph_rhythm,
    check_ending_hook,
    check_opening_hook,
    detect_ai_tells,
    detect_fatigue_words,
    validate_numerical_update,
)


class TestIntegrationPerformance:
    """Verify that running all quality checks together stays under 200 ms."""

    def test_all_checks_total_under_200ms(self) -> None:
        """Run every util on a realistic chapter and assert total < 200 ms."""
        text = (
            "他突然停下脚步，冷冷地看着前方。眼中闪过一丝寒芒，\n"
            "嘴角勾起一抹弧度。废物，跪地求饶吧。\n"
            '\u201c这是一个段落。\u201d他又说道。\u201c我们走吧。\u201d\n'
            "接下来是另一个叙述段落，同样保持在合适的篇幅范围内，"
            "让读者能够顺畅地阅读下去，不会感到疲劳或断裂不适。\n"
            '\u201c那接下来怎么办？\u201d有人问道。\u201c先休息吧。\u201d\n'
            "第三个叙述段落也同样保持合适的篇幅，"
            "内容充实且节奏稳定，让读者能够沉浸其中。\n"
            '\u201c我也不知道。\u201d另一个人回答，\u201c但总要试试。\u201d\n'
            "最后一个叙述段落收尾，保持与前文一致的篇幅和节奏，"
            "让整章内容显得完整而连贯，没有突兀的断裂感。\n"
            "他究竟能否逃过这一劫？"
        )
        fatigue_words = [
            "冷笑",
            "废物",
            "嘴角勾起一抹弧度",
            "跪地求饶",
            "此子不可留",
        ]
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="cultivation_level",
            opening_value=100.0,
            increments=[Increment(amount=10.0, source="breakthrough", source_quote="突破了")],
            closing_value=110.0,
        )

        start = time.perf_counter()

        detect_ai_tells(text)
        detect_fatigue_words(text, fatigue_words)
        check_opening_hook(text)
        check_ending_hook(text)
        analyze_paragraph_rhythm(text)
        validate_numerical_update(update)

        elapsed = int((time.perf_counter() - start) * 1000)

        assert elapsed < 200, (
            f"All quality checks took {elapsed}ms total, expected < 200ms"
        )
