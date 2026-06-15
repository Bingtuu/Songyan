"""Tests for hook detection."""

from __future__ import annotations

from songyan.utils.hook_checker import (
    check_ending_hook,
    check_hooks_with_timing,
    check_opening_hook,
)


class TestCheckOpeningHook:
    """Tests for check_opening_hook."""

    def test_empty_text(self) -> None:
        assert check_opening_hook("") is False

    def test_pure_environment_no_hook(self) -> None:
        text = "天朗气清，惠风和畅。远处的山峦在晨雾中若隐若现。"
        assert check_opening_hook(text) is False

    def test_character_presence_has_hook(self) -> None:
        text = "他突然停下脚步，冷冷地看着前方。"
        assert check_opening_hook(text) is True

    def test_dialogue_has_hook(self) -> None:
        text = '"你确定要这么做？"他问道，语气中带着一丝不安。'
        assert check_opening_hook(text) is True

    def test_action_verb_has_hook(self) -> None:
        text = "杀！一声令下，刀光剑影。"
        assert check_opening_hook(text) is True

    def test_sudden_event_has_hook(self) -> None:
        text = "突然，一道黑影从天而降。"
        assert check_opening_hook(text) is True

    def test_no_pronoun_no_action_no_hook(self) -> None:
        text = "清晨的阳光洒在山谷中，鸟儿在枝头歌唱。微风拂过，带来一丝凉意。"
        assert check_opening_hook(text) is False

    def test_custom_check_length(self) -> None:
        # Each block is ~24 chars, 15 blocks = 360 chars of pure environment
        env = "天朗气清，惠风和畅，远处的山峦在晨雾中若隐若现。"
        text = env * 15 + "他突然停下脚步。"
        # Default 300 chars should hit only the environment part (first 360)
        assert check_opening_hook(text) is False
        # If we extend check_length to cover the action part, it returns True
        assert check_opening_hook(text, check_length=400) is True


class TestCheckEndingHook:
    """Tests for check_ending_hook."""

    def test_empty_text(self) -> None:
        assert check_ending_hook("") is False

    def test_question_mark_has_hook(self) -> None:
        text = "他究竟能否逃过这一劫？"
        assert check_ending_hook(text) is True

    def test_exclamation_has_hook(self) -> None:
        text = "大事不好！"
        assert check_ending_hook(text) is True

    def test_twist_word_has_hook(self) -> None:
        text = "然而，他不知道的是，更大的危机正在逼近。"
        assert check_ending_hook(text) is True

    def test_future_time_has_hook(self) -> None :
        text = "等着吧，明天就是决战之日。"
        assert check_ending_hook(text) is True

    def test_unresolved_state_has_hook(self) -> None:
        text = "真相还未浮出水面。"
        assert check_ending_hook(text) is True

    def test_plain_ending_no_hook(self) -> None:
        text = "他们一起回到了住处，各自休息。"
        assert check_ending_hook(text) is False

    def test_ellipsis_has_hook(self) -> None:
        text = "他缓缓闭上眼睛……"
        assert check_ending_hook(text) is True

    def test_question_word_has_hook(self) -> None:
        text = "这一切究竟是怎么回事？"
        assert check_ending_hook(text) is True


class TestCheckHooksWithTiming:
    """Performance tests for hook checking."""

    def test_performance_under_20ms(self) -> None:
        text = "他突然停下脚步。" * 100 + "他究竟能否逃过这一劫？"
        opening, ending, elapsed = check_hooks_with_timing(text)
        assert elapsed < 20, f"Hook checking took {elapsed}ms, expected < 20ms"
