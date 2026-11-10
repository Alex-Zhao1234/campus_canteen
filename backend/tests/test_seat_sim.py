"""座位模拟器：餐段曲线插值、单 tick 翻转朝目标靠拢且不越界、走 apply_states 写入。"""

import random
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.models import Campus, Canteen, Seat, SeatState
from app.tasks.seat_sim import floor_target, plan_flips, simulate_tick, target_ratio


def _m(h: int, m: int = 0) -> int:
    return h * 60 + m


def test_target_curve_key_points():
    assert target_ratio(_m(3)) == pytest.approx(0.03)
    assert target_ratio(_m(12)) == pytest.approx(0.90)
    assert target_ratio(_m(18)) == pytest.approx(0.85)
    assert target_ratio(_m(15)) == pytest.approx(0.08)
    assert target_ratio(_m(22)) == pytest.approx(0.05)


def test_target_curve_interpolates_between_points():
    # 11:00 → 0.08，11:30 → 0.90，11:15 应在中间
    mid = target_ratio(_m(11, 15))
    assert 0.08 < mid < 0.90
    assert mid == pytest.approx(0.49, abs=0.01)


def test_floor_target_decreases_with_floor_and_is_clamped():
    rng = random.Random(1)
    f1 = [floor_target(_m(12), 1, rng) for _ in range(50)]
    f3 = [floor_target(_m(12), 3, rng) for _ in range(50)]
    assert all(0.0 <= x <= 0.98 for x in f1 + f3)
    assert sum(f1) / 50 > sum(f3) / 50


def test_plan_flips_moves_toward_target_without_overshoot():
    rng = random.Random(7)
    seats = [(f"S{i:03d}", False) for i in range(100)]  # 全空，目标 50%
    flips = plan_flips(seats, 0.5, rng)
    turned_on = [c for c, occ in flips if occ]
    # 每 tick 最多翻 5% 朝目标 + 1% 随机进出
    assert 5 <= len(turned_on) <= 6
    assert len(flips) <= 6
    assert len({c for c, _ in flips}) == len(flips)  # 同一座位不重复出现


def test_plan_flips_at_target_only_churns():
    rng = random.Random(3)
    seats = [(f"S{i:03d}", i < 50) for i in range(100)]
    flips = plan_flips(seats, 0.5, rng)
    assert len(flips) == 1  # 1% 随机进出


def test_plan_flips_small_floor_still_churns():
    # 80 座的楼层（二食堂 3 层）到达目标后也要有人进出，1% 向上取整至少 1 个
    rng = random.Random(5)
    seats = [(f"S{i:03d}", i < 40) for i in range(80)]
    assert len(plan_flips(seats, 0.5, rng)) == 1


def test_plan_flips_moves_down_when_over_target():
    rng = random.Random(9)
    seats = [(f"S{i:03d}", True) for i in range(100)]  # 全满，凌晨目标 3%
    flips = plan_flips(seats, 0.03, rng)
    # 5% 朝目标 + 1% 随机进出（全满时随机进出只能是有人起身），全部是"离开"
    assert len(flips) == 6
    assert all(not occ for _, occ in flips)


def test_plan_flips_handles_empty_floor():
    assert plan_flips([], 0.9, random.Random(0)) == []


async def test_simulate_tick_writes_states_via_service(db):
    canteen = Canteen(name="二食堂", floors=1, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.flush()
    db.add_all([Seat(canteen_id=canteen.id, floor=1, code=f"C1-1F-{i:03d}") for i in range(1, 41)])
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-OFF", is_active=False))
    await db.commit()

    noon_beijing = datetime(2026, 11, 10, 4, 0)  # UTC 04:00 = 北京 12:00，目标 0.9
    applied = await simulate_tick(db, now=noon_beijing, rng=random.Random(42))
    assert applied >= 1
    occupied = await db.scalar(
        select(func.count()).select_from(SeatState).where(SeatState.is_occupied.is_(True))
    )
    # 40 座 × 5% = 2 个朝目标，随机进出 ceil(40*0.01)=1 个（全空时只能坐上）
    assert occupied == 3
    # 停用座位不会被写入
    off_id = await db.scalar(select(Seat.id).where(Seat.code == "C1-1F-OFF"))
    assert await db.scalar(select(SeatState).where(SeatState.seat_id == off_id)) is None


async def test_simulate_tick_with_no_seats_is_noop(db):
    assert await simulate_tick(db, now=datetime(2026, 11, 10, 4, 0)) == 0
