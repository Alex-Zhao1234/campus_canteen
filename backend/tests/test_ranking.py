"""榜单纯函数：排序、门槛、冷启动、踩雷过滤、名次变化。规则见架构文档 7.2。"""

from app.recommender.ranking import build_ranking, min_reviews_for
from app.recommender.scoring import (
    BAD_RANK_MAX_SCORE,
    COLD_START_TOTAL_REVIEWS,
    RANK_MIN_REVIEWS,
    RANK_SIZE,
)
from app.recommender.stats import DishMetrics


def m(score: float, count: int = 5) -> DishMetrics:
    return DishMetrics(score_7d=score, review_count_7d=count)


def test_min_reviews_drops_to_one_in_cold_start():
    assert min_reviews_for(COLD_START_TOTAL_REVIEWS - 1) == 1
    assert min_reviews_for(COLD_START_TOTAL_REVIEWS) == RANK_MIN_REVIEWS


def test_good_ranking_sorts_desc_and_applies_threshold():
    items = build_ranking(
        "good",
        [(1, m(0.2)), (2, m(0.8)), (3, m(0.9, count=2)), (4, m(0.5))],
        min_reviews=3,
    )
    assert [i.dish_id for i in items] == [2, 4, 1]  # 3 号评价数不够
    assert [i.rank for i in items] == [1, 2, 3]
    assert items[0].score == 0.8
    assert items[0].review_count_7d == 5


def test_good_ranking_excludes_non_positive_scores():
    items = build_ranking("good", [(1, m(0.3)), (2, m(0.0)), (3, m(-0.5))], min_reviews=1)
    assert [i.dish_id for i in items] == [1]


def test_bad_ranking_sorts_asc_and_requires_clearly_negative():
    items = build_ranking(
        "bad",
        [(1, m(-0.1)), (2, m(-0.9)), (3, m(-0.4)), (4, m(BAD_RANK_MAX_SCORE))],
        min_reviews=1,
    )
    assert [i.dish_id for i in items] == [2, 3]  # -0.1 和恰好 -0.3 都不算踩雷


def test_delta_is_rank_change_since_previous_snapshot():
    previous = {1: 1, 2: 2, 3: 3}  # dish_id -> 上次名次
    items = build_ranking(
        "good", [(1, m(0.5)), (2, m(0.9)), (4, m(0.7))], min_reviews=1, previous_ranks=previous
    )
    by_id = {i.dish_id: i for i in items}
    assert by_id[2].rank == 1 and by_id[2].delta == 1  # 2 → 1，上升 1
    assert by_id[1].rank == 3 and by_id[1].delta == -2  # 1 → 3，下降 2
    assert by_id[4].rank == 2 and by_id[4].delta is None  # 新上榜


def test_ranking_is_truncated_to_size():
    cands = [(i, m(i / 100)) for i in range(1, RANK_SIZE + 10)]
    items = build_ranking("good", cands, min_reviews=1)
    assert len(items) == RANK_SIZE
    assert items[0].dish_id == RANK_SIZE + 9


def test_ties_break_by_more_reviews_then_dish_id():
    items = build_ranking("good", [(5, m(0.5, 3)), (2, m(0.5, 9)), (1, m(0.5, 3))], min_reviews=1)
    assert [i.dish_id for i in items] == [2, 1, 5]
