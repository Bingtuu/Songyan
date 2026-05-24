"""Hook detection — opening and ending hook quality checks."""

from __future__ import annotations

import re
import time

# Characters that signal an attractive opening event
_OPENING_INDICATORS = re.compile(
    r"[他她我你这那]"  # pronouns → character presence
    r"|[跑跳打杀追逃喊叫骂哭笑怒恨怕疼死伤战斗突破修炼]"  # action verbs
    r"|[\"\"''「『]"  # dialogue markers
    r"|[突然猛然陡然刹那间]"  # sudden events
)

# Characters that signal a悬念 at the end
_ENDING_INDICATORS = re.compile(
    r"[\?？！…]"  # suspense / exclamation punctuation
    r"|但是|然而|没想到|不料|谁知|岂料|只是"  #转折
    r"|明天|下次|将来|以后|等着|拭目以待|日后|未来|即将"  # future time
    r"|没有|还未|尚未|等待|悬念|未知|谜团|真相|秘密|谜底"  # unresolved
    r"|究竟|到底|难道|莫非|是否|会不会|能否|能不能"  # question words
)

# Pure-environment description markers (negative signal for opening)
_ENVIRONMENT_ONLY = re.compile(
    r"^(?:天|地|山|水|风|云|雨|雪|日|月|星|空|光|色|气|雾|霜|露|雷|电|河|海|林|"
    r"草|花|树|石|城|宫|殿|阁|朗|清|晨|暮|朝|夕|春|夏|秋|冬|暖|凉|冷|热)+"
    r"[，,。！？\s]*$"
)


def _first_n_chars(text: str, n: int) -> str:
    """Return the first *n* characters, counting CJK as 1 char each."""
    # For Chinese text len() works fine because Python str is Unicode codepoints
    return text[:n]


def _last_n_chars(text: str, n: int) -> str:
    """Return the last *n* characters."""
    return text[-n:] if len(text) >= n else text


def check_opening_hook(text: str, check_length: int = 300) -> bool:
    """Return ``True`` if the first *check_length* chars contain a hook.

    A hook is detected when the opening contains at least one of:
    - a pronoun (character presence)
    - an action verb
    - dialogue
    - a sudden-event marker

    If the opening consists only of environment description without
    any of the above, it is considered hook-less.

    Complexity: O(check_length) — < 10 ms for 300 chars.
    """
    opening = _first_n_chars(text, check_length)
    if not opening:
        return False

    # Must contain at least one indicator
    has_indicator = bool(_OPENING_INDICATORS.search(opening))
    if not has_indicator:
        return False

    # If it's purely environment description, still no hook
    # Remove punctuation and check
    cleaned = re.sub(r"[，,。！？\s\"\"''「『」』]", "", opening)
    if _ENVIRONMENT_ONLY.match(cleaned):
        return False

    return True


def check_ending_hook(text: str, check_length: int = 200) -> bool:
    """Return ``True`` if the last *check_length* chars contain a hook.

    A hook is detected when the ending contains at least one of:
    - suspense / exclamation punctuation
    - a转折 word
    - a future-time word
    - an unresolved-state word
    - a question word

    Complexity: O(check_length) — < 10 ms for 200 chars.
    """
    ending = _last_n_chars(text, check_length)
    if not ending:
        return False

    return bool(_ENDING_INDICATORS.search(ending))


def check_hooks_with_timing(text: str) -> tuple[bool, bool, int]:
    """Run both hook checks and return ``(opening, ending, elapsed_ms)``."""
    start = time.perf_counter()
    opening = check_opening_hook(text)
    ending = check_ending_hook(text)
    elapsed = int((time.perf_counter() - start) * 1000)
    return opening, ending, elapsed
