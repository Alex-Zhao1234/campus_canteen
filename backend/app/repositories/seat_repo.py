"""座位数据访问：按 code 找座位、读写当前状态、按食堂 × 楼层聚合。不含业务判断。"""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Canteen, Seat, SeatState


class SeatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active_seats_by_codes(self, codes: Iterable[str]) -> list[Seat]:
        codes = list(codes)
        if not codes:
            return []
        stmt = select(Seat).where(Seat.code.in_(codes), Seat.is_active.is_(True))
        return list((await self.db.scalars(stmt)).all())

    async def get_states(self, seat_ids: Iterable[int]) -> dict[int, SeatState]:
        ids = list(seat_ids)
        if not ids:
            return {}
        rows = await self.db.scalars(select(SeatState).where(SeatState.seat_id.in_(ids)))
        return {s.seat_id: s for s in rows}

    def add_state(self, state: SeatState) -> None:
        self.db.add(state)

    async def commit(self) -> None:
        await self.db.commit()

    async def list_active_canteens(self, campus_id: int | None) -> list[Canteen]:
        stmt = select(Canteen).where(Canteen.is_active.is_(True)).order_by(Canteen.id)
        if campus_id is not None:
            stmt = stmt.where(Canteen.campus_id == campus_id)
        return list((await self.db.scalars(stmt)).all())

    async def floor_counts(
        self, canteen_ids: Iterable[int]
    ) -> list[tuple[int, int, int, int, datetime | None]]:
        """每个 (canteen_id, floor) 的 (total, occupied, 最新 updated_at)，只算在用座位。"""
        ids = list(canteen_ids)
        if not ids:
            return []
        occupied = func.coalesce(
            func.sum(case((SeatState.is_occupied.is_(True), 1), else_=0)), 0
        )
        stmt = (
            select(
                Seat.canteen_id,
                Seat.floor,
                func.count(Seat.id),
                occupied,
                func.max(SeatState.updated_at),
            )
            .select_from(Seat)
            .outerjoin(SeatState, SeatState.seat_id == Seat.id)
            .where(Seat.is_active.is_(True), Seat.canteen_id.in_(ids))
            .group_by(Seat.canteen_id, Seat.floor)
            .order_by(Seat.canteen_id, Seat.floor)
        )
        return [tuple(r) for r in (await self.db.execute(stmt)).all()]

    async def list_active_seats(self) -> list[tuple[Seat, SeatState | None]]:
        """模拟器用：全部在用座位及其状态（没有记录为 None）。"""
        stmt = (
            select(Seat, SeatState)
            .outerjoin(SeatState, SeatState.seat_id == Seat.id)
            .where(Seat.is_active.is_(True))
            .order_by(Seat.id)
        )
        return [(seat, state) for seat, state in (await self.db.execute(stmt)).all()]
