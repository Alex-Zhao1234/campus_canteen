"""榜单任务：全量重算 stats（衰减生效）并写快照，同一维度只留最新一份。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import (
    Campus,
    Canteen,
    Dish,
    DishStats,
    RankingSnapshot,
    Review,
    Stall,
    StallStats,
    User,
)
from app.tasks.rankings import rebuild_rankings

NOW = datetime(2026, 11, 9, 12, 0)


@pytest.fixture
async def world(db):
    """主校区：二食堂(香锅窗口: 荤/素/冷门) + 三食堂(面窗: 牛肉面)；两位用户。"""
    campus = Campus(name="主校区")
    c2 = Canteen(name="二食堂", campus=campus)
    c3 = Canteen(name="三食堂", campus=campus)
    hotpot = Stall(name="川味香锅", floor=3, canteen=c2)
    noodle = Stall(name="面窗", floor=1, canteen=c3)
    meat = Dish(name="香锅(荤)", price_cents=1800, stall=hotpot)
    veg = Dish(name="香锅(素)", price_cents=1200, stall=hotpot)
    cold = Dish(name="冷门菜", price_cents=900, stall=hotpot)  # 只有 8 天前一条评价
    off = Dish(name="下架菜", price_cents=100, stall=hotpot, is_active=False)
    beef = Dish(name="牛肉面", price_cents=1500, stall=noodle)
    u1 = User(email_hash="a" * 64, nickname="甲", campus=campus)
    u2 = User(email_hash="b" * 64, nickname="乙", campus=campus)
    db.add_all([meat, veg, cold, off, beef, u1, u2])
    await db.flush()

    def rv(user, dish, verdict, age=timedelta(0), hidden=False):
        return Review(
            user_id=user.id,
            dish_id=dish.id,
            stall_id=dish.stall_id,
            verdict=verdict,
            created_at=NOW - age,
            is_hidden=hidden,
        )

    db.add_all(
        [
            rv(u1, meat, "good"),
            rv(u2, meat, "good", timedelta(days=2)),
            rv(u2, meat, "bad", timedelta(hours=1), hidden=True),  # 已隐藏，不计
            rv(u1, veg, "bad"),
            rv(u2, veg, "bad", timedelta(hours=2)),
            rv(u1, cold, "good", timedelta(days=8)),
            rv(u1, beef, "good", timedelta(days=3)),
            rv(u2, off, "good"),  # 下架菜上的评价仍属于该窗口的事件
        ]
    )
    # 一条过期的 stats，任务应覆盖它
    db.add(DishStats(dish_id=beef.id, score_7d=0.9, review_count_7d=9, review_count_all=9))
    await db.commit()
    return {
        "campus": campus.id,
        "c2": c2.id,
        "c3": c3.id,
        "hotpot": hotpot.id,
        "noodle": noodle.id,
        "meat": meat.id,
        "veg": veg.id,
        "cold": cold.id,
        "off": off.id,
        "beef": beef.id,
        "u1": u1,
        "u2": u2,
    }


async def test_rebuild_refreshes_stats_with_decay_for_every_active_dish(db, world):
    summary = await rebuild_rankings(db, now=NOW)
    assert summary.dishes == 4  # 下架菜不算
    assert summary.stalls == 2

    beef = await db.get(DishStats, world["beef"])
    assert beef.review_count_7d == 1  # 过期 stats 被覆盖
    assert beef.score_7d == pytest.approx(0.2)  # 3 天前一条 good：0.5/(0.5+2)

    meat = await db.get(DishStats, world["meat"])
    assert meat.review_count_7d == 2  # 隐藏的那条不计

    cold = await db.get(DishStats, world["cold"])
    assert cold.review_count_7d == 0 and cold.review_count_all == 1

    assert await db.get(DishStats, world["off"]) is None

    hotpot = await db.get(StallStats, world["hotpot"])
    # 24h 内：荤 good(now)、素 bad×2、下架菜 good；2 天前的荤 good 与隐藏的 bad 不计
    assert hotpot.bad_count_24h == 2 and hotpot.review_count_24h == 4


async def test_rebuild_writes_campus_wide_and_per_canteen_snapshots(db, world):
    summary = await rebuild_rankings(db, now=NOW)
    assert summary.snapshots == 6  # (全校 + 2 食堂) × (good, bad)

    rows = (await db.scalars(select(RankingSnapshot))).all()
    keys = {(r.canteen_id, r.ranking_type) for r in rows}
    assert keys == {
        (None, "good"),
        (None, "bad"),
        (world["c2"], "good"),
        (world["c2"], "bad"),
        (world["c3"], "good"),
        (world["c3"], "bad"),
    }
    assert all(r.campus_id == world["campus"] and r.meal_slot is None for r in rows)
    assert all(r.generated_at == NOW for r in rows)


async def test_campus_good_ranking_content_in_cold_start(db, world):
    await rebuild_rankings(db, now=NOW)
    snap = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id.is_(None), RankingSnapshot.ranking_type == "good"
        )
    )
    # 冷启动门槛 1 条：荤(2 good) > 牛肉面(1 good, 3 天前)
    # 素(2 bad) 负分不进好评榜；冷门菜 7 日内无评价不入榜
    ids = [item["dish_id"] for item in snap.payload_json]
    assert ids == [world["meat"], world["beef"]]
    top = snap.payload_json[0]
    assert top["rank"] == 1 and top["review_count_7d"] == 2 and top["delta"] is None
    assert top["score"] > 0

    bad = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id.is_(None), RankingSnapshot.ranking_type == "bad"
        )
    )
    assert [i["dish_id"] for i in bad.payload_json] == [world["veg"]]

    c3_good = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id == world["c3"], RankingSnapshot.ranking_type == "good"
        )
    )
    assert [i["dish_id"] for i in c3_good.payload_json] == [world["beef"]]


async def test_second_run_replaces_snapshots_and_computes_delta(db, world):
    await rebuild_rankings(db, now=NOW)
    # 牛肉面再来两条 good，应反超香锅(荤)
    later = NOW + timedelta(minutes=10)
    for u in (world["u1"], world["u2"]):
        db.add(
            Review(
                user_id=u.id,
                dish_id=world["beef"],
                stall_id=world["noodle"],
                verdict="good",
                created_at=later,
            )
        )
    await db.commit()

    await rebuild_rankings(db, now=later)
    assert await db.scalar(select(func.count()).select_from(RankingSnapshot)) == 6  # 没有堆积
    snap = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id.is_(None), RankingSnapshot.ranking_type == "good"
        )
    )
    assert snap.generated_at == later
    by_id = {i["dish_id"]: i for i in snap.payload_json}
    assert by_id[world["beef"]]["rank"] == 1 and by_id[world["beef"]]["delta"] == 1
    assert by_id[world["meat"]]["rank"] == 2 and by_id[world["meat"]]["delta"] == -1


async def test_rebuild_on_empty_db_is_noop(db):
    summary = await rebuild_rankings(db, now=NOW)
    assert (summary.dishes, summary.stalls, summary.snapshots) == (0, 0, 0)
