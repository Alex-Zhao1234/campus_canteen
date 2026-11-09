"""随机推荐：硬约束过滤 → 避雷排除 → 去重复 → softmax 加权不放回抽样。见 7.4 第一阶段。"""

import random
from datetime import timedelta

from app.models import User
from app.models._mixins import utcnow
from app.recommender.random_pick import is_stall_flagged, weighted_sample
from app.recommender.scoring import (
    BAD_RANK_MAX_SCORE,
    RANDOM_ALTERNATES,
    RECENT_REVIEWED_EXCLUDE_DAYS,
)
from app.repositories.org_repo import OrgRepository
from app.repositories.recommend_repo import CandidateRow, RecommendRepository
from app.schemas.recommend import RandomRecommendOut, RecommendItemOut


def _to_item(row: CandidateRow) -> RecommendItemOut:
    dish, stall, canteen, ds, _ = row
    return RecommendItemOut(
        dish_id=dish.id,
        dish_name=dish.name,
        stall_id=stall.id,
        stall_name=stall.name,
        canteen_id=canteen.id,
        canteen_name=canteen.name,
        price_cents=dish.price_cents,
        spicy_level=dish.spicy_level,
        is_veg=dish.is_veg,
        score_7d=ds.score_7d if ds else 0.0,
        review_count_7d=ds.review_count_7d if ds else 0,
    )


class RecommendService:
    def __init__(
        self, repo: RecommendRepository, org: OrgRepository, rng: random.Random | None = None
    ) -> None:
        self.repo = repo
        self.org = org
        self.rng = rng

    async def random(
        self,
        *,
        user: User | None,
        campus_id: int | None,
        canteen_id: int | None,
        budget: int | None,
        spicy: int | None,
        veg: bool | None,
        exclude: set[int],
    ) -> RandomRecommendOut:
        empty = RandomRecommendOut(pick=None, alternates=[], candidate_count=0)
        if campus_id is None:
            campus_id = await self.org.first_campus_id()
            if campus_id is None:
                return empty

        rows = await self.repo.list_candidates(
            campus_id=campus_id, canteen_id=canteen_id, budget=budget, spicy=spicy, veg=veg
        )

        skip = set(exclude)
        if user is not None:
            since = utcnow() - timedelta(days=RECENT_REVIEWED_EXCLUDE_DAYS)
            skip |= await self.repo.recently_reviewed_dish_ids(user.id, since)

        candidates: list[CandidateRow] = []
        for row in rows:
            dish, _, _, ds, ss = row
            if dish.id in skip:
                continue
            if ds is not None and ds.score_7d < BAD_RANK_MAX_SCORE:
                continue  # 踩雷门槛
            if ss is not None and is_stall_flagged(ss.bad_count_24h, ss.review_count_24h):
                continue  # 黄牌窗口
            candidates.append(row)

        if not candidates:
            return empty

        by_id = {row[0].id: row for row in candidates}
        scored = [(row[0].id, row[3].score_7d if row[3] else 0.0) for row in candidates]
        picked = weighted_sample(scored, k=1 + RANDOM_ALTERNATES, rng=self.rng)
        items = [_to_item(by_id[i]) for i in picked]
        return RandomRecommendOut(
            pick=items[0], alternates=items[1:], candidate_count=len(candidates)
        )
