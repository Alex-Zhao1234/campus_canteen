from pydantic import BaseModel


class RecommendItemOut(BaseModel):
    dish_id: int
    dish_name: str
    stall_id: int
    stall_name: str
    canteen_id: int
    canteen_name: str
    price_cents: int
    spicy_level: int
    is_veg: bool
    score_7d: float
    review_count_7d: int


class RandomRecommendOut(BaseModel):
    pick: RecommendItemOut | None
    alternates: list[RecommendItemOut]
    candidate_count: int
