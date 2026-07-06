"""Task 170d: LiteraryAuditor 校准（character_autonomy 锚点 rubric）.

校准是 prompt 侧改动，真实收敛以 LLM 回测（scripts/backtest_170d_auditor_calibration.py）为准。
本单测锁定两件确定性的事：
  1. 工艺卡 1.0.2 的锚点契约存在（rubric 分档 + 遮标签测试 + 高分需证据约束）。
  2. 解析路径正确：LLM 若按 rubric 给低分（对白同质→低档），结果如实落库、不被上抬。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from songyan.agents.literary_auditor import run_literary_audit
from songyan.prompts import get_prompt_loader


class TestCard102AnchorContract:
    """校准后工艺卡必须包含锚点 rubric，且为默认版本."""

    def test_default_version_is_1_0_2(self) -> None:
        card = get_prompt_loader().load_card("literary_auditor")
        assert card.metadata.version == "1.0.2"

    def test_character_autonomy_rubric_has_three_bands(self) -> None:
        prompt = get_prompt_loader().load_card("literary_auditor").system_prompt
        # 三档锚点齐全
        assert "1-3（低档，塌陷）" in prompt
        assert "4-6（中档）" in prompt
        assert "7-10（高档）" in prompt

    def test_has_mask_the_speaker_test(self) -> None:
        prompt = get_prompt_loader().load_card("literary_auditor").system_prompt
        # "遮住说话人标签" 的判定测试是校准核心
        assert "遮住" in prompt

    def test_high_score_requires_evidence_constraint(self) -> None:
        prompt = get_prompt_loader().load_card("literary_auditor").system_prompt
        # 规则 9：高分需证据，同质必落低档 + polyphony_weakness
        assert "polyphony_weakness" in prompt
        assert "对白同质" in prompt

    def test_all_four_scores_have_rubric(self) -> None:
        prompt = get_prompt_loader().load_card("literary_auditor").system_prompt
        for anchor in (
            "character_autonomy_score（",
            "literary_quality_score（",
            "conceptual_grounding_score（",
            "fissure_preservation_score（",
        ):
            assert anchor in prompt, anchor


def _resp(scores: dict[str, float], observations: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "observations": observations or [],
            "literary_quality_score": scores.get("literary_quality", 5.0),
            "character_autonomy_score": scores.get("character_autonomy", 5.0),
            "conceptual_grounding_score": scores.get("conceptual_grounding", 5.0),
            "fissure_preservation_score": scores.get("fissure_preservation", 5.0),
            "summary": "test",
        }
    )


class TestParsePreservesRubricScores:
    """解析路径不上抬 LLM 的低分——校准要生效必须如实透传."""

    async def test_same_voice_low_autonomy_is_preserved(self) -> None:
        # 模拟按 rubric：对白同质 → character_autonomy 落低档 2.0
        resp = _resp(
            {"character_autonomy": 2.0},
            observations=[
                {
                    "observation_id": "obs_001",
                    "observation_type": "polyphony_weakness",
                    "description": "全员冷静解说腔，遮标签认不出说话人",
                    "evidence_quote": "……",
                    "severity": "suggestion",
                    "recommendation": "赋予个体语气",
                    "preserve": False,
                }
            ],
        )
        with patch(
            "songyan.agents.literary_auditor.call_llm",
            new=AsyncMock(return_value=resp),
        ):
            result = await run_literary_audit("对白同质的正文……")

        assert result.character_autonomy_score == 2.0
        assert any(o.observation_type == "polyphony_weakness" for o in result.observations)

    async def test_distinct_voice_high_autonomy_is_preserved(self) -> None:
        resp = _resp({"character_autonomy": 8.0})
        with patch(
            "songyan.agents.literary_auditor.call_llm",
            new=AsyncMock(return_value=resp),
        ):
            result = await run_literary_audit("对白可辨身份的正文……")

        assert result.character_autonomy_score == 8.0
