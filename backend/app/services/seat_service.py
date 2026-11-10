"""座位服务：读数写入（upsert seat_state）、按食堂 × 楼层聚合拥挤度。

apply_states 是"传感器网关 → 后端"链路的落点。本期没有上报 HTTP 接口，唯一调用方是
app/tasks/seat_sim.py 的模拟器；将来接真硬件时加一个路由层调用它即可。
"""

from datetime import datetime

from app.models import SeatState
from app.models._mixins import utcnow
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import (
    ApplyResult,
    CanteenOccupancyOut,
    FloorOccupancyOut,
    SeatDotOut,
    SeatMapOut,
    SeatReading,
)
from app.seating.levels import SEAT_GRID_COLS, level_for, occupancy_ratio
from app.services.errors import NotFoundError


class SeatService:
    def __init__(self, repo: SeatRepository) -> None:
        self.repo = repo

    async def apply_states(
        self, readings: list[SeatReading], now: datetime | None = None
    ) -> ApplyResult:
        """批量 upsert。同批同 code 以最后一条为准；未知/停用 code 收集返回，不整批失败。

        changed_at 只在 is_occupied 翻转时更新，updated_at 每条读数都更新（心跳）。
        """
        now = now or utcnow()
        latest: dict[str, SeatReading] = {}
        for r in readings:
            latest[r.code] = r

        seats = {seat.code: seat for seat in await self.repo.list_active_seats_by_codes(latest)}
        unknown = sorted(code for code in latest if code not in seats)
        existing = await self.repo.get_states(seat.id for seat in seats.values())

        applied = 0
        for code, reading in latest.items():
            seat = seats.get(code)
            if seat is None:
                continue
            ts = reading.ts or now
            state = existing.get(seat.id)
            if state is None:
                self.repo.add_state(
                    SeatState(
                        seat_id=seat.id,
                        is_occupied=reading.is_occupied,
                        changed_at=ts,
                        updated_at=ts,
                    )
                )
            else:
                if state.is_occupied != reading.is_occupied:
                    state.is_occupied = reading.is_occupied
                    state.changed_at = ts
                state.updated_at = ts
            applied += 1

        await self.repo.commit()
        return ApplyResult(applied=applied, unknown_codes=unknown)

    async def occupancy(self, campus_id: int | None = None) -> list[CanteenOccupancyOut]:
        """每个在营食堂按 1..floors 列出每层；有座位但超出 floors 的层也列出。"""
        canteens = await self.repo.list_active_canteens(campus_id)
        counts = {
            (cid, floor): (total, occupied, updated_at)
            for cid, floor, total, occupied, updated_at in await self.repo.floor_counts(
                c.id for c in canteens
            )
        }
        result: list[CanteenOccupancyOut] = []
        for c in canteens:
            seat_floors = [f for (cid, f) in counts if cid == c.id]
            top = max([c.floors, *seat_floors])
            levels = []
            for floor in range(1, top + 1):
                total, occupied, updated_at = counts.get((c.id, floor), (0, 0, None))
                levels.append(
                    FloorOccupancyOut(
                        floor=floor,
                        total=total,
                        occupied=occupied,
                        free=total - occupied,
                        ratio=occupancy_ratio(occupied, total),
                        level=level_for(occupied, total),
                        updated_at=updated_at,
                    )
                )
            result.append(
                CanteenOccupancyOut(
                    canteen_id=c.id, canteen_name=c.name, floors=c.floors, levels=levels
                )
            )
        return result

    async def floor_map(self, canteen_id: int, floor: int) -> SeatMapOut:
        """某层座位平面图。食堂不存在/停用 404；该层没有座位返回空列表。"""
        if await self.repo.get_active_canteen(canteen_id) is None:
            raise NotFoundError("食堂", canteen_id)
        rows = await self.repo.list_floor_seats(canteen_id, floor)
        seats = [
            SeatDotOut(code=seat.code, is_occupied=bool(state.is_occupied) if state else False)
            for seat, state in rows
        ]
        updated = [state.updated_at for _, state in rows if state is not None]
        return SeatMapOut(
            canteen_id=canteen_id,
            floor=floor,
            cols=SEAT_GRID_COLS,
            total=len(seats),
            occupied=sum(1 for s in seats if s.is_occupied),
            updated_at=max(updated) if updated else None,
            seats=seats,
        )
