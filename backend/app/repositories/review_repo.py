"""评价事件流与派生 stats 的数据访问。review 只 INSERT，软删只改 is_hidden。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dish, DishStats, Review, StallStats, Tag, User
from app.recommender.stats import DishMetrics, ReviewEvent, StallMetrics


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 读 ---

    async def get_active_dish(self, dish_id: int) -> Dish | None:
        return await self.session.scalar(
            select(Dish).where(Dish.id == dish_id, Dish.is_active.is_(True))
        )

    async def list_tags(self) -> list[Tag]:
        return list((await self.session.scalars(select(Tag).order_by(Tag.id))).all())

    async def get_tags_by_codes(self, codes: list[str]) -> list[Tag]:
        if not codes:
            return []
        return list((await self.session.scalars(select(Tag).where(Tag.code.in_(codes)))).all())

    async def get_review(self, review_id: int) -> Review | None:
        return await self.session.get(Review, review_id)

    async def count_user_reviews_since(self, user_id: int, since: datetime) -> int:
        return await self.session.scalar(
            select(func.count())
            .select_from(Review)
            .where(Review.user_id == user_id, Review.created_at >= since)
        )

    async def list_user_reviews(self, user_id: int, limit: int = 50) -> list[tuple[Review, Dish]]:
        stmt = (
            select(Review, Dish)
            .join(Dish, Dish.id == Review.dish_id)
            .where(Review.user_id == user_id, Review.is_hidden.is_(False))
            .order_by(Review.created_at.desc(), Review.id.desc())
            .limit(limit)
        )
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]

    async def list_dish_reviews(
        self, dish_id: int, limit: int, before_id: int | None
    ) -> list[tuple[Review, User]]:
        """菜品评论区：未隐藏评价按 id 倒序（id 单调递增，等价于时间倒序），游标 before_id。"""
        stmt = (
            select(Review, User)
            .join(User, User.id == Review.user_id)
            .where(Review.dish_id == dish_id, Review.is_hidden.is_(False))
            .order_by(Review.id.desc())
            .limit(limit)
        )
        if before_id is not None:
            stmt = stmt.where(Review.id < before_id)
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]

    async def _events(self, where) -> list[ReviewEvent]:
        stmt = (
            select(Review.verdict, Review.created_at, User.trust_score)
            .join(User, User.id == Review.user_id)
            .where(where, Review.is_hidden.is_(False))
        )
        rows = (await self.session.execute(stmt)).all()
        return [ReviewEvent(verdict=v, created_at=t, trust_score=s) for v, t, s in rows]

    async def events_for_dish(self, dish_id: int) -> list[ReviewEvent]:
        return await self._events(Review.dish_id == dish_id)

    async def events_for_stall(self, stall_id: int) -> list[ReviewEvent]:
        return await self._events(Review.stall_id == stall_id)

    # --- 写 ---

    async def add_review(self, review: Review, tags: list[Tag]) -> Review:
        """INSERT review + review_tag 并提交。唯一索引冲突会抛 IntegrityError，由服务层翻译。"""
        review.tags = tags
        self.session.add(review)
        await self.session.commit()
        return review

    async def hide_review(self, review: Review) -> None:
        review.is_hidden = True
        await self.session.commit()

    async def upsert_dish_stats(self, dish_id: int, m: DishMetrics) -> DishStats:
        row = await self.session.get(DishStats, dish_id)
        if row is None:
            row = DishStats(dish_id=dish_id)
            self.session.add(row)
        row.score_7d = m.score_7d
        row.good_rate_7d = m.good_rate_7d
        row.review_count_7d = m.review_count_7d
        row.score_all = m.score_all
        row.review_count_all = m.review_count_all
        row.last_review_at = m.last_review_at
        await self.session.commit()
        return row

    async def upsert_stall_stats(self, stall_id: int, m: StallMetrics) -> StallStats:
        row = await self.session.get(StallStats, stall_id)
        if row is None:
            row = StallStats(stall_id=stall_id)
            self.session.add(row)
        row.score_7d = m.score_7d
        row.bad_count_24h = m.bad_count_24h
        row.review_count_24h = m.review_count_24h
        await self.session.commit()
        return row
