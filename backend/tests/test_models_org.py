"""组织结构模型：campus → canteen → stall → dish。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Campus, Canteen, Dish, Stall


async def _seed_chain(db):
    campus = Campus(name="主校区")
    canteen = Canteen(name="二食堂", floors=3, campus=campus)
    stall = Stall(name="川味香锅", floor=3, cuisine_type="川菜", canteen=canteen)
    dish = Dish(name="麻辣香锅(荤)", price_cents=1800, spicy_level=3, stall=stall)
    db.add(dish)
    await db.commit()
    return campus, canteen, stall, dish


async def test_dish_links_back_to_canteen_through_stall(db):
    await _seed_chain(db)
    dish = await db.scalar(select(Dish).where(Dish.name == "麻辣香锅(荤)"))
    assert dish.stall.name == "川味香锅"
    assert dish.stall.canteen.name == "二食堂"
    assert dish.stall.canteen.campus.name == "主校区"


async def test_dish_defaults(db):
    _, _, _, dish = await _seed_chain(db)
    assert dish.is_veg is False
    assert dish.is_active is True
    assert dish.dish_type == "常驻"
    assert dish.created_at is not None


async def test_stall_today_status_defaults_to_unknown(db):
    _, _, stall, _ = await _seed_chain(db)
    assert stall.today_status == "unknown"
    assert stall.is_active is True


async def test_dish_requires_existing_stall(db):
    db.add(Dish(name="幽灵菜", price_cents=100, stall_id=999))
    with pytest.raises(IntegrityError):
        await db.commit()
