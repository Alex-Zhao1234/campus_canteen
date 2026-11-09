"""评价接口的请求/响应模型。verdict / meal_slot 取值与 app.models.review 常量一致。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.org import DishStatsOut

Verdict = Literal["good", "ok", "bad"]
MealSlot = Literal["breakfast", "lunch", "dinner", "night"]


class ReviewCreateIn(BaseModel):
    dish_id: int
    verdict: Verdict
    tag_codes: list[str] = Field(default_factory=list, max_length=10)
    comment: str | None = Field(default=None, max_length=100)
    meal_slot: MealSlot | None = None


class ReviewCreatedOut(BaseModel):
    review_id: int
    dish_id: int
    dish_stats: DishStatsOut


class ReviewDeletedOut(BaseModel):
    review_id: int
    dish_id: int
    dish_stats: DishStatsOut


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    category: str


class MyReviewOut(BaseModel):
    id: int
    dish_id: int
    dish_name: str
    stall_id: int
    stall_name: str
    verdict: str
    comment: str | None
    meal_slot: str | None
    tags: list[TagOut]
    created_at: datetime
