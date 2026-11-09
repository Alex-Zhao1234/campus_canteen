from fastapi import APIRouter

from app.api.deps import OrgServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.org import CanteenOut, StallOut

router = APIRouter(prefix="/canteens")


@router.get("", response_model=Envelope[list[CanteenOut]])
async def list_canteens(svc: OrgServiceDep, campus_id: int | None = None):
    return ok(await svc.list_canteens(campus_id))


@router.get("/{canteen_id}/stalls", response_model=Envelope[list[StallOut]])
async def list_stalls(canteen_id: int, svc: OrgServiceDep):
    return ok(await svc.list_stalls(canteen_id))
