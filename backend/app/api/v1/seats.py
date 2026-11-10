"""空位查询：登录用户看每个食堂每层的占用率与拥挤度。前端 5 秒轮询。"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SeatServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.seat import CanteenOccupancyOut

router = APIRouter(prefix="/seats")


@router.get("/occupancy", response_model=Envelope[list[CanteenOccupancyOut]])
async def seat_occupancy(user: CurrentUser, svc: SeatServiceDep, campus_id: int | None = None):
    return ok(await svc.occupancy(campus_id))
