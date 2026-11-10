"""ORM 模型统一出口。导入本包即可让 Base.metadata 包含全部表。"""

from app.models.org import Campus, Canteen, Dish, Stall
from app.models.review import MEAL_SLOTS, VERDICTS, Review, ReviewTag, Tag
from app.models.seat import Seat, SeatState
from app.models.stats import RANKING_TYPES, DishStats, RankingSnapshot, StallStats
from app.models.user import User

__all__ = [
    "MEAL_SLOTS",
    "RANKING_TYPES",
    "VERDICTS",
    "Campus",
    "Canteen",
    "Dish",
    "DishStats",
    "RankingSnapshot",
    "Review",
    "ReviewTag",
    "Seat",
    "SeatState",
    "Stall",
    "StallStats",
    "Tag",
    "User",
]
