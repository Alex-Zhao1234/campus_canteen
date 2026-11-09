from datetime import datetime, timedelta

from app.recommender.scoring import aggregate_score, time_weight


def test_half_life():
    now = datetime(2026, 11, 9)
    assert abs(time_weight(now - timedelta(days=3), now) - 0.5) < 1e-6


def test_bayes_smoothing_keeps_single_good_review_modest():
    assert aggregate_score([(1.0, 1.0)]) < 0.5
