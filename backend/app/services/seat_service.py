"""座位服务：读数写入（upsert seat_state）、按食堂 × 楼层聚合拥挤度。

apply_states 是"传感器网关 → 后端"链路的落点。本期没有上报 HTTP 接口，唯一调用方是
app/tasks/seat_sim.py 的模拟器；将来接真硬件时加一个路由层调用它即可。
"""

from datetime import datetime

from app.models import SeatState
from app.models._mixins import utcnow
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import ApplyResult, SeatReading


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
