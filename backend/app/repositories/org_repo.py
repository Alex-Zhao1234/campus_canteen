"""组织结构数据访问。只封装查询，不含业务判断。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Canteen, Dish, DishStats, Stall, StallStats


class OrgRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_canteens(self, campus_id: int | None = None) -> list[Canteen]:
        stmt = select(Canteen).where(Canteen.is_active.is_(True)).order_by(Canteen.id)
        if campus_id is not None:
            stmt = stmt.where(Canteen.campus_id == campus_id)
        return list((await self.session.scalars(stmt)).all())

    async def get_canteen(self, canteen_id: int) -> Canteen | None:
        return await self.session.get(Canteen, canteen_id)

    async def list_stalls_with_stats(
        self, canteen_id: int
    ) -> list[tuple[Stall, StallStats | None]]:
        stmt = (
            select(Stall, StallStats)
            .outerjoin(StallStats, StallStats.stall_id == Stall.id)
            .where(Stall.canteen_id == canteen_id, Stall.is_active.is_(True))
            .order_by(Stall.floor, Stall.id)
        )
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]

    async def get_stall(self, stall_id: int) -> Stall | None:
        return await self.session.get(Stall, stall_id)

    async def get_stall_stats(self, stall_id: int) -> StallStats | None:
        return await self.session.get(StallStats, stall_id)

    async def list_dishes_with_stats(self, stall_id: int) -> list[tuple[Dish, DishStats | None]]:
        stmt = (
            select(Dish, DishStats)
            .outerjoin(DishStats, DishStats.dish_id == Dish.id)
            .where(Dish.stall_id == stall_id, Dish.is_active.is_(True))
            .order_by(Dish.id)
        )
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]

    async def get_dish_with_stats(self, dish_id: int) -> tuple[Dish, DishStats | None] | None:
        stmt = (
            select(Dish, DishStats)
            .outerjoin(DishStats, DishStats.dish_id == Dish.id)
            .where(Dish.id == dish_id)
        )
        row = (await self.session.execute(stmt)).first()
        return tuple(row) if row else None
