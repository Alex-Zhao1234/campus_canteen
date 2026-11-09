from fastapi import APIRouter

from app.api.deps import OrgServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.org import DishDetailOut

router = APIRouter(prefix="/dishes")


@router.get("/{dish_id}", response_model=Envelope[DishDetailOut])
async def get_dish(dish_id: int, svc: OrgServiceDep):
    return ok(await svc.get_dish(dish_id))
