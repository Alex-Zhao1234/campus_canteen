"""种子导入：预设标签 + CSV 组织结构，必须幂等。"""

from pathlib import Path

from sqlalchemy import func, select

from app.models import Campus, Canteen, Dish, Seat, Stall, Tag
from app.tasks.seed import PRESET_TAGS, seed_dishes, seed_seats, seed_tags

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "dishes.csv"


async def _count(db, model) -> int:
    return await db.scalar(select(func.count()).select_from(model))


async def test_seed_tags_inserts_preset_set(db):
    created = await seed_tags(db)
    assert created == len(PRESET_TAGS) == 14
    assert await _count(db, Tag) == 14
    salty = await db.scalar(select(Tag).where(Tag.code == "too_salty"))
    assert salty.label == "偏咸"
    assert salty.category == "taste"


async def test_seed_tags_is_idempotent(db):
    await seed_tags(db)
    created_again = await seed_tags(db)
    assert created_again == 0
    assert await _count(db, Tag) == 14


async def test_seed_dishes_builds_org_chain(db):
    stats = await seed_dishes(db, CSV_PATH)
    assert stats == {"campus": 1, "canteen": 2, "stall": 13, "dish": 38}
    assert await _count(db, Campus) == 1
    assert await _count(db, Canteen) == 2
    assert await _count(db, Stall) == 13
    assert await _count(db, Dish) == 38


async def test_seed_dishes_maps_csv_fields(db):
    await seed_dishes(db, CSV_PATH)
    dish = await db.scalar(select(Dish).where(Dish.name == "麻辣香锅(素)"))
    assert dish.price_cents == 1200
    assert dish.spicy_level == 3
    assert dish.is_veg is True
    assert dish.dish_type == "常驻"
    assert dish.stall.name == "川味香锅"
    assert dish.stall.floor == 3
    assert dish.stall.cuisine_type == "川菜"
    assert dish.stall.canteen.name == "二食堂"
    assert dish.stall.canteen.campus.name == "主校区"

    baozi = await db.scalar(select(Dish).where(Dish.name == "肉包"))
    assert baozi.is_veg is False
    assert dish.image_url == "/dish-images/malaxiangguo-su.jpg"


async def test_seed_backfills_image_url_on_existing_dish(db):
    await seed_dishes(db, CSV_PATH)
    fanqie = await db.scalar(select(Dish).where(Dish.name == "番茄炒蛋"))
    fanqie.image_url = None
    await db.commit()
    await seed_dishes(db, CSV_PATH)  # 再跑一次只补空图，不新建
    await db.refresh(fanqie)
    assert fanqie.image_url == "/dish-images/fanqiechaodan.jpg"


async def test_seed_dishes_is_idempotent(db):
    await seed_dishes(db, CSV_PATH)
    stats = await seed_dishes(db, CSV_PATH)
    assert stats == {"campus": 0, "canteen": 0, "stall": 0, "dish": 0}
    assert await _count(db, Dish) == 38
    assert await _count(db, Stall) == 13


async def test_seed_dishes_reuses_existing_canteen_under_campus(db):
    # 预先存在同名食堂时应复用，而不是再建一个
    db.add(Canteen(name="二食堂", floors=3, campus=Campus(name="主校区")))
    await db.commit()
    stats = await seed_dishes(db, CSV_PATH)
    assert stats["campus"] == 0
    assert stats["canteen"] == 1  # 二食堂复用，只新建三食堂
    assert await _count(db, Canteen) == 2


SEATS_CSV = CSV_PATH.with_name("seats.csv")


async def test_seed_seats_creates_seats_per_floor(db):
    await seed_dishes(db, CSV_PATH)
    stats = await seed_seats(db, SEATS_CSV)
    assert stats == {"seat": 600, "skipped_rows": 0}
    assert await _count(db, Seat) == 600
    c2 = await db.scalar(select(Canteen).where(Canteen.name == "二食堂"))
    first = await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-1F-001"))
    assert first is not None and first.canteen_id == c2.id and first.floor == 1
    assert await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-3F-080")) is not None
    assert await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-3F-081")) is None


async def test_seed_seats_is_idempotent(db):
    await seed_dishes(db, CSV_PATH)
    await seed_seats(db, SEATS_CSV)
    again = await seed_seats(db, SEATS_CSV)
    assert again["seat"] == 0
    assert await _count(db, Seat) == 600


async def test_seed_seats_skips_unknown_canteen(db, tmp_path):
    await seed_dishes(db, CSV_PATH)
    csv_file = tmp_path / "seats.csv"
    csv_file.write_text(
        "canteen_name,floor,seat_count\n不存在食堂,1,10\n二食堂,1,2\n", encoding="utf-8"
    )
    stats = await seed_seats(db, csv_file)
    assert stats == {"seat": 2, "skipped_rows": 1}
