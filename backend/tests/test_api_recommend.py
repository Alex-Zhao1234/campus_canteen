"""GET /recommend/random：约束过滤 + 避雷 + 去重复 + 加权随机。"""

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Dish, DishStats, Review, Stall, StallStats, User
from app.models._mixins import utcnow
from app.services.auth_service import code_store


@pytest.fixture
async def world(engine):
    """二食堂：香锅窗口(荤 18 元辣 3 / 素 12 元辣 3 / 番茄蛋 8 元素不辣)，黄牌窗口(烂菜)；
    三食堂：面窗(牛肉面 15 元辣 1)。"""
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        campus = Campus(name="主校区")
        c2 = Canteen(name="二食堂", campus=campus)
        c3 = Canteen(name="三食堂", campus=campus)
        hotpot = Stall(name="川味香锅", floor=3, canteen=c2)
        flagged = Stall(name="黄牌窗口", floor=1, canteen=c2)
        noodle = Stall(name="面窗", floor=1, canteen=c3)
        meat = Dish(name="香锅(荤)", price_cents=1800, spicy_level=3, stall=hotpot)
        veg = Dish(name="香锅(素)", price_cents=1200, spicy_level=3, is_veg=True, stall=hotpot)
        egg = Dish(name="番茄炒蛋", price_cents=800, spicy_level=0, is_veg=True, stall=hotpot)
        rotten = Dish(name="烂菜", price_cents=500, stall=flagged)
        lowscore = Dish(name="差评菜", price_cents=600, stall=hotpot)
        off = Dish(name="下架菜", price_cents=100, stall=hotpot, is_active=False)
        beef = Dish(name="牛肉面", price_cents=1500, spicy_level=1, stall=noodle)
        db.add_all([meat, veg, egg, rotten, lowscore, off, beef])
        await db.flush()
        db.add_all(
            [
                DishStats(dish_id=meat.id, score_7d=0.6, review_count_7d=5),
                DishStats(dish_id=lowscore.id, score_7d=-0.5, review_count_7d=4),
                StallStats(stall_id=flagged.id, bad_count_24h=3, review_count_24h=4),
                StallStats(stall_id=hotpot.id, bad_count_24h=1, review_count_24h=6),
            ]
        )
        await db.commit()
        return {
            "c2": c2.id,
            "c3": c3.id,
            "hotpot": hotpot.id,
            "meat": meat.id,
            "veg": veg.id,
            "egg": egg.id,
            "rotten": rotten.id,
            "lowscore": lowscore.id,
            "off": off.id,
            "beef": beef.id,
            "db": factory,
        }


async def _ids(client, query="") -> set[int]:
    """多抽几次，收集所有出现过的菜 id（候选全集）。"""
    seen: set[int] = set()
    for _ in range(30):
        r = await client.get(f"/api/v1/recommend/random{query}")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        if data["pick"]:
            seen.add(data["pick"]["dish_id"])
        seen.update(a["dish_id"] for a in data["alternates"])
    return seen


async def test_response_shape(client, world):
    r = await client.get("/api/v1/recommend/random")
    data = r.json()["data"]
    assert set(data) == {"pick", "alternates", "candidate_count"}
    assert data["candidate_count"] == 4  # 荤、素、蛋、牛肉面
    assert len(data["alternates"]) == 2
    pick = data["pick"]
    assert set(pick) == {
        "dish_id",
        "dish_name",
        "stall_id",
        "stall_name",
        "canteen_id",
        "canteen_name",
        "price_cents",
        "spicy_level",
        "is_veg",
        "score_7d",
        "review_count_7d",
    }
    assert pick["dish_id"] not in {a["dish_id"] for a in data["alternates"]}


async def test_excludes_flagged_stall_low_score_and_inactive(client, world):
    seen = await _ids(client)
    assert seen == {world["meat"], world["veg"], world["egg"], world["beef"]}


async def test_budget_constraint(client, world):
    assert await _ids(client, "?budget=1000") == {world["egg"]}


async def test_spicy_constraint(client, world):
    assert await _ids(client, "?spicy=1") == {world["egg"], world["beef"]}


async def test_veg_constraint(client, world):
    assert await _ids(client, "?veg=true") == {world["veg"], world["egg"]}


async def test_canteen_constraint(client, world):
    assert await _ids(client, f"?canteen_id={world['c3']}") == {world["beef"]}


async def test_exclude_param_supports_reroll(client, world):
    seen = await _ids(client, f"?exclude={world['meat']},{world['veg']}")
    assert seen == {world["egg"], world["beef"]}


async def test_no_candidates_returns_null_pick(client, world):
    r = await client.get("/api/v1/recommend/random?budget=100")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data == {"pick": None, "alternates": [], "candidate_count": 0}


@pytest.mark.parametrize("query", ["?spicy=4", "?budget=-1", "?exclude=a,b"])
async def test_invalid_params_422(client, world, query):
    r = await client.get(f"/api/v1/recommend/random{query}")
    assert r.status_code == 422


async def test_logged_in_user_skips_dishes_reviewed_in_last_3_days(client, world):
    code = (await client.post("/api/v1/auth/send-code", json={"email": "u@test.edu.cn"})).json()[
        "data"
    ]["dev_code"]
    token = (
        await client.post("/api/v1/auth/verify", json={"email": "u@test.edu.cn", "code": code})
    ).json()["data"]["access_token"]
    async with world["db"]() as db:
        user = (await db.execute(User.__table__.select())).first()
        now = utcnow()
        db.add_all(
            [
                Review(
                    user_id=user.id,
                    dish_id=world["meat"],
                    stall_id=world["hotpot"],
                    verdict="good",
                    created_at=now - timedelta(days=1),
                ),
                Review(
                    user_id=user.id,
                    dish_id=world["egg"],
                    stall_id=world["hotpot"],
                    verdict="good",
                    created_at=now - timedelta(days=5),
                ),  # 超过 3 天，不排除
            ]
        )
        await db.commit()

    client.headers["Authorization"] = f"Bearer {token}"
    try:
        seen = await _ids(client)
    finally:
        del client.headers["Authorization"]
    assert seen == {world["veg"], world["egg"], world["beef"]}

    # 游客不受影响
    assert world["meat"] in await _ids(client)


async def test_garbage_token_is_treated_as_guest(client, world):
    r = await client.get("/api/v1/recommend/random", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 200
