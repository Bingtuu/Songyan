"""Task 172a.2/172a.3: GenreRuntimeProfile 默认注册表 + 加载器 + 仓储.

加载顺序（AGENTS.md V8 硬约束）：
    genre -> DB genre_runtime_profiles
        -> 命中：反序列化返回
        -> 未命中：回退代码内默认注册表
            -> 注册表命中（scifi/xuanhuan/...）：返回
            -> 注册表未命中：返回 scifi baseline（保证旧行为不变）

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
    xuanhuan.character_decay.dormant_window = 20
    xuanhuan.character_decay.focal_gaps = {"full": 4, "compact": 12, "symbol": 40}
    xuanhuan.setting_evaporation.time_denominators = {
        "critical": 140,
        "recurring": 110,
        "background": 40,
        "technical": 45,
        "historical": 30,
    }
    # 172a.p: xuanhuan 每章密集埋伏笔且 LLM horizon 偏短 -> Ch15 overdue=28。
    # plant 时把 horizon 夹到 >= planted+12（实跑 DB 模拟：overdue 28->1），
    # 压下 S 维度失分；scifi(floor=0) 不受影响。
    xuanhuan.foreshadowing_horizon_floor = 12

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
    """按加载顺序解析 Profile：DB 优先，其次代码注册表，最后 scifi 回退."""
    key = (genre or "").strip().lower()
    if key:
        try:
            repo = GenreRuntimeProfileRepository()
            db_profile = await repo.get(key)
            if db_profile is not None:
                return db_profile
        except Exception as exc:  # noqa: BLE001 - DB 不可用时回退注册表，不阻断生成
            logger.warning(
                "genre_runtime_profile.db_load_failed",
                genre=key,
                error=str(exc),
            )
    return load_profile_from_registry(key)
