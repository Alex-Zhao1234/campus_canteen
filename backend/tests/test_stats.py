"""从评价事件列表派生 dish_stats / stall_stats 的纯函数。公式见架构文档 7.1。"""

from datetime import datetime, timedelta

import pytest

from app.recommender.stats import (
    ReviewEvent,
    compute_dish_metrics,
    compute_stall_metrics,
)

NOW = datetime(2026, 11, 9, 12, 0)


def ev(verdict: str, age: timedelta = timedelta(0), trust: float = 1.0) -> ReviewEvent:
    return ReviewEvent(verdict=verdict, created_at=NOW - age, trust_score=trust)


def test_empty_gives_zeros():
    m = compute_dish_metrics([], NOW)
    assert m.score_7d == 0.0
    assert m.good_rate_7d == 0.0
    assert m.review_count_7d == 0
    assert m.score_all == 0.0
    assert m.review_count_all == 0
    assert m.last_review_at is None


def test_single_fresh_good_is_bayes_smoothed():
    # base 1.0 × weight 1.0 / (1.0 + k=2) = 1/3
    m = compute_dish_metrics([ev("good")], NOW)
    assert m.score_7d == pytest.approx(1 / 3)
    assert m.review_count_7d == 1
    assert m.good_rate_7d == 1.0


def test_bad_weighs_more_than_good():
    good = compute_dish_metrics([ev("good")], NOW).score_7d
    bad = compute_dish_metrics([ev("bad")], NOW).score_7d
    assert bad == pytest.approx(-1.5 / 3)
    assert abs(bad) > abs(good)


def test_three_day_old_review_has_half_weight():
    # weight 0.5 → 0.5 / (0.5 + 2) = 0.2
    m = compute_dish_metrics([ev("good", timedelta(days=3))], NOW)
    assert m.score_7d == pytest.approx(0.2)


def test_trust_score_scales_weight():
    m = compute_dish_metrics([ev("good", trust=0.5)], NOW)
    assert m.score_7d == pytest.approx(0.5 / 2.5)


def test_reviews_older_than_7_days_leave_7d_window_but_stay_in_all():
    m = compute_dish_metrics([ev("good", timedelta(days=8)), ev("bad")], NOW)
    assert m.review_count_7d == 1
    assert m.review_count_all == 2
    assert m.score_7d == pytest.approx(-1.5 / 3)
    assert m.score_all > m.score_7d  # 旧 good 权重已很小，但确实把总分拉高了一点
    assert m.last_review_at == NOW


def test_good_rate_is_share_of_good_in_7d():
    m = compute_dish_metrics([ev("good"), ev("good"), ev("bad"), ev("ok")], NOW)
    assert m.good_rate_7d == pytest.approx(0.5)


def test_stall_metrics_count_recent_bad():
    events = [
        ev("bad"),
        ev("bad", timedelta(hours=23)),
        ev("bad", timedelta(hours=25)),  # 超出 24h
        ev("good", timedelta(hours=1)),
    ]
    m = compute_stall_metrics(events, NOW)
    assert m.bad_count_24h == 2
    assert m.review_count_24h == 3
    assert m.score_7d < 0
