"""评分常量与公式，见 docs/架构设计.md 第 7.1 节。"""

from datetime import datetime

VERDICT_BASE = {"good": 1.0, "ok": 0.0, "bad": -1.5}
HALF_LIFE_DAYS = 3.0
BAYES_K = 2.0
# 统计窗口：菜品/窗口的"近期"评分看 7 天，窗口预警看 24 小时
RECENT_WINDOW_DAYS = 7
ALERT_WINDOW_HOURS = 24
# 榜单（7.2）：上榜门槛、冷启动阈值、踩雷榜分数上限、每榜条数
RANK_MIN_REVIEWS = 3
COLD_START_TOTAL_REVIEWS = 500
BAD_RANK_MAX_SCORE = -0.3
RANK_SIZE = 10


def time_weight(created_at: datetime, now: datetime, trust_score: float = 1.0) -> float:
    age_days = max((now - created_at).total_seconds() / 86400, 0.0)
    return (0.5 ** (age_days / HALF_LIFE_DAYS)) * trust_score


def aggregate_score(weighted: list[tuple[float, float]]) -> float:
    """weighted: [(base, weight), ...] → 贝叶斯平滑后的分数。"""
    num = sum(b * w for b, w in weighted)
    den = sum(w for _, w in weighted) + BAYES_K
    return num / den if den else 0.0


# 随机推荐（7.4 第一阶段）：softmax 温度、备选数、排除近 N 天评过的菜
RANDOM_TEMPERATURE = 0.5
RANDOM_ALTERNATES = 2
RECENT_REVIEWED_EXCLUDE_DAYS = 3
# 黄牌窗口条件（7.3 bad_surge 黄牌）：近 24h bad ≥ 3 且占比 ≥ 50%
ALERT_YELLOW_BAD_COUNT = 3
ALERT_YELLOW_BAD_RATIO = 0.5
