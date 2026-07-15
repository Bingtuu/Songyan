"""Task 172a.2/172a.3/172i: GenreRuntimeProfile 默认注册表 + 加载器 + 仓储.

加载语义（172i 最终版）：
    代码注册表是体裁基线（含 V8 实证调校）；DB 记录是字段级覆盖层。
    未知体裁或无 DB 记录时回退代码注册表；注册表未命中则回退 scifi baseline。

加载顺序：
    1. genre -> 代码默认注册表 -> 命中返回基线副本；未命中返回 scifi baseline 副本。
    2. 若 DB 中有该体裁记录，用 DB 显式字段覆盖基线；未提供字段保留基线值。
    3. 若 DB 不可用或无记录，直接返回注册表基线。

嵌套模型（setting_evaporation / foreshadowing_evaporation / character_decay /
continuity）按子模型整体替换：DB 提供则整体替换，不提供则保留基线子模型，
不细粒度合并子模型内部键，避免歧义。

代码默认注册表兜底保证新环境/测试无需 DB 预置即可运行。
"""

from __future__ import annotations

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import SongyanError
from songyan.models.genre_runtime_profile import GenreRuntimeProfile
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

logger = structlog.get_logger(__name__)

# 回退基准体裁：无任何匹配时使用（= V7 已验证的科幻行为）
FALLBACK_GENRE = "scifi"


def _default_registry() -> dict[str, GenreRuntimeProfile]:
    """代码内默认 Profile 注册表.

    scifi = 全默认（= 172a.1 baseline 快照 = 当前代码常量）。
    xuanhuan/wuxia = 基于实测的初始调参（172a.4/172a.6 会进一步 tune）。
    只在此处集中定义体裁差异，新增体裁只需加一条记录。
    """
    scifi = GenreRuntimeProfile(genre="scifi")

    # xuanhuan: genre_rules 实测比 scifi 贵 +79.9%（172a.1），不可裁核心在低预算
    # 窗口溢出。真实杠杆是抬高 base_budget，而非分区权重。
    # 实跑标定：
    #   base=12000 -> Ch8 before_emergency 1.03（不再 halt，但每章触发 emergency）
    #   base=13000 -> end15 15/15 accepted、峰值 before_emergency 1.286
    #                （仍每章 emergency，逼近 1.3）
    #   base=15000 -> 给不可裁核心（~14K）真实裕度，避免每章 emergency（172a.7 复核）
    xuanhuan = GenreRuntimeProfile(
        genre="xuanhuan",
        base_budget=15000,
        ramp_per_chapter=250,
    )
    # xuanhuan 状态密度高：角色出场密、设定（功法/境界）需长期保持
    # 172b.q: Ch90+ consistency CED 热点集中在 character_behavior /
    # dialogue_distinctness；后段预算充足，增加角色状态装载量与 full/compact
    # 保留窗口，给 Writer/Auditor 更多声纹与行为约束。
    xuanhuan.max_character_states = 8
    xuanhuan.character_decay.dormant_window = 20
    xuanhuan.character_decay.focal_gaps = {"full": 8, "compact": 20, "symbol": 60}
    xuanhuan.setting_evaporation.time_denominators = {
        "critical": 140,
        "recurring": 110,
        "background": 40,
        "technical": 45,
        "historical": 30,
    }
    # 172a.p: floor=12 解决短窗口 S 维度；172b.p: Ch65 实跑证明 xuanhuan
    # plant 密度高于 scifi，floor=12 在 Ch100 尺度仍会 overdue 超标。
    # floor=48 是 Ch100 长窗口档：只抬高 expected horizon，不改评估口径；
    # scifi(floor=0) 不受影响。
    xuanhuan.foreshadowing_horizon_floor = 48

    # wuxia: genre_rules +27.7%，中等压力，base_budget 适度抬高
    wuxia = GenreRuntimeProfile(
        genre="wuxia",
        base_budget=9500,
    )
    # 172a.p: wuxia 埋伏笔 horizon 比 xuanhuan 更短（--end 15 回归实测峰值 +2/+3，
    # max +11，overdue=25）。实跑 DB 模拟：floor=12 -> overdue@end15 = 5。
    # 与 xuanhuan 同机制复用，为 172c wuxia Ch100 爬坡做准备。
    wuxia.foreshadowing_horizon_floor = 12

    # urban: genre_rules ≈ scifi（-1.5%），运行时与 scifi 同级
    urban = GenreRuntimeProfile(genre="urban")

    return {p.genre: p for p in (scifi, xuanhuan, wuxia, urban)}


