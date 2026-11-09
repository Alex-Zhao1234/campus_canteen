"""随机推荐的抽样纯函数：softmax(score / temperature) 加权、不放回。"""

import math
import random
from collections.abc import Sequence

from app.recommender.scoring import (
    ALERT_YELLOW_BAD_COUNT,
    ALERT_YELLOW_BAD_RATIO,
    RANDOM_TEMPERATURE,
)


def softmax_weights(
    scores: Sequence[float], temperature: float = RANDOM_TEMPERATURE
) -> list[float]:
    if not scores:
        return []
    scaled = [s / temperature for s in scores]
    m = max(scaled)  # 减最大值防溢出
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def weighted_sample(
    candidates: Sequence[tuple[int, float]],
    k: int,
    temperature: float = RANDOM_TEMPERATURE,
    rng: random.Random | None = None,
) -> list[int]:
    """从 (id, score) 列表里按 softmax 权重不放回抽 k 个，返回 id 列表，先抽到的在前。"""
    rng = rng or random.Random()
    pool = list(candidates)
    picked: list[int] = []
    while pool and len(picked) < k:
        weights = softmax_weights([s for _, s in pool], temperature)
        idx = rng.choices(range(len(pool)), weights=weights, k=1)[0]
        picked.append(pool.pop(idx)[0])
    return picked


def is_stall_flagged(bad_count_24h: int, review_count_24h: int) -> bool:
    """黄牌条件。stall_alert 表是 M2 的，MVP 直接用 stall_stats 现算。"""
    if review_count_24h == 0:
        return False
    return (
        bad_count_24h >= ALERT_YELLOW_BAD_COUNT
        and bad_count_24h / review_count_24h >= ALERT_YELLOW_BAD_RATIO
    )
