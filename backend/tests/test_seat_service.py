"""SeatService.apply_states：座位读数 upsert。本期由模拟器调用，将来传感器网关的路由也调它。"""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import Campus, Canteen, Seat, SeatState
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import SeatReading
from app.services.seat_service import SeatService

T1 = datetime(2026, 11, 10, 4, 0)
T2 = datetime(2026, 11, 10, 4, 5)
T3 = datetime(2026, 11, 10, 4, 10)


@pytest.fixture
async def svc(db) -> SeatService:
    """二食堂 1 层三个座位，其中 003 停用。"""
    canteen = Canteen(name="二食堂", floors=1, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.flush()
    db.add_all(
        [
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"),
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-002"),
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-003", is_active=False),
        ]
    )
    await db.commit()
    return SeatService(SeatRepository(db))


async def _states(db) -> dict[str, SeatState]:
    rows = (await db.execute(select(Seat.code, SeatState).join(SeatState))).all()
    return {code: state for code, state in rows}


async def test_upserts_and_reports_unknown_codes(db, svc):
    result = await svc.apply_states(
        [
            SeatReading(code="C1-1F-001", is_occupied=True),
            SeatReading(code="C1-1F-003", is_occupied=True),  # 停用座位
            SeatReading(code="C9-9F-999", is_occupied=False),  # 不存在
        ],
        now=T1,
    )
    assert result.applied == 1
    assert result.unknown_codes == ["C1-1F-003", "C9-9F-999"]
    states = await _states(db)
    assert set(states) == {"C1-1F-001"}
    assert states["C1-1F-001"].is_occupied is True
    assert states["C1-1F-001"].changed_at == states["C1-1F-001"].updated_at == T1


async def test_changed_at_only_moves_on_flip(db, svc):
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=True, ts=T1)])
    # 同状态心跳：updated_at 前进，changed_at 不动
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=True, ts=T2)])
    s = (await _states(db))["C1-1F-001"]
    assert s.changed_at == T1
    assert s.updated_at == T2
    # 翻转：两者都前进
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=False, ts=T3)])
    s = (await _states(db))["C1-1F-001"]
    assert s.is_occupied is False
    assert s.changed_at == s.updated_at == T3


async def test_reading_without_ts_uses_now(db, svc):
    await svc.apply_states([SeatReading(code="C1-1F-002", is_occupied=True)], now=T2)
    assert (await _states(db))["C1-1F-002"].updated_at == T2


async def test_duplicate_code_in_batch_last_one_wins(db, svc):
    result = await svc.apply_states(
        [
            SeatReading(code="C1-1F-001", is_occupied=True),
            SeatReading(code="C1-1F-001", is_occupied=False),
        ]
    )
    assert result.applied == 1
    assert (await _states(db))["C1-1F-001"].is_occupied is False


async def test_empty_batch_is_noop(db, svc):
    result = await svc.apply_states([])
    assert result.applied == 0 and result.unknown_codes == []
    assert await _states(db) == {}
