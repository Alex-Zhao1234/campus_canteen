"""座位相关 DTO：读数（模拟器 / 将来的传感器网关 → 服务层）与空位查询出参。"""

from datetime import datetime

from pydantic import BaseModel

from app.seating.levels import Level


class SeatReading(BaseModel):
    """一条座位读数。ts 缺省由服务层取当前 UTC。"""

    code: str
    is_occupied: bool
    ts: datetime | None = None


class ApplyResult(BaseModel):
    applied: int
    unknown_codes: list[str]


class FloorOccupancyOut(BaseModel):
    floor: int
    total: int
    occupied: int
    free: int
    ratio: float
    level: Level
    updated_at: datetime | None


class CanteenOccupancyOut(BaseModel):
    canteen_id: int
    canteen_name: str
    floors: int
    levels: list[FloorOccupancyOut]


class SeatDotOut(BaseModel):
    code: str
    is_occupied: bool


class SeatMapOut(BaseModel):
    """某食堂某层的座位平面图：seats 按编码顺序，前端按 cols 列铺成网格。"""

    canteen_id: int
    floor: int
    cols: int
    total: int
    occupied: int
    updated_at: datetime | None
    seats: list[SeatDotOut]