class GenreRuntimeProfileError(SongyanError):
    """Genre runtime profile repository error."""


class GenreRuntimeProfileRepository:
    """DB 读写 genre_runtime_profiles 表."""

    async def get(self, genre: str) -> GenreRuntimeProfile | None:
        """按 genre 读取 Profile；无记录返回 None."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT profile_json FROM genre_runtime_profiles WHERE genre = ?",
                (genre,),
            )
            row = await cursor.fetchone()
        if not row or not row[0]:
            return None
        data = _from_json(row[0], default=None)
        if not data:
            return None
        return GenreRuntimeProfile.model_validate(data)

    async def upsert(self, profile: GenreRuntimeProfile) -> None:
        """写入/更新一条 Profile（按 genre 唯一）."""
        payload = _to_json(profile.model_dump(mode="json"))
        async with get_db() as conn:
            try:
                await conn.execute(
                    """INSERT INTO genre_runtime_profiles (genre, version, profile_json)
                       VALUES (?, ?, ?)
                       ON CONFLICT(genre) DO UPDATE SET
                           version = excluded.version,
                           profile_json = excluded.profile_json,
                           updated_at = datetime('now')""",
                    (profile.genre, profile.version, payload),
                )
                await conn.commit()
            except Exception as exc:  # noqa: BLE001 - 归一化为领域异常
                await conn.rollback()
                msg = f"failed to upsert genre runtime profile: {profile.genre}"
                raise GenreRuntimeProfileError(msg) from exc

    async def list_all(self) -> list[GenreRuntimeProfile]:
        """列出所有 DB 中的 Profile."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT profile_json FROM genre_runtime_profiles ORDER BY genre"
            )
            rows = await cursor.fetchall()
        out: list[GenreRuntimeProfile] = []
        for row in rows:
            data = _from_json(row[0], default=None)
            if data:
                out.append(GenreRuntimeProfile.model_validate(data))
        return out


def load_profile_from_registry(genre: str | None) -> GenreRuntimeProfile:
    """仅从代码默认注册表加载（同步，无 DB）.

    未命中返回 scifi baseline 的副本，保证任何体裁都能回退旧行为。
    """
    registry = _default_registry()
    key = (genre or "").strip().lower()
    if key in registry:
        return registry[key].model_copy(deep=True)
    return registry[FALLBACK_GENRE].model_copy(deep=True)


async def load_profile(genre: str | None) -> GenreRuntimeProfile:
    """按体裁加载 Profile：代码注册表为基线，DB 记录为字段级覆盖层.

    加载顺序与语义：
    1. 先从代码注册表取体裁默认值（含 V8 实证调校）；未知体裁回退 scifi baseline。
    2. 若 DB 中有该体裁记录，用 DB 记录的显式字段覆盖注册表基线；未提供的字段
       保留基线值。
    3. 若 DB 不可用或无记录，直接返回注册表基线。

    嵌套模型（setting_evaporation / foreshadowing_evaporation / character_decay /
    continuity）按子模型整体替换：DB 提供则整体替换，不提供则保留基线子模型，
    不细粒度合并子模型内部键，避免歧义。
    """
    key = (genre or "").strip().lower()
    base = load_profile_from_registry(key)

    if not key:
        return base

    try:
        repo = GenreRuntimeProfileRepository()
        override = await repo.get(key)
    except Exception as exc:  # noqa: BLE001 - DB 不可用时回退基线，不阻断生成
        logger.warning(
            "genre_runtime_profile.db_load_failed",
            genre=key,
            error=str(exc),
        )
        return base

    if override is None:
        return base

    # 字段级覆盖：DB 中异于模型默认值的字段视为显式覆盖，覆盖注册表基线；
    # 与默认值相同的字段视为未显式覆盖，保留注册表基线。
    # 嵌套子模型按整体替换：DB 提供且异于默认时替换整个子模型，否则保留基线子模型。
    base_data = base.model_dump(mode="json")
    override_data = override.model_dump(mode="json")
    default_for_genre = GenreRuntimeProfile(genre=override.genre)
    default_data = default_for_genre.model_dump(mode="json")
    diff = {
        k: v
        for k, v in override_data.items()
        if k != "genre" and v != default_data.get(k)
    }
    merged = {**base_data, **diff}
    return GenreRuntimeProfile.model_validate(merged)
