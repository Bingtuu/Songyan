"""Task 110a: CharacterState 分层保真压缩测试."""

from __future__ import annotations

from songyan.agents.settlement_extractor._state_compression import (
    compress_character_state_value,
)


class TestStateCompression:
    """测试角色状态值的分层保真压缩."""

    def test_short_value_not_compressed(self) -> None:
        """短文本不应该被压缩."""
        value = "主角感到愤怒。"
        result = compress_character_state_value(value, "mental_state", "protagonist")
        assert result == value

    def test_location_not_compressed(self) -> None:
        """location 字段不应该被压缩."""
        value = "E-7 维护通道圆形大厅（靠近原始日志装置）"
        result = compress_character_state_value(value, "location", "supporting")
        assert result == value

    def test_protagonist_mental_state_compressed(self) -> None:
        """主角心理状态超长时保留关键句."""
        value = (
            "主角此刻心情非常复杂，脑海中不断闪过过去的种种画面。"
            "他意识到自己的处境已经十分危险，必须尽快找到出路。"
            "他决定不顾劝阻，独自深入探索未知区域，寻找真相。"
        )
        result = compress_character_state_value(value, "mental_state", "protagonist")
        # 应该包含状态和决策
        assert "决定" in result or "必须" in result or "意识到" in result
        assert len(result) <= 400

    def test_supporting_structured_compression(self) -> None:
        """配角心理状态被结构化压缩."""
        value = (
            "配角 A 一直沉浸在悲痛之中，无法接受眼前的现实。"
            "当他得知真相后，内心充满了愤怒和自责。"
            "他决定背叛原来的组织，投靠主角一方。"
        )
        result = compress_character_state_value(value, "mental_state", "supporting")
        assert len(result) <= 150
        # 应该保留关键转折
        assert "背叛" in result or "投靠" in result or "决定" in result

    def test_functional_minimal_compression(self) -> None:
        """功能性角色极度压缩."""
        value = (
            "这名守卫今天心情不错，正在岗位上打盹。"
            "他完全没有注意到有人潜入了走廊。"
        )
        result = compress_character_state_value(value, "mental_state", "functional")
        assert len(result) <= 60

    def test_physical_state_compression(self) -> None:
        """身体状态可压缩."""
        value = (
            "主角的左腿受了重伤，鲜血不断从伤口涌出。"
            "他咬紧牙关，忍着剧痛继续向前爬行。"
            "伤势严重影响了他的移动速度。"
        )
        result = compress_character_state_value(value, "physical_state", "protagonist")
        assert len(result) <= 400
        assert "重伤" in result or "伤势" in result or "移动" in result

    def test_fallback_truncation(self) -> None:
        """无法提取关键句时回退到截断."""
        # 无标点、无关键词的超长文本会走 fallback 截断
        value = "这是一段非常长的无意义重复文本" * 50
        result = compress_character_state_value(value, "mental_state", "supporting")
        assert len(result) <= 150
        assert result.endswith("...")
