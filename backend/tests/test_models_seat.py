"""座位表：code 全局唯一；seat_state 以 seat_id 为主键，一座一行。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Campus, Canteen, Seat, SeatState


async def _canteen(db) -> Canteen:
    canteen = Canteen(name="二食堂", floors=3, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.commit()
    return canteen


async def test_seat_code_is_unique(db):
    canteen = await _canteen(db)
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"))
    await db.commit()
    db.add(Seat(canteen_id=canteen.id, floor=2, code="C1-1F-001"))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_seat_defaults_active(db):
    canteen = await _canteen(db)
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"))
    await db.commit()
    seat = await db.scalar(select(Seat))
    assert seat.is_active is True


async def test_seat_state_defaults_timestamps(db):
    canteen = await _canteen(db)
    seat = Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001")
    db.add(seat)
    await db.commit()
    db.add(SeatState(seat_id=seat.id, is_occupied=True))
    await db.commit()
    state = await db.scalar(select(SeatState))
    assert state.is_occupied is True
    assert state.changed_at is not None and state.updated_at is not None


async def test_seat_state_is_one_row_per_seat(db):
    canteen = await _canteen(db)
    seat = Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001")
    db.add(seat)
    await db.commit()
    db.add(SeatState(seat_id=seat.id, is_occupied=True))
    await db.commit()
    db.add(SeatState(seat_id=seat.id, is_occupied=False))
    with pytest.raises(IntegrityError):
        await db.commit()
