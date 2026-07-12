"""Task 171b: 对话密度分层工具（代表性样本方法论）.

把章节按"对话密度"分层，使 voice 只在能公平测量的层上评估（框架 §8 C1）。
密度信号与 RuleAuditor 的 voice 章级门同源（成对引号计数 / 每千字），
因此"分层口径 = 量具计分口径"。本模块只做分层判定，不改任何检测逻辑。
"""

from __future__ import annotations

# 密度阈值（成对引号数 / 每千字），由 171b 真实语料分布校准：
#   sparse   < 3.0  —— 单人解谜/意识流/纯叙事，无可比对白对，voice 不适用；
#   mixed   [3.0, 8.0) —— 有对白但夹叙述，voice 可测但样本量有限；
#   dialogue ≥ 8.0  —— 多角色密集对白，voice 评估主力。
SPARSE_MAX_DENSITY: float = 3.0
DIALOGUE_MIN_DENSITY: float = 8.0

DialogueLayer = str  # "sparse" | "mixed" | "dialogue"


def dialogue_density(char_count: int, quote_count: int) -> float:
    """成对引号数 / 每千字。char_count<=0 时返回 0.0（不崩）."""
    if char_count <= 0:
        return 0.0
    return quote_count / (char_count / 1000.0)


def classify_dialogue_layer(
    char_count: int,
    quote_count: int,
    *,
    sparse_max: float = SPARSE_MAX_DENSITY,
    dialogue_min: float = DIALOGUE_MIN_DENSITY,
) -> tuple[DialogueLayer, float]:
    """按对话密度返回 (层, 密度)。

    Args:
        char_count: 正文字符数。
        quote_count: 成对引号数（应使用 `_VOICE_QUOTE_RE` 计数，与量具同源）。
        sparse_max: 稀疏层上界（含）以下判 sparse。
        dialogue_min: 对话承载层下界（含）以上判 dialogue。

    Returns:
        (layer, density) —— layer ∈ {"sparse","mixed","dialogue"}。
    """
    density = dialogue_density(char_count, quote_count)
    if density < sparse_max:
        return "sparse", density
    if density >= dialogue_min:
        return "dialogue", density
    return "mixed", density


def is_voice_applicable(layer: DialogueLayer) -> bool:
    """voice 是否应在该层计分：稀疏层不计分（对治样本错配）."""
    return layer != "sparse"
