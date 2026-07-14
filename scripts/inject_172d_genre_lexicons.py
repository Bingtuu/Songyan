"""172d: inject genre-specific literary guardrail lexicons into genres/*.json.

Idempotent: only sets the 5 lexicon fields, preserves all other content.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENRE_DIR = ROOT / "genres"

LEXICONS: dict[str, dict[str, list[str]]] = {
    "xuanhuan": {
        "active_verbs": [
            "主动", "选择", "决定", "拒绝", "闭关", "夺舍", "立誓", "破境",
            "祭炼", "斩", "出手", "结印", "布阵", "催动", "献祭", "舍弃",
        ],
        "passive_only_patterns": ["继续修炼", "继续参悟", "继续承受", "静待时机"],
        "cost_keywords": [
            "代价", "折寿", "道心受损", "根基受创", "因果", "反噬", "损耗",
            "走火入魔", "寿元", "不可逆",
        ],
        "supporting_action_keywords": [
            "拒绝", "坚持", "隐瞒", "阻止", "拦", "背叛", "夺", "抢", "献",
            "叛", "护", "追杀", "要挟", "迫使",
        ],
        "consequence_keywords": [
            "延迟", "改变路线", "结仇", "代价", "误判", "压力", "暴露",
            "失去", "反噬", "迫使",
        ],
    },
    "wuxia": {
        "active_verbs": [
            "主动", "选择", "决定", "拒绝", "出剑", "拔刀", "挑战", "退隐",
            "立誓", "断交", "闯", "闯入", "接招", "劫", "护",
        ],
        "passive_only_patterns": ["继续赶路", "继续养伤", "继续承受", "静观其变"],
        "cost_keywords": [
            "代价", "内伤", "断脉", "结仇", "背负", "名声", "受伤", "损耗",
            "不可逆", "血债",
        ],
        "supporting_action_keywords": [
            "拒绝", "坚持", "隐瞒", "阻止", "拦", "背叛", "追杀", "抢", "劫",
            "护", "叛", "要挟", "迫使", "带",
        ],
        "consequence_keywords": [
            "延迟", "改变路线", "结仇", "代价", "误判", "压力", "暴露",
            "失去", "迫使", "波及",
        ],
    },
    "urban": {
        "active_verbs": [
            "主动", "选择", "决定", "拒绝", "辞职", "摊牌", "举报", "签约",
            "断绝", "揭穿", "起诉", "反击", "放弃", "争取",
        ],
        "passive_only_patterns": ["继续等待", "继续隐忍", "继续承受", "维持现状"],
        "cost_keywords": [
            "代价", "失业", "名誉", "亏损", "决裂", "风险", "损失", "受伤",
            "不可逆", "把柄",
        ],
        "supporting_action_keywords": [
            "拒绝", "坚持", "隐瞒", "阻止", "拦", "背叛", "举报", "抢", "签",
            "揭穿", "要挟", "迫使", "带", "施压",
        ],
        "consequence_keywords": [
            "延迟", "改变计划", "决裂", "代价", "误判", "压力", "暴露",
            "失去", "迫使", "波及",
        ],
    },
}


def main() -> None:
    for genre, lexicon in LEXICONS.items():
        path = GENRE_DIR / f"{genre}.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for key, values in lexicon.items():
            data[key] = values
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"updated {path.name}: +{len(lexicon)} lexicon fields")


if __name__ == "__main__":
    main()
