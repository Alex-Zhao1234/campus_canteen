from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import OptionalUser, OrgServiceDep, ReviewServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.org import DishDetailOut
from app.schemas.review import DishReviewPageOut

router = APIRouter(prefix="/dishes")


@router.get("/{dish_id}", response_model=Envelope[DishDetailOut])
async def get_dish(dish_id: int, svc: OrgServiceDep):
    return ok(await svc.get_dish(dish_id))


@router.get("/{dish_id}/reviews", response_model=Envelope[DishReviewPageOut])
async def list_dish_reviews(
    dish_id: int,
    user: OptionalUser,
    svc: ReviewServiceDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    before_id: Annotated[int | None, Query(gt=0)] = None,
):
    """菜品评论区：按时间倒序，游标分页。登录用户的条目带 is_mine。"""
    return ok(await svc.list_for_dish(dish_id, user, limit, before_id))
