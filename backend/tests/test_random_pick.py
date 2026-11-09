"""加权随机抽样：softmax(score / temperature)，不放回。"""

import random
from collections import Counter

from app.recommender.random_pick import softmax_weights, weighted_sample


def test_softmax_weights_sum_to_one_and_favor_higher_score():
    w = softmax_weights([0.0, 0.5, -0.5], temperature=0.5)
    assert sum(w) == 1.0 or abs(sum(w) - 1.0) < 1e-9
    assert w[1] > w[0] > w[2]


def test_lower_temperature_is_greedier():
    hot = softmax_weights([0.0, 0.5], temperature=2.0)
    cold = softmax_weights([0.0, 0.5], temperature=0.2)
    assert cold[1] > hot[1]


def test_sample_is_without_replacement_and_keeps_order_of_draw():
    rng = random.Random(1)
    picked = weighted_sample([(1, 0.1), (2, 0.2), (3, 0.3), (4, 0.4)], k=3, rng=rng)
    assert len(picked) == 3
    assert len(set(picked)) == 3


def test_sample_returns_all_when_fewer_than_k():
    picked = weighted_sample([(7, 0.0), (8, 0.0)], k=3, rng=random.Random(0))
    assert sorted(picked) == [7, 8]


def test_sample_empty_is_empty():
    assert weighted_sample([], k=3, rng=random.Random(0)) == []


def test_high_score_wins_first_place_most_of_the_time():
    rng = random.Random(42)
    firsts = Counter(
        weighted_sample([(1, 0.6), (2, 0.0), (3, -0.2)], k=1, rng=rng)[0] for _ in range(2000)
    )
    # softmax(score/0.5)：e^1.2 : e^0 : e^-0.4 ≈ 3.32 : 1 : 0.67 → 1 号约 2/3
    assert firsts[1] > firsts[2] > firsts[3]
    assert 0.6 < firsts[1] / 2000 < 0.75
