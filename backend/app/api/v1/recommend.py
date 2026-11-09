from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import OptionalUser, RecommendServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.recommend import RandomRecommendOut

router = APIRouter(prefix="/recommend")


def _parse_exclude(raw: str | None) -> set[int]:
    if not raw:
        return set()
    return {int(x) for x in raw.split(",") if x.strip()}


@router.get("/random", response_model=Envelope[RandomRecommendOut])
async def random_recommend(
    svc: RecommendServiceDep,
    user: OptionalUser,
    canteen_id: int | None = None,
    campus_id: int | None = None,
    budget: Annotated[int | None, Query(ge=0, description="最高价格，分")] = None,
    spicy: Annotated[int | None, Query(ge=0, le=3, description="最高辣度")] = None,
    veg: bool | None = None,
    exclude: Annotated[
        str | None, Query(pattern=r"^\d+(,\d+)*$", description="已看过的菜 id，逗号分隔")
    ] = None,
):
    return ok(
        await svc.random(
            user=user,
            campus_id=campus_id,
            canteen_id=canteen_id,
            budget=budget,
            spicy=spicy,
            veg=veg,
            exclude=_parse_exclude(exclude),
        )
    )
