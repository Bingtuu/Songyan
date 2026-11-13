"""task 253：S5 人改率（tech-m4-followup-s5 §4）。

口径：变更行数（difflib opcodes 的 insert/delete + replace 双侧）/
max(源稿行数, 1)。所有权代理，不是文学分（PRD :200）；<5% 由调用方警告。
"""

from __future__ import annotations

import difflib


def compute_edit_ratio(source: str, edited: str) -> float:
    """行级人改率：0.0 = 纯复制，1.0 = 全重写。

    空源 + 非空稿 = 1.0（全新内容）；双方空 = 0.0。
    """
    source_lines = source.splitlines()
    edited_lines = edited.splitlines()
    if not source_lines and not edited_lines:
        return 0.0
    if not source_lines:
        return 1.0

    matcher = difflib.SequenceMatcher(None, source_lines, edited_lines)
    changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            changed += j2 - j1
        elif tag == "delete":
            changed += i2 - i1
        elif tag == "replace":
            changed += max(i2 - i1, j2 - j1)
    return min(1.0, changed / len(source_lines))
