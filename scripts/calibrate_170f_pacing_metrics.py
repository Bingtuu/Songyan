"""Task 170f Stage 0 校准脚本：验证候选 pacing/exposition 指标能否区分好/慢章.

只读、不改数据。从 170b 隔离 DB 读 Ch28-Ch40 accepted 正文，
算候选指标，对照 170b 第 5 节人工 pacing 终评分，做区分度判定：
指标能把"慢章(pacing<=2)"与"好章(pacing>=3)"分开才值得落为 RuleAuditor 检测项。

关键前提（亲读 170b 得到）：Ch28（人工 pacing=3，最佳）是短段密集动作章，
Ch33/39/40（pacing=2）是独白/日志堆叠——故"段落长度"不能naive判 pacing，
需验证 对白密度 / 最长连续非对白块 / 场景切换密度 / 认知动词独白比例。

用法:
    python scripts/calibrate_170f_pacing_metrics.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

# 强制隔离 DB（.tmp/），绝不读 .env 的 DATABASE_URL（指向主库）。
_db = os.getenv("CALIB_DB", ".tmp/task170b_ch1_ch40.db")
if not _db.startswith(".tmp/"):
    raise SystemExit(f"[safety] CALIB_DB 必须在 .tmp/ 下，拒绝: {_db}")
settings.database_url = f"sqlite:///{_db}"

from songyan.agents.rule_auditor import _split_scenes  # noqa: E402
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository  # noqa: E402
from songyan.utils._helpers import split_paragraphs  # noqa: E402
from songyan.utils.word_count import count_chinese_words  # noqa: E402

PROJECT_FILE = Path(".tmp/task170b_project.json")

# 170b 第 5 节人工 pacing 终评分（1=差 5=好）。好章(>=3): 28,33,34,36,37；慢章(<=2): 其余。
HUMAN_PACING = {
    28: 3, 29: 2, 30: 2, 31: 2, 32: 2, 33: 3, 34: 3,
    35: 2, 36: 3, 37: 3, 38: 2, 39: 2, 40: 2,
}

WINDOW = list(range(28, 41))

# 对白标记：中文引号 / 直角引号 / 英文引号。
_DIALOGUE_RE = re.compile(r"[“”\"「」]")
# 认知动词（内心独白信号）。
_COGNITION_WORDS = [
    "想", "记得", "意识到", "明白", "感觉", "回忆", "知道", "觉得",
    "心想", "记起", "想起", "察觉", "认为", "思考", "琢磨",
]


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
    return None


async def _load_content(project_id: str, chapter: int) -> str | None:
    head = await ChapterHeadRepository().get(project_id, chapter)
    if head is None or head.status != "accepted" or not head.accepted_version_id:
        return None
    version = await ChapterVersionRepository().get(head.accepted_version_id)
    return version.content if version else None


def _has_dialogue(paragraph: str) -> bool:
    return bool(_DIALOGUE_RE.search(paragraph))


def _dialogue_paragraph_ratio(paragraphs: list[str]) -> float:
    if not paragraphs:
        return 0.0
    d = sum(1 for p in paragraphs if _has_dialogue(p))
    return round(d / len(paragraphs), 3)


def _max_narration_run_chars(paragraphs: list[str]) -> int:
    """连续无对白段落的最大字数（越大 = 越长的纯叙述/说明块）."""
    best = 0
    cur = 0
    for p in paragraphs:
        if _has_dialogue(p):
            cur = 0
        else:
            cur += len(p)
            best = max(best, cur)
    return best


def _scene_switch_density(content: str, word_count: int) -> float:
    """场景数 / 千字."""
    scenes = len(_split_scenes(content))
    if word_count <= 0:
        return 0.0
    return round(scenes / (word_count / 1000), 3)


def _monologue_ratio(paragraphs: list[str]) -> float:
    """无对白 + 含认知动词段落占比（内心独白信号，噪声较大）."""
    if not paragraphs:
        return 0.0
    m = sum(
        1 for p in paragraphs
        if not _has_dialogue(p) and any(w in p for w in _COGNITION_WORDS)
    )
    return round(m / len(paragraphs), 3)


def _discrimination(good: list[float], slow: list[float], higher_is_better: bool) -> str:
    """判定指标区分度：好章均值 vs 慢章均值，方向是否符合预期 + 是否有间隔."""
    if not good or not slow:
        return "数据不足"
    gm, sm = mean(good), mean(slow)
    # higher_is_better=True 表示"值越高越好"（如对白密度、场景切换）
    good_hi = gm > sm
    aligned = good_hi == higher_is_better
    gap = abs(gm - sm)
    rel = gap / (abs(mean(good + slow)) + 1e-9)
    verdict = "✓ 可区分" if aligned and rel >= 0.15 else (
        "~ 弱区分" if aligned and rel >= 0.05 else "✗ 无区分/反向")
    return (
        f"好章均值={gm:.3f} 慢章均值={sm:.3f} "
        f"方向{'符' if aligned else '反'} 相对差={rel:.0%} → {verdict}"
    )


async def _amain() -> int:
    if not Path(_db).exists():
        print(f"[error] 隔离 DB 不存在: {_db}")
        return 1
    project_id = _resolve_project_id()
    if not project_id:
        print("[error] 无法解析 project_id")
        return 1

    print(f"[preflight] DB={settings.database_url}  project={project_id}")
    print(f"[preflight] 窗口 Ch{WINDOW[0]}-Ch{WINDOW[-1]}，人工 pacing 分见下表\n")

    metrics: dict[int, dict[str, float]] = {}
    header = (
        f"{'Ch':>3} {'pacing':>6} {'字数':>6} {'对白密度':>8} "
        f"{'最长说明块':>10} {'场景/千字':>9} {'独白比':>7}"
    )
    print(header)
    print("-" * len(header))
    for ch in WINDOW:
        content = await _load_content(project_id, ch)
        if not content:
            print(f"{ch:>3}  (无 accepted 正文)")
            continue
        paras = split_paragraphs(content)
        wc = count_chinese_words(content)
        m = {
            "pacing": HUMAN_PACING.get(ch, 0),
            "word_count": wc,
            "dialogue_paragraph_ratio": _dialogue_paragraph_ratio(paras),
            "max_narration_run_chars": _max_narration_run_chars(paras),
            "scene_switch_density": _scene_switch_density(content, wc),
            "monologue_ratio": _monologue_ratio(paras),
        }
        metrics[ch] = m
        print(f"{ch:>3} {m['pacing']:>6} {wc:>6} "
              f"{m['dialogue_paragraph_ratio']:>8.3f} {m['max_narration_run_chars']:>10} "
              f"{m['scene_switch_density']:>9.3f} {m['monologue_ratio']:>7.3f}")

    # 区分度判定：好章 pacing>=3 vs 慢章 pacing<=2
    good = {ch for ch, m in metrics.items() if m["pacing"] >= 3}
    slow = {ch for ch, m in metrics.items() if m["pacing"] <= 2}
    print(f"\n好章(pacing>=3): {sorted(good)}")
    print(f"慢章(pacing<=2): {sorted(slow)}")

    def col(name: str, chapters: set[int]) -> list[float]:
        return [metrics[ch][name] for ch in chapters if ch in metrics]

    print("\n" + "=" * 68)
    print("区分度判定（好章 vs 慢章）")
    print("=" * 68)
    checks = [
        ("dialogue_paragraph_ratio", True, "对白密度（慢章应更低）"),
        ("max_narration_run_chars", False, "最长说明块（慢章应更长）"),
        ("scene_switch_density", True, "场景切换密度（慢章应更低）"),
        ("monologue_ratio", False, "独白比例（慢章应更高）"),
    ]
    verdicts: dict[str, str] = {}
    for name, higher_better, label in checks:
        v = _discrimination(col(name, good), col(name, slow), higher_better)
        verdicts[name] = v
        print(f"\n[{label}]  ({name})")
        print(f"  {v}")

    print("\n" + "=" * 68)
    print("结论建议（供 Stage 1 决定落哪些指标）")
    print("=" * 68)
    usable = [name for name, v in verdicts.items() if "✓" in v]
    weak = [name for name, v in verdicts.items() if "~" in v]
    print(f"  可落地（✓ 可区分）: {usable or '（无）'}")
    print(f"  弱区分（~ 需谨慎/组合）: {weak or '（无）'}")
    if not usable and not weak:
        print("  ▶ 简单代码指标均无法区分——如实记录 pacing 需 LLM 语义判断，不强行落坏指标。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))
