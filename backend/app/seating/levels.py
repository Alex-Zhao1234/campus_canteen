"""拥挤度分层。阈值见 docs/superpowers/specs/2026-11-10-seat-occupancy-design.md 第 3 节。

找座难度非线性：70% 以前随便坐，70%–85% 要绕一圈，85% 以上剩的是散落单座，
所以高两档区间故意比低三档窄。
"""

from typing import Literal

Level = Literal["unknown", "empty", "low", "medium", "high", "full"]

# (占用率上限（不含）, 档位)，按升序；超过最后一档上限即 full
LEVEL_THRESHOLDS: tuple[tuple[float, Level], ...] = (
    (0.25, "empty"),
    (0.50, "low"),
    (0.70, "medium"),
    (0.85, "high"),
)

# 座位平面图每行座位数：所有楼层都是"宽 10"，座位在图中的位置 = 它在该层的序号
SEAT_GRID_COLS = 10

LEVEL_LABELS: dict[Level, str] = {
    "unknown": "暂无数据",
    "empty": "空闲",
    "low": "较少",
    "medium": "适中",
    "high": "较多",
    "full": "爆满",
}


def occupancy_ratio(occupied: int, total: int) -> float:
    """占用率，保留 3 位；没有座位时为 0。"""
    if total <= 0:
        return 0.0
    return round(occupied / total, 3)


def level_for(occupied: int, total: int) -> Level:
    if total <= 0:
        return "unknown"
    ratio = occupied / total  # 分档用未舍入的值，避免 0.2496 被舍成 0.25
    for upper, level in LEVEL_THRESHOLDS:
        if ratio < upper:
            return level
    return "full"
