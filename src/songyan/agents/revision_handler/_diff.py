"""RevisionHandler 模糊文本匹配 — difflib + 段落级回退."""

from __future__ import annotations

import difflib

import structlog

logger = structlog.get_logger(__name__)


def _difflib_fuzzy_search(
    text: str,
    target: str,
    issue_id: str = "",
    thresholds: tuple[float, ...] = (0.90, 0.85, 0.80),
) -> tuple[int, int] | None:
    """使用 difflib 进行多级 threshold 模糊搜索.

    策略：
    1. 先用大步长（target_len // 20）快速扫描找候选区域
    2. 在候选区域附近用小步长（1-2 字符）精确搜索
    3. 逐级降低 threshold 回退
    """
    target_len = len(target)
    if target_len == 0:
        return None

    for threshold in thresholds:
        best_ratio = 0.0
        best_start = -1

        # 阶段 A：大步长快速扫描，找候选区域
        coarse_step = max(1, target_len // 20)
        candidate_starts: list[int] = []
        for i in range(0, len(text) - target_len + 1, coarse_step):
            window = text[i : i + target_len]
            ratio = difflib.SequenceMatcher(None, target, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i
            if ratio >= threshold:
                candidate_starts.append(i)

        # 阶段 B：在候选区域附近细粒度搜索
        fine_step = 1
        search_radius = target_len  # 在候选位置前后各 target_len 范围内细搜
        search_starts = set(candidate_starts)
        if best_start != -1:
            search_starts.add(best_start)

        for cand_start in search_starts:
            start_range = max(0, cand_start - search_radius)
            end_range = min(len(text) - target_len + 1, cand_start + search_radius + 1)
            for i in range(start_range, end_range, fine_step):
                window = text[i : i + target_len]
                ratio = difflib.SequenceMatcher(None, target, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_start = i
                if best_ratio >= threshold:
                    break
            if best_ratio >= threshold:
                break

        if best_ratio >= threshold and best_start != -1:
            logger.info(
                "revision_handler.fuzzy_match",
                issue_id=issue_id,
                ratio=round(best_ratio, 3),
                threshold=threshold,
            )
            return (best_start, best_start + target_len)

    return None


def _paragraph_fallback_search(
    text: str,
    target: str,
    issue_id: str = "",
    min_paragraph_ratio: float = 0.70,
) -> tuple[int, int] | None:
    """段落级回退匹配：将 target 按段落分割，逐段查找最佳匹配.

    当整段文本无法匹配时，尝试按段落（\n\n 或 \n 分割）分别查找，
    如果主要段落都能找到较好的匹配，则返回整体匹配位置。

    Returns:
        (start, end) 如果足够比例的段落匹配成功，否则 None
    """
    if not target or not text:
        return None

    # 按段落分割 target
    paragraphs = [p.strip() for p in target.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        # 单段落无法匹配时，尝试按句子分割
        sentences = [s.strip() for s in target.split("。") if s.strip()]
        if len(sentences) <= 1:
            return None
        paragraphs = sentences

    matched_spans: list[tuple[int, int, float]] = []
    for para in paragraphs:
        if len(para) < 5:
            continue
        # 对每个段落用 difflib 找最佳匹配
        para_len = len(para)
        best_ratio = 0.0
        best_start = -1
        step = max(1, para_len // 20)
        for i in range(0, len(text) - para_len + 1, step):
            window = text[i : i + para_len]
            ratio = difflib.SequenceMatcher(None, para, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i
            if best_ratio >= min_paragraph_ratio:
                break
        if best_ratio >= min_paragraph_ratio and best_start != -1:
            matched_spans.append((best_start, best_start + para_len, best_ratio))

    # 需要至少 50% 的段落（至少 2 个）匹配成功
    if len(matched_spans) >= max(2, len(paragraphs) // 2):
        # 按匹配位置排序，取整体范围
        matched_spans.sort(key=lambda x: x[0])
        overall_start = matched_spans[0][0]
        overall_end = matched_spans[-1][1]
        avg_ratio = sum(s[2] for s in matched_spans) / len(matched_spans)
        logger.info(
            "revision_handler.paragraph_fallback_match",
            issue_id=issue_id,
            paragraphs_matched=len(matched_spans),
            total_paragraphs=len(paragraphs),
            avg_ratio=round(avg_ratio, 3),
        )
        return (overall_start, overall_end)

    return None
