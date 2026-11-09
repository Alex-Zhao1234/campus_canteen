from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Canteen, Dish, DishStats, Review, Stall, StallStats

CandidateRow = tuple[Dish, Stall, Canteen, DishStats | None, StallStats | None]


class RecommendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_candidates(
        self,
        *,
        campus_id: int,
        canteen_id: int | None,
        budget: int | None,
        spicy: int | None,
        veg: bool | None,
    ) -> list[CandidateRow]:
        """在售菜 + 在营窗口/食堂，按硬约束过滤，附 dish_stats / stall_stats。"""
        stmt = (
            select(Dish, Stall, Canteen, DishStats, StallStats)
            .join(Stall, Stall.id == Dish.stall_id)
            .join(Canteen, Canteen.id == Stall.canteen_id)
            .outerjoin(DishStats, DishStats.dish_id == Dish.id)
            .outerjoin(StallStats, StallStats.stall_id == Stall.id)
            .where(
                Canteen.campus_id == campus_id,
                Dish.is_active.is_(True),
                Stall.is_active.is_(True),
                Canteen.is_active.is_(True),
            )
        )
        if canteen_id is not None:
            stmt = stmt.where(Canteen.id == canteen_id)
        if budget is not None:
            stmt = stmt.where(Dish.price_cents <= budget)
        if spicy is not None:
            stmt = stmt.where(Dish.spicy_level <= spicy)
        if veg:
            stmt = stmt.where(Dish.is_veg.is_(True))
        return [tuple(r) for r in (await self.session.execute(stmt)).all()]

    async def recently_reviewed_dish_ids(self, user_id: int, since: datetime) -> set[int]:
        stmt = select(Review.dish_id).where(Review.user_id == user_id, Review.created_at >= since)
        return set((await self.session.scalars(stmt)).all())
