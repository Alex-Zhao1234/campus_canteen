from fastapi import APIRouter

from app.api.deps import RankingServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.ranking import RankingOut, RankingTypeIn

router = APIRouter(prefix="/rankings")


@router.get("/today", response_model=Envelope[RankingOut])
async def today(
    svc: RankingServiceDep,
    type: RankingTypeIn = "good",
    canteen_id: int | None = None,
    campus_id: int | None = None,
):
    return ok(await svc.today(type, canteen_id, campus_id))
