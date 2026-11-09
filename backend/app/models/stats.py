"""派生 / 快照表。全部由定时任务从 review 事件流重算，可随时清空重建。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import IdMixin, utcnow

RANKING_TYPES = ("good", "bad", "new", "trending")


class DishStats(Base):
    __tablename__ = "dish_stats"

    dish_id: Mapped[int] = mapped_column(ForeignKey("dish.id"), primary_key=True)
    score_7d: Mapped[float] = mapped_column(default=0.0, nullable=False)
    good_rate_7d: Mapped[float] = mapped_column(default=0.0, nullable=False)
    review_count_7d: Mapped[int] = mapped_column(default=0, nullable=False)
    score_all: Mapped[float] = mapped_column(default=0.0, nullable=False)
    review_count_all: Mapped[int] = mapped_column(default=0, nullable=False)
    last_review_at: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)


class StallStats(Base):
    __tablename__ = "stall_stats"

    stall_id: Mapped[int] = mapped_column(ForeignKey("stall.id"), primary_key=True)
    score_7d: Mapped[float] = mapped_column(default=0.0, nullable=False)
    bad_count_24h: Mapped[int] = mapped_column(default=0, nullable=False)
    review_count_24h: Mapped[int] = mapped_column(default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)


class RankingSnapshot(IdMixin, Base):
    """榜单快照。payload_json: [{dish_id, score, rank, delta}, ...]"""

    __tablename__ = "ranking_snapshot"
    __table_args__ = (
        CheckConstraint(
            "ranking_type IN (" + ", ".join(f"'{t}'" for t in RANKING_TYPES) + ")",
            name="ck_ranking_type",
        ),
    )

    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), nullable=False)
    canteen_id: Mapped[int | None] = mapped_column(ForeignKey("canteen.id"))
    meal_slot: Mapped[str | None] = mapped_column(String(10))
    ranking_type: Mapped[str] = mapped_column(String(10), nullable=False)
    payload_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
