"""评价事件流：verdict / meal_slot 约束、单人单菜单日一评、标签多对多。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Campus, Canteen, Dish, Review, ReviewTag, Stall, Tag, User


async def _seed(db):
    campus = Campus(name="主校区")
    stall = Stall(name="家常小炒", floor=2, canteen=Canteen(name="二食堂", campus=campus))
    dish = Dish(name="番茄炒蛋", price_cents=800, stall=stall)
    user = User(email_hash="a" * 64, nickname="小明", campus=campus)
    db.add_all([dish, user])
    await db.commit()
    return user, dish


async def test_review_defaults_and_stall_denormalised(db):
    user, dish = await _seed(db)
    db.add(Review(user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="good"))
    await db.commit()
    review = await db.scalar(select(Review))
    assert review.is_hidden is False
    assert review.comment is None
    assert review.meal_slot is None
    assert review.stall_id == dish.stall_id
    assert review.created_at is not None


async def test_user_defaults(db):
    user, _ = await _seed(db)
    assert user.trust_score == 1.0
    assert user.created_at is not None
    assert user.last_active_at is None


async def test_user_email_hash_is_unique(db):
    user, _ = await _seed(db)
    db.add(User(email_hash="a" * 64, nickname="冒名者", campus_id=user.campus_id))
    with pytest.raises(IntegrityError):
        await db.commit()


@pytest.mark.parametrize("bad_verdict", ["great", "GOOD", ""])
async def test_verdict_must_be_good_ok_bad(db, bad_verdict):
    user, dish = await _seed(db)
    db.add(Review(user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict=bad_verdict))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_meal_slot_must_be_known_value(db):
    user, dish = await _seed(db)
    db.add(
        Review(
            user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id,
            verdict="ok", meal_slot="brunch",
        )
    )
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_same_user_same_dish_same_day_only_once(db):
    user, dish = await _seed(db)
    at = datetime(2026, 11, 9, 12, 0)
    db.add(
        Review(
            user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="good", created_at=at
        )
    )
    await db.commit()
    db.add(
        Review(
            user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="bad",
            created_at=at + timedelta(hours=6),
        )
    )
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_same_user_same_dish_next_day_is_allowed(db):
    user, dish = await _seed(db)
    at = datetime(2026, 11, 9, 12, 0)
    db.add(
        Review(
            user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="good", created_at=at
        )
    )
    await db.commit()
    db.add(
        Review(
            user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="bad",
            created_at=at + timedelta(days=1),
        )
    )
    await db.commit()
    assert len((await db.scalars(select(Review))).all()) == 2


async def test_review_can_carry_tags(db):
    user, dish = await _seed(db)
    tag = Tag(code="portion_less", label="份量少了", category="portion")
    review = Review(user_id=user.id, dish_id=dish.id, stall_id=dish.stall_id, verdict="bad")
    db.add_all([tag, review])
    await db.commit()
    db.add(ReviewTag(review_id=review.id, tag_id=tag.id))
    await db.commit()
    loaded = await db.scalar(select(Review))
    assert [t.code for t in loaded.tags] == ["portion_less"]


async def test_tag_code_is_unique(db):
    db.add_all([
        Tag(code="price_up", label="涨价了", category="price"),
        Tag(code="price_up", label="又涨了", category="price"),
    ])
    with pytest.raises(IntegrityError):
        await db.commit()
