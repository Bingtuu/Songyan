"""Task 171c: 确定性 exposition 后处理变换（杠杆候选，content-preserving）.

这是 171c "确定性后处理 rewrite" 杠杆的**最保守实现**：只在句子边界处把过长的
说明性对白引语（`info_delivery_dialogue` 检测器命中的 ≥N 字引语）拆成相邻的多段
短引语。**只改标点（拆引号），不增删任何字**，因此 content-preserving。

设计意图是作为杠杆的"最好情况"基线：若连这种零内容损失的结构拆分都只能"把命中数
压下去而不改善实际行文"（Goodhart），则说明确定性后处理不是有效杠杆。本模块因此
既是候选实现、也是可证伪实验的探针。**不调用 LLM。**
"""

from __future__ import annotations

import re

# 与 rule_auditor.info_delivery_dialogue_re 同源的长引语判定阈值。
_LONG_QUOTE_MIN_CHARS = 50
# 成对引号（方向性，避免跨对话轮拼接），捕获引语内容。
_QUOTE_RE = re.compile(r'(["“])([^"“”]{1,800})(["”])')
# 句子终止符（保留在前半句尾）。
_SENT_END = "。！？…"


def _split_long_quote_body(body: str, open_q: str, close_q: str) -> str | None:
    """把一段长引语内容按句子边界拆成相邻短引语；无法安全拆分时返回 None.

    仅当引语含 ≥2 个句子、且拆分后每段非空时才拆。只改引号标点，字全保留。
    例：``"A。B。C。"`` -> ``"A。""B。""C。"``（不插入任何叙述）。
    """
    # 在句子终止符后切分，保留终止符。
    parts = re.findall(rf"[^{_SENT_END}]*[{_SENT_END}]+", body)
    remainder = body[sum(len(p) for p in parts):]
    if remainder.strip():
        parts.append(remainder)
    parts = [p for p in parts if p.strip()]
    if len(parts) < 2:
        return None
    return "".join(f"{open_q}{p}{close_q}" for p in parts)


def split_long_expository_quotes(
    text: str,
    *,
    min_chars: int = _LONG_QUOTE_MIN_CHARS,
) -> tuple[str, int]:
    """把超过 min_chars 的多句引语拆成相邻短引语（content-preserving）.

    Returns:
        (变换后文本, 实际拆分的引语数)。无可拆引语时原样返回、计数 0。
    """
    split_count = 0

    def _repl(m: re.Match[str]) -> str:
        nonlocal split_count
        open_q, body, close_q = m.group(1), m.group(2), m.group(3)
        if len(body) < min_chars:
            return m.group(0)
        rebuilt = _split_long_quote_body(body, open_q, close_q)
        if rebuilt is None:
            return m.group(0)
        split_count += 1
        return rebuilt

    return _QUOTE_RE.sub(_repl, text), split_count
