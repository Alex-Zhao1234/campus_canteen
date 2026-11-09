from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RankingTypeIn = Literal["good", "bad"]


class RankingItemOut(BaseModel):
    rank: int
    dish_id: int
    dish_name: str
    stall_id: int
    stall_name: str
    canteen_id: int
    canteen_name: str
    price_cents: int
    image_url: str | None = None
    score: float
    review_count_7d: int
    delta: int | None


class RankingOut(BaseModel):
    ranking_type: str
    campus_id: int | None
    canteen_id: int | None
    generated_at: datetime | None
    items: list[RankingItemOut]
