"""Quality detection utilities for Songyan."""

from songyan.utils.ai_tells import detect_ai_tells, detect_ai_tells_with_timing
from songyan.utils.fatigue_words import (
    detect_fatigue_words,
    detect_fatigue_words_with_timing,
)
from songyan.utils.hook_checker import (
    check_ending_hook,
    check_hooks_with_timing,
    check_opening_hook,
)
from songyan.utils.numerical_validator import (
    validate_numerical_update,
    validate_numerical_updates,
    validate_numerical_updates_with_timing,
)
from songyan.utils.paragraph_rhythm import (
    RhythmScore,
    analyze_paragraph_rhythm,
    analyze_paragraph_rhythm_with_timing,
)

__all__ = [
    "detect_ai_tells",
    "detect_ai_tells_with_timing",
    "detect_fatigue_words",
    "detect_fatigue_words_with_timing",
    "check_opening_hook",
    "check_ending_hook",
    "check_hooks_with_timing",
    "analyze_paragraph_rhythm",
    "analyze_paragraph_rhythm_with_timing",
    "RhythmScore",
    "validate_numerical_update",
    "validate_numerical_updates",
    "validate_numerical_updates_with_timing",
]
