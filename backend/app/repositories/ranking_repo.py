"""榜单任务与榜单接口的数据访问。写操作不单独提交，由调用方统一 commit。"""

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Campus,
    Canteen,
    Dish,
    DishStats,
    RankingSnapshot,
    Review,
    Stall,
    StallStats,
    User,
)
from app.recommender.stats import DishMetrics, ReviewEvent, StallMetrics


class RankingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 任务侧：读 ---

    async def list_active_dishes(self) -> list[tuple[int, int, int, int]]:
        """(dish_id, stall_id, canteen_id, campus_id)，只含在售菜、在营窗口/食堂。"""
        stmt = (
            select(Dish.id, Stall.id, Canteen.id, Canteen.campus_id)
            .join(Stall, Stall.id == Dish.stall_id)
            .join(Canteen, Canteen.id == Stall.canteen_id)
            .where(Dish.is_active.is_(True), Stall.is_active.is_(True), Canteen.is_active.is_(True))
        )
        return [tuple(r) for r in (await self.session.execute(stmt)).all()]

    async def list_active_stall_ids(self) -> list[int]:
        stmt = select(Stall.id).where(Stall.is_active.is_(True))
        return list((await self.session.scalars(stmt)).all())

    async def list_review_events(self) -> list[tuple[int, int, ReviewEvent]]:
        """全部未隐藏评价：(dish_id, stall_id, event)。"""
        stmt = (
            select(
                Review.dish_id, Review.stall_id, Review.verdict, Review.created_at, User.trust_score
            )
            .join(User, User.id == Review.user_id)
            .where(Review.is_hidden.is_(False))
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            (d, s, ReviewEvent(verdict=v, created_at=t, trust_score=ts)) for d, s, v, t, ts in rows
        ]

    async def count_reviews(self) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(Review).where(Review.is_hidden.is_(False))
        )

    async def list_campus_ids(self) -> list[int]:
        return list((await self.session.scalars(select(Campus.id).order_by(Campus.id))).all())

    async def list_canteens(self) -> list[tuple[int, int]]:
        """(canteen_id, campus_id)，在营食堂。"""
        stmt = select(Canteen.id, Canteen.campus_id).where(Canteen.is_active.is_(True))
        return [tuple(r) for r in (await self.session.execute(stmt)).all()]

    async def load_dish_stats(self) -> dict[int, DishStats]:
        return {r.dish_id: r for r in (await self.session.scalars(select(DishStats))).all()}

    async def load_stall_stats(self) -> dict[int, StallStats]:
        return {r.stall_id: r for r in (await self.session.scalars(select(StallStats))).all()}

    # --- 任务侧：写（不提交） ---

    def set_dish_stats(self, existing: dict[int, DishStats], dish_id: int, m: DishMetrics) -> None:
        row = existing.get(dish_id)
        if row is None:
            row = DishStats(dish_id=dish_id)
            self.session.add(row)
            existing[dish_id] = row
        row.score_7d = m.score_7d
        row.good_rate_7d = m.good_rate_7d
        row.review_count_7d = m.review_count_7d
        row.score_all = m.score_all
        row.review_count_all = m.review_count_all
        row.last_review_at = m.last_review_at

    def set_stall_stats(
        self, existing: dict[int, StallStats], stall_id: int, m: StallMetrics
    ) -> None:
        row = existing.get(stall_id)
        if row is None:
            row = StallStats(stall_id=stall_id)
            self.session.add(row)
            existing[stall_id] = row
        row.score_7d = m.score_7d
        row.bad_count_24h = m.bad_count_24h
        row.review_count_24h = m.review_count_24h

    async def replace_snapshot(
        self,
        *,
        campus_id: int,
        canteen_id: int | None,
        ranking_type: str,
        payload: list[dict[str, Any]],
        generated_at: datetime,
    ) -> None:
        """同一维度只保留最新一份：先删旧再插新。"""
        await self.session.execute(
            delete(RankingSnapshot).where(
                RankingSnapshot.campus_id == campus_id,
                RankingSnapshot.canteen_id.is_(None)
                if canteen_id is None
                else RankingSnapshot.canteen_id == canteen_id,
                RankingSnapshot.meal_slot.is_(None),
                RankingSnapshot.ranking_type == ranking_type,
            )
        )
        self.session.add(
            RankingSnapshot(
                campus_id=campus_id,
                canteen_id=canteen_id,
                meal_slot=None,
                ranking_type=ranking_type,
                payload_json=payload,
                generated_at=generated_at,
            )
        )

    # --- 读快照（任务与接口共用） ---

    async def get_latest_snapshot(
        self, campus_id: int, canteen_id: int | None, ranking_type: str
    ) -> RankingSnapshot | None:
        stmt = (
            select(RankingSnapshot)
            .where(
                RankingSnapshot.campus_id == campus_id,
                RankingSnapshot.canteen_id.is_(None)
                if canteen_id is None
                else RankingSnapshot.canteen_id == canteen_id,
                RankingSnapshot.meal_slot.is_(None),
                RankingSnapshot.ranking_type == ranking_type,
            )
            .order_by(RankingSnapshot.generated_at.desc(), RankingSnapshot.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def first_campus_id(self) -> int | None:
        return await self.session.scalar(select(Campus.id).order_by(Campus.id).limit(1))

    async def list_dish_briefs(self, dish_ids: list[int]) -> dict[int, tuple[Dish, Stall, Canteen]]:
        if not dish_ids:
            return {}
        stmt = (
            select(Dish, Stall, Canteen)
            .join(Stall, Stall.id == Dish.stall_id)
            .join(Canteen, Canteen.id == Stall.canteen_id)
            .where(Dish.id.in_(dish_ids))
        )
        return {d.id: (d, s, c) for d, s, c in (await self.session.execute(stmt)).all()}
