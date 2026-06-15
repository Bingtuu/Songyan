"""Generic name detection — 检测小说中的通用/敷衍角色名."""

from __future__ import annotations

import re

from songyan.models import GenericNameMatch

# 常见中文姓氏
COMMON_SURNAMES = {
    "张", "王", "李", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "林", "何", "高", "罗",
    "郑", "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹",
    "彭", "曾", "肖", "田", "董", "袁", "潘", "于", "蒋", "蔡",
    "余", "杜", "叶", "程", "苏", "魏", "吕", "丁", "任", "沈",
}

# 常见职业/称谓
COMMON_TITLES = {
    "经理", "主任", "医生", "护士", "警察", "保安", "教授", "老师",
    "司机", "服务员", "老板", "员工", "同事", "客户", "领导",
    "军官", "士兵", "律师", "记者", "工程师", "技师", "厨师",
}

# 通用名正则模式
_GENERIC_NAME_PATTERNS = [
    # 小/老 + 姓氏
    rf"[小老]({'|'.join(COMMON_SURNAMES)})",
    # 姓氏 + 职业
    rf"({'|'.join(COMMON_SURNAMES)})({'|'.join(COMMON_TITLES)})",
    # 纯职业作为角色名（前后有引号或对话标记）
    rf"['\"]({'|'.join(COMMON_TITLES)})",
]

_GENERIC_NAME_RE = re.compile(
    "|".join(f"(?:{p})" for p in _GENERIC_NAME_PATTERNS),
    re.MULTILINE,
)

# 排除模式（这些不是角色名）
_EXCLUDE_RE = re.compile(
    r"小[心说心心里声时]"  # 小心、小说、心里、小声、小时 等
)


def detect_generic_names(text: str) -> list[GenericNameMatch]:
    """检测文本中的通用/敷衍角色名.

    检测以下模式：
    - 小/老 + 姓氏（如"小张"、"老王"）
    - 姓氏 + 职业（如"李经理"、"张医生"）
    - 纯职业称谓作为角色名（如对话中的"医生"）

    Args:
        text: 章节正文

    Returns:
        命中列表
    """
    matches: list[GenericNameMatch] = []
    seen: set[str] = set()

    for m in _GENERIC_NAME_RE.finditer(text):
        name = m.group(0)
        # 排除非角色名的模式
        if _EXCLUDE_RE.match(name):
            continue
        # 去重：同一名字只报告一次
        if name in seen:
            continue
        seen.add(name)

        # 估算位置（第几段）
        paragraph_num = text[: m.start()].count("\n\n") + 1
        location = f"第{paragraph_num}段"

        matches.append(
            GenericNameMatch(
                name=name,
                location=location,
                matched_text=text[max(0, m.start() - 10) : m.end() + 10],
            )
        )

    return matches
