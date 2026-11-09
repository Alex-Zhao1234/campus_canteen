"""派生表：dish_stats / stall_stats 以外键为主键，ranking_snapshot 存 JSON 载荷。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Campus, Canteen, Dish, DishStats, RankingSnapshot, Stall, StallStats


async def _seed(db):
    campus = Campus(name="主校区")
    canteen = Canteen(name="二食堂", campus=campus)
    stall = Stall(name="家常小炒", floor=2, canteen=canteen)
    dish = Dish(name="番茄炒蛋", price_cents=800, stall=stall)
    db.add(dish)
    await db.commit()
    return campus, canteen, stall, dish


async def test_dish_stats_is_one_row_per_dish(db):
    _, _, _, dish = await _seed(db)
    db.add(DishStats(dish_id=dish.id, score_7d=0.4, good_rate_7d=0.8, review_count_7d=5))
    await db.commit()
    db.add(DishStats(dish_id=dish.id, score_7d=0.1))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_dish_stats_defaults_to_zero(db):
    _, _, _, dish = await _seed(db)
    db.add(DishStats(dish_id=dish.id))
    await db.commit()
    stats = await db.scalar(select(DishStats))
    assert stats.score_7d == 0.0
    assert stats.review_count_7d == 0
    assert stats.review_count_all == 0
    assert stats.last_review_at is None
    assert stats.updated_at is not None


async def test_stall_stats_requires_existing_stall(db):
    db.add(StallStats(stall_id=42))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_ranking_snapshot_roundtrips_json_payload(db):
    campus, canteen, _, dish = await _seed(db)
    payload = [{"dish_id": dish.id, "score": 0.42, "rank": 1, "delta": 0}]
    db.add(
        RankingSnapshot(
            campus_id=campus.id, canteen_id=canteen.id, ranking_type="good", payload_json=payload
        )
    )
    await db.commit()
    snap = await db.scalar(select(RankingSnapshot))
    assert snap.payload_json == payload
    assert snap.meal_slot is None
    assert snap.generated_at is not None


async def test_ranking_type_must_be_known_value(db):
    campus, _, _, _ = await _seed(db)
    db.add(RankingSnapshot(campus_id=campus.id, ranking_type="worst", payload_json=[]))
    with pytest.raises(IntegrityError):
        await db.commit()
