"""一键评价：写事件 → 就地重算该菜/该窗口的 stats。

规则：菜品需在售；标签 code 需存在；单人单菜单日一评由唯一索引 uq_review_daily 保证，
这里只把 IntegrityError 翻译成 409；单人单日上限 15 条（架构文档 10.2）。
"""

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.models import Review, User
from app.models._mixins import utcnow
from app.recommender.stats import compute_dish_metrics, compute_stall_metrics
from app.repositories.review_repo import ReviewRepository
from app.schemas.org import DishStatsOut
from app.schemas.review import (
    MyReviewOut,
    ReviewCreatedOut,
    ReviewCreateIn,
    ReviewDeletedOut,
    TagOut,
)
from app.services.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
)

DAILY_REVIEW_CAP = 15
BEIJING_OFFSET = timedelta(hours=8)


def beijing_day_start_utc(now: datetime) -> datetime:
    """now 为 UTC naive；返回其所在北京日 00:00 对应的 UTC 时刻。"""
    beijing_date = (now + BEIJING_OFFSET).date()
    return datetime.combine(beijing_date, datetime.min.time()) - BEIJING_OFFSET


class ReviewService:
    def __init__(self, repo: ReviewRepository) -> None:
        self.repo = repo

    async def list_tags(self) -> list[TagOut]:
        return [TagOut.model_validate(t) for t in await self.repo.list_tags()]

    async def create(self, user: User, data: ReviewCreateIn) -> ReviewCreatedOut:
        dish = await self.repo.get_active_dish(data.dish_id)
        if dish is None:
            raise NotFoundError("菜品", data.dish_id)

        codes = list(dict.fromkeys(data.tag_codes))  # 去重保序
        tags = await self.repo.get_tags_by_codes(codes)
        unknown = set(codes) - {t.code for t in tags}
        if unknown:
            raise BadRequestError(f"未知标签：{', '.join(sorted(unknown))}")

        now = utcnow()
        today_count = await self.repo.count_user_reviews_since(user.id, beijing_day_start_utc(now))
        if today_count >= DAILY_REVIEW_CAP:
            raise RateLimitError(f"今天已评价 {DAILY_REVIEW_CAP} 条，明天再来吧")

        review = Review(
            user_id=user.id,
            dish_id=dish.id,
            stall_id=dish.stall_id,
            verdict=data.verdict,
            comment=data.comment,
            meal_slot=data.meal_slot,
            created_at=now,
        )
        try:
            await self.repo.add_review(review, tags)
        except IntegrityError as e:
            await self.repo.session.rollback()
            if "uq_review_daily" in str(e.orig):
                raise ConflictError("今天已经评价过这道菜了") from e
            raise

        stats = await self._refresh_stats(dish.id, dish.stall_id, now)
        return ReviewCreatedOut(review_id=review.id, dish_id=dish.id, dish_stats=stats)

    async def delete(self, user: User, review_id: int) -> ReviewDeletedOut:
        review = await self.repo.get_review(review_id)
        if review is None or review.is_hidden:
            raise NotFoundError("评价", review_id)
        if review.user_id != user.id:
            raise ForbiddenError("只能删除自己的评价")
        await self.repo.hide_review(review)
        stats = await self._refresh_stats(review.dish_id, review.stall_id, utcnow())
        return ReviewDeletedOut(review_id=review.id, dish_id=review.dish_id, dish_stats=stats)

    async def list_mine(self, user: User) -> list[MyReviewOut]:
        rows = await self.repo.list_user_reviews(user.id)
        return [
            MyReviewOut(
                id=r.id,
                dish_id=d.id,
                dish_name=d.name,
                stall_id=d.stall.id,
                stall_name=d.stall.name,
                verdict=r.verdict,
                comment=r.comment,
                meal_slot=r.meal_slot,
                tags=[TagOut.model_validate(t) for t in r.tags],
                created_at=r.created_at,
            )
            for r, d in rows
        ]

    async def _refresh_stats(self, dish_id: int, stall_id: int, now: datetime) -> DishStatsOut:
        dish_metrics = compute_dish_metrics(await self.repo.events_for_dish(dish_id), now)
        stall_metrics = compute_stall_metrics(await self.repo.events_for_stall(stall_id), now)
        row = await self.repo.upsert_dish_stats(dish_id, dish_metrics)
        await self.repo.upsert_stall_stats(stall_id, stall_metrics)
        return DishStatsOut.model_validate(row)
