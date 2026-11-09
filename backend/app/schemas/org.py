"""组织结构接口的响应模型（DTO）。与 ORM 模型分离：ORM 描述表，这里描述接口。"""

from pydantic import BaseModel, ConfigDict


class _FromORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CanteenOut(_FromORM):
    id: int
    campus_id: int
    name: str
    floors: int


class StallStatsOut(_FromORM):
    score_7d: float = 0.0
    bad_count_24h: int = 0
    review_count_24h: int = 0


class DishStatsOut(_FromORM):
    score_7d: float = 0.0
    good_rate_7d: float = 0.0
    review_count_7d: int = 0
    review_count_all: int = 0


class StallBase(_FromORM):
    """窗口自身字段，可直接从 ORM 对象校验。"""

    id: int
    canteen_id: int
    floor: int
    name: str
    cuisine_type: str | None
    position_desc: str | None
    today_status: str


class StallOut(StallBase):
    stats: StallStatsOut


class DishBase(_FromORM):
    id: int
    stall_id: int
    name: str
    price_cents: int
    spicy_level: int
    is_veg: bool
    portion_hint: str | None
    dish_type: str


class DishOut(DishBase):
    stats: DishStatsOut


class StallDetailOut(StallOut):
    dishes: list[DishOut]


class StallBriefOut(BaseModel):
    id: int
    name: str
    floor: int
    canteen_id: int
    canteen_name: str


class DishDetailOut(DishOut):
    stall: StallBriefOut
