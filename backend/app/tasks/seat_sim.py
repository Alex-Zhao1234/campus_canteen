"""座位模拟器：没有真实传感器时，按餐段曲线生成座位进出。

扮演"传感器网关"的角色：算出要翻转的座位后，走 SeatService.apply_states 写入；
将来真硬件接入也会调同一个方法。不知道调度器的存在：定时任务、命令行、测试都直接调 simulate_tick。
用法：python -m app.tasks.seat_sim
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models._mixins import utcnow
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import SeatReading
from app.services.seat_service import SeatService

BEIJING_OFFSET = timedelta(hours=8)

# (北京时间分钟数, 目标占用率)，分段线性插值。spec 第 5 节的表展开成折线。
TARGET_CURVE: tuple[tuple[int, float], ...] = (
    (0, 0.03),
    (390, 0.03),  # 06:30
    (420, 0.35),  # 07:00 早餐
    (510, 0.35),  # 08:30
    (570, 0.08),  # 09:30
    (660, 0.08),  # 11:00
    (690, 0.90),  # 11:30 午高峰
    (750, 0.90),  # 12:30
    (810, 0.08),  # 13:30
    (990, 0.08),  # 16:30
    (1050, 0.85),  # 17:30 晚高峰
    (1110, 0.85),  # 18:30
    (1200, 0.05),  # 20:00
    (1440, 0.05),
)
# 层间系数：1 层最挤，越高越空；未列出的楼层用 DEFAULT_FLOOR_FACTOR
FLOOR_FACTOR: dict[int, float] = {1: 1.0, 2: 0.9}
DEFAULT_FLOOR_FACTOR = 0.8
NOISE = 0.05  # 目标占用率随机噪声 ±
MAX_RATIO = 0.98
MAX_FLIP_SHARE = 0.05  # 每 tick 朝目标最多翻转的座位比例
CHURN_SHARE = 0.01  # 每 tick 额外随机进出比例


def target_ratio(beijing_minutes: int) -> float:
    m = beijing_minutes % 1440
    for (m0, r0), (m1, r1) in zip(TARGET_CURVE, TARGET_CURVE[1:], strict=False):
        if m0 <= m <= m1:
            if m1 == m0:
                return r1
            return r0 + (r1 - r0) * (m - m0) / (m1 - m0)
    return TARGET_CURVE[-1][1]


def floor_target(beijing_minutes: int, floor: int, rng: random.Random) -> float:
    base = target_ratio(beijing_minutes) * FLOOR_FACTOR.get(floor, DEFAULT_FLOOR_FACTOR)
    return min(MAX_RATIO, max(0.0, base + rng.uniform(-NOISE, NOISE)))


def plan_flips(
    seats: list[tuple[str, bool]], target: float, rng: random.Random
) -> list[tuple[str, bool]]:
    """给定一层的 (code, is_occupied) 与目标占用率，返回本 tick 要翻转的 (code, 新状态)。"""
    total = len(seats)
    if total == 0:
        return []
    occupied = [c for c, occ in seats if occ]
    free = [c for c, occ in seats if not occ]
    gap = round(target * total) - len(occupied)
    step = min(abs(gap), max(1, int(total * MAX_FLIP_SHARE)))

    flips: dict[str, bool] = {}
    if gap > 0:
        for c in rng.sample(free, min(step, len(free))):
            flips[c] = True
    elif gap < 0:
        for c in rng.sample(occupied, min(step, len(occupied))):
            flips[c] = False

    # 随机进出：高峰时也有人起身、有人坐下
    churn = int(total * CHURN_SHARE)
    remaining = [(c, occ) for c, occ in seats if c not in flips]
    for c, occ in rng.sample(remaining, min(churn, len(remaining))):
        flips[c] = not occ
    return list(flips.items())


def _beijing_minutes(now: datetime) -> int:
    local = now + BEIJING_OFFSET
    return local.hour * 60 + local.minute


async def simulate_tick(
    session: AsyncSession, now: datetime | None = None, rng: random.Random | None = None
) -> int:
    """跑一个 tick：每个食堂每层朝目标占用率翻转少量座位。返回写入的座位数。"""
    now = now or utcnow()
    rng = rng or random.Random()
    repo = SeatRepository(session)
    rows = await repo.list_active_seats()
    if not rows:
        return 0

    by_floor: dict[tuple[int, int], list[tuple[str, bool]]] = {}
    for seat, state in rows:
        occ = bool(state.is_occupied) if state is not None else False
        by_floor.setdefault((seat.canteen_id, seat.floor), []).append((seat.code, occ))

    minutes = _beijing_minutes(now)
    readings: list[SeatReading] = []
    for (_, floor), seats in by_floor.items():
        target = floor_target(minutes, floor, rng)
        readings.extend(
            SeatReading(code=code, is_occupied=occ, ts=now)
            for code, occ in plan_flips(seats, target, rng)
        )
    if not readings:
        return 0
    result = await SeatService(repo).apply_states(readings, now=now)
    return result.applied


async def _main() -> None:
    async with SessionLocal() as session:
        applied = await simulate_tick(session)
    print(f"座位模拟器：本 tick 写入 {applied} 个座位状态")


if __name__ == "__main__":
    asyncio.run(_main())
