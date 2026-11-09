"""演示评价：评价表为空时写入一批分布合理的评价，让榜单/踩雷标记一打开就有内容；幂等。"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select

from app.models import Dish, Review, StallStats, User
from app.recommender.scoring import RANK_SIZE
from app.tasks.demo import seed_demo_reviews
from app.tasks.rankings import rebuild_rankings
from app.tasks.seed import seed_dishes, seed_tags

CSV = Path(__file__).resolve().parents[2] / "data" / "seed" / "dishes.csv"
NOW = datetime(2026, 11, 9, 12, 0)


async def _count(db, model):
    return await db.scalar(select(func.count()).select_from(model))


async def test_writes_reviews_once(db):
    await seed_tags(db)
    await seed_dishes(db, CSV)
    n = await seed_demo_reviews(db, now=NOW)
    assert n >= 15
    assert await _count(db, Review) == n
    assert await _count(db, User) >= 4
    assert await seed_demo_reviews(db, now=NOW) == 0  # 已有评价则不动
    assert await _count(db, Review) == n


async def test_rankings_have_content_after_demo(db):
    await seed_tags(db)
    await seed_dishes(db, CSV)
    await seed_demo_reviews(db, now=NOW)
    await rebuild_rankings(db, now=NOW)

    from app.models import RankingSnapshot

    good = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id.is_(None), RankingSnapshot.ranking_type == "good"
        )
    )
    bad = await db.scalar(
        select(RankingSnapshot).where(
            RankingSnapshot.canteen_id.is_(None), RankingSnapshot.ranking_type == "bad"
        )
    )
    names = {d.id: d.name for d in (await db.scalars(select(Dish))).all()}
    good_names = [names[i["dish_id"]] for i in good.payload_json]
    bad_names = [names[i["dish_id"]] for i in bad.payload_json]
    # 两榜都要满 10 条，且榜首固定
    assert len(good_names) == RANK_SIZE == 10
    assert len(bad_names) == RANK_SIZE == 10
    assert good_names[0] == "麻辣香锅(荤)"
    assert bad_names[0] == "鱼香肉丝"
    assert set(good_names).isdisjoint(bad_names)

    # 家常小炒窗口近 24h 踩雷 ≥ 3 → 食堂页出现预警标记、随机推荐排除
    stall_id = await db.scalar(select(Dish.stall_id).where(Dish.name == "鱼香肉丝"))
    ss = await db.get(StallStats, stall_id)
    assert ss.bad_count_24h >= 3
    # 其它窗口不应被黄牌误伤：近 24h 踩雷 ≥ 3 的窗口只有这一个
    flagged = [
        r.stall_id for r in (await db.scalars(select(StallStats))).all() if r.bad_count_24h >= 3
    ]
    assert flagged == [stall_id]


async def test_noop_without_dishes(db):
    assert await seed_demo_reviews(db, now=NOW) == 0
