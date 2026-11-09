"""榜单生成纯函数。输入各菜的指标，输出排好序的榜单；不碰数据库。见架构文档 7.2。"""

from dataclasses import dataclass
from typing import Literal

from app.recommender.scoring import (
    BAD_RANK_MAX_SCORE,
    COLD_START_TOTAL_REVIEWS,
    RANK_MIN_REVIEWS,
    RANK_SIZE,
)
from app.recommender.stats import DishMetrics

RankingType = Literal["good", "bad"]


@dataclass(frozen=True)
class RankedItem:
    dish_id: int
    rank: int
    score: float
    review_count_7d: int
    delta: int | None  # 相比上一份快照的名次变化，正数上升；None 为新上榜


def min_reviews_for(total_reviews: int) -> int:
    """冷启动期（全站评价少）把上榜门槛降到 1 条。"""
    return 1 if total_reviews < COLD_START_TOTAL_REVIEWS else RANK_MIN_REVIEWS


def build_ranking(
    ranking_type: RankingType,
    candidates: list[tuple[int, DishMetrics]],
    min_reviews: int,
    previous_ranks: dict[int, int] | None = None,
    size: int = RANK_SIZE,
) -> list[RankedItem]:
    eligible = [(d, m) for d, m in candidates if m.review_count_7d >= min_reviews]
    if ranking_type == "good":
        # 只收正分（只有踩雷的菜不该出现在好评榜）；分数高优先，同分评价多优先，再按 id 稳定
        eligible = [(d, m) for d, m in eligible if m.score_7d > 0]
        eligible.sort(key=lambda x: (-x[1].score_7d, -x[1].review_count_7d, x[0]))
    else:
        eligible = [(d, m) for d, m in eligible if m.score_7d < BAD_RANK_MAX_SCORE]
        eligible.sort(key=lambda x: (x[1].score_7d, -x[1].review_count_7d, x[0]))

    previous_ranks = previous_ranks or {}
    items: list[RankedItem] = []
    for rank, (dish_id, m) in enumerate(eligible[:size], start=1):
        prev = previous_ranks.get(dish_id)
        items.append(
            RankedItem(
                dish_id=dish_id,
                rank=rank,
                score=m.score_7d,
                review_count_7d=m.review_count_7d,
                delta=None if prev is None else prev - rank,
            )
        )
    return items
