"""组织结构服务：把 ORM 对象 + 统计组装成接口 DTO，处理"找不到"。"""

from app.models import Dish, DishStats, Stall, StallStats
from app.repositories.org_repo import OrgRepository
from app.schemas.org import (
    CanteenOut,
    DishBase,
    DishDetailOut,
    DishOut,
    DishStatsOut,
    StallBase,
    StallBriefOut,
    StallDetailOut,
    StallOut,
    StallStatsOut,
)
from app.services.errors import NotFoundError


def _stall_out(stall: Stall, stats: StallStats | None) -> dict:
    """窗口字段 + 统计；没有统计记录时给全零默认值。"""
    return {
        **StallBase.model_validate(stall).model_dump(),
        "stats": StallStatsOut.model_validate(stats) if stats else StallStatsOut(),
    }


def _dish_out(dish: Dish, stats: DishStats | None) -> dict:
    return {
        **DishBase.model_validate(dish).model_dump(),
        "stats": DishStatsOut.model_validate(stats) if stats else DishStatsOut(),
    }


class OrgService:
    def __init__(self, repo: OrgRepository) -> None:
        self.repo = repo

    async def list_canteens(self, campus_id: int | None = None) -> list[CanteenOut]:
        return [CanteenOut.model_validate(c) for c in await self.repo.list_canteens(campus_id)]

    async def list_stalls(self, canteen_id: int) -> list[StallOut]:
        if await self.repo.get_canteen(canteen_id) is None:
            raise NotFoundError("食堂", canteen_id)
        rows = await self.repo.list_stalls_with_stats(canteen_id)
        return [StallOut(**_stall_out(stall, stats)) for stall, stats in rows]

    async def get_stall(self, stall_id: int) -> StallDetailOut:
        stall = await self.repo.get_stall(stall_id)
        if stall is None:
            raise NotFoundError("窗口", stall_id)
        stats = await self.repo.get_stall_stats(stall_id)
        dishes = [
            DishOut(**_dish_out(d, s)) for d, s in await self.repo.list_dishes_with_stats(stall_id)
        ]
        return StallDetailOut(**_stall_out(stall, stats), dishes=dishes)

    async def get_dish(self, dish_id: int) -> DishDetailOut:
        row = await self.repo.get_dish_with_stats(dish_id)
        if row is None:
            raise NotFoundError("菜品", dish_id)
        dish, stats = row
        brief = StallBriefOut(
            id=dish.stall.id,
            name=dish.stall.name,
            floor=dish.stall.floor,
            canteen_id=dish.stall.canteen_id,
            canteen_name=dish.stall.canteen.name,
        )
        return DishDetailOut(**_dish_out(dish, stats), stall=brief)
