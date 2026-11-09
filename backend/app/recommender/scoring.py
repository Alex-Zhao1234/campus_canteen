"""评分常量与公式，见 docs/架构设计.md 第 7.1 节。"""

from datetime import datetime

VERDICT_BASE = {"good": 1.0, "ok": 0.0, "bad": -1.5}
HALF_LIFE_DAYS = 3.0
BAYES_K = 2.0


def time_weight(created_at: datetime, now: datetime, trust_score: float = 1.0) -> float:
    age_days = max((now - created_at).total_seconds() / 86400, 0.0)
    return (0.5 ** (age_days / HALF_LIFE_DAYS)) * trust_score


def aggregate_score(weighted: list[tuple[float, float]]) -> float:
    """weighted: [(base, weight), ...] → 贝叶斯平滑后的分数。"""
    num = sum(b * w for b, w in weighted)
    den = sum(w for _, w in weighted) + BAYES_K
    return num / den if den else 0.0
