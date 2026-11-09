"""从评价事件派生 dish_stats / stall_stats 的纯函数。

输入是已经过滤掉 is_hidden 的评价事件列表，输出指标值；不碰数据库。
服务层负责查评价、调这里、写回 stats 表。榜单任务复用同一套函数。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.recommender.scoring import (
    ALERT_WINDOW_HOURS,
    RECENT_WINDOW_DAYS,
    VERDICT_BASE,
    aggregate_score,
    time_weight,
)


@dataclass(frozen=True)
class ReviewEvent:
    verdict: str
    created_at: datetime
    trust_score: float = 1.0


@dataclass(frozen=True)
class DishMetrics:
    score_7d: float = 0.0
    good_rate_7d: float = 0.0
    review_count_7d: int = 0
    score_all: float = 0.0
    review_count_all: int = 0
    last_review_at: datetime | None = None


@dataclass(frozen=True)
class StallMetrics:
    score_7d: float = 0.0
    bad_count_24h: int = 0
    review_count_24h: int = 0


def _score(events: list[ReviewEvent], now: datetime) -> float:
    return aggregate_score(
        [(VERDICT_BASE[e.verdict], time_weight(e.created_at, now, e.trust_score)) for e in events]
    )


def _recent(events: list[ReviewEvent], now: datetime, span: timedelta) -> list[ReviewEvent]:
    cutoff = now - span
    return [e for e in events if e.created_at >= cutoff]


def compute_dish_metrics(events: list[ReviewEvent], now: datetime) -> DishMetrics:
    if not events:
        return DishMetrics()
    recent = _recent(events, now, timedelta(days=RECENT_WINDOW_DAYS))
    good_recent = sum(1 for e in recent if e.verdict == "good")
    return DishMetrics(
        score_7d=_score(recent, now),
        good_rate_7d=good_recent / len(recent) if recent else 0.0,
        review_count_7d=len(recent),
        score_all=_score(events, now),
        review_count_all=len(events),
        last_review_at=max(e.created_at for e in events),
    )


def compute_stall_metrics(events: list[ReviewEvent], now: datetime) -> StallMetrics:
    if not events:
        return StallMetrics()
    recent = _recent(events, now, timedelta(days=RECENT_WINDOW_DAYS))
    last_24h = _recent(events, now, timedelta(hours=ALERT_WINDOW_HOURS))
    return StallMetrics(
        score_7d=_score(recent, now),
        bad_count_24h=sum(1 for e in last_24h if e.verdict == "bad"),
        review_count_24h=len(last_24h),
    )
