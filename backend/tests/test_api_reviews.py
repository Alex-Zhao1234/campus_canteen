"""一键评价：POST /reviews、DELETE /reviews/{id}、GET /me/reviews、GET /tags。"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Dish, DishStats, Review, ReviewTag, Stall, StallStats
from app.services.auth_service import code_store
from app.tasks.seed import seed_tags


@pytest.fixture
async def world(engine):
    """一个校区/食堂/窗口，两道在售菜 + 一道下架菜，14 个预设标签。"""
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        stall = Stall(
            name="川味香锅", floor=3, canteen=Canteen(name="二食堂", campus=Campus(name="主校区"))
        )
        meat = Dish(name="麻辣香锅(荤)", price_cents=1800, stall=stall)
        veg = Dish(name="麻辣香锅(素)", price_cents=1200, stall=stall)
        off = Dish(name="下架菜", price_cents=100, stall=stall, is_active=False)
        db.add_all([meat, veg, off])
        await db.commit()
        await seed_tags(db)
        return {"stall_id": stall.id, "meat": meat.id, "veg": veg.id, "off": off.id, "db": factory}


async def _auth(client, email="u1@test.edu.cn") -> dict:
    code = (await client.post("/api/v1/auth/send-code", json={"email": email})).json()["data"][
        "dev_code"
    ]
    r = await client.post("/api/v1/auth/verify", json={"email": email, "code": code})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _post(client, headers, **body):
    return await client.post("/api/v1/reviews", json=body, headers=headers)


async def test_tags_lists_preset_set(client, world):
    r = await client.get("/api/v1/tags")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 14
    assert {"code": "too_salty", "label": "偏咸", "category": "taste"} in data


async def test_post_review_requires_login(client, world):
    r = await client.post("/api/v1/reviews", json={"dish_id": world["meat"], "verdict": "good"})
    assert r.status_code == 401


async def test_post_review_writes_event_and_refreshes_stats(client, world):
    h = await _auth(client)
    r = await _post(
        client,
        h,
        dish_id=world["meat"],
        verdict="good",
        tag_codes=["portion_good", "worth_it"],
        comment="量大实惠",
        meal_slot="lunch",
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["dish_id"] == world["meat"]
    assert data["review_id"] > 0
    assert data["dish_stats"]["review_count_7d"] == 1
    assert data["dish_stats"]["good_rate_7d"] == 1.0
    assert data["dish_stats"]["score_7d"] == pytest.approx(1 / 3)

    async with world["db"]() as db:
        review = await db.get(Review, data["review_id"])
        assert review.verdict == "good"
        assert review.stall_id == world["stall_id"]  # 冗余 stall_id 已填
        assert review.comment == "量大实惠"
        assert review.meal_slot == "lunch"
        tag_count = await db.scalar(select(func.count()).select_from(ReviewTag))
        assert tag_count == 2
        dish_stats = await db.get(DishStats, world["meat"])
        assert dish_stats.review_count_all == 1
        stall_stats = await db.get(StallStats, world["stall_id"])
        assert stall_stats.review_count_24h == 1
        assert stall_stats.bad_count_24h == 0


async def test_bad_review_counts_toward_stall_alert_metrics(client, world):
    h = await _auth(client)
    r = await _post(client, h, dish_id=world["meat"], verdict="bad")
    assert r.status_code == 201
    assert r.json()["data"]["dish_stats"]["score_7d"] == pytest.approx(-0.5)
    async with world["db"]() as db:
        stall_stats = await db.get(StallStats, world["stall_id"])
        assert stall_stats.bad_count_24h == 1


async def test_same_dish_same_day_twice_is_409(client, world):
    h = await _auth(client)
    assert (await _post(client, h, dish_id=world["meat"], verdict="good")).status_code == 201
    r = await _post(client, h, dish_id=world["meat"], verdict="bad")
    assert r.status_code == 409
    assert r.json()["code"] == 409
    assert "今天" in r.json()["msg"]


async def test_different_users_can_review_same_dish_same_day(client, world):
    h1 = await _auth(client, "a@test.edu.cn")
    h2 = await _auth(client, "b@test.edu.cn")
    assert (await _post(client, h1, dish_id=world["meat"], verdict="good")).status_code == 201
    r = await _post(client, h2, dish_id=world["meat"], verdict="bad")
    assert r.status_code == 201
    assert r.json()["data"]["dish_stats"]["review_count_7d"] == 2


async def test_unknown_or_inactive_dish_404(client, world):
    h = await _auth(client)
    assert (await _post(client, h, dish_id=9999, verdict="good")).status_code == 404
    assert (await _post(client, h, dish_id=world["off"], verdict="good")).status_code == 404


async def test_unknown_tag_code_400(client, world):
    h = await _auth(client)
    r = await _post(client, h, dish_id=world["meat"], verdict="good", tag_codes=["nonsense"])
    assert r.status_code == 400
    assert "nonsense" in r.json()["msg"]


@pytest.mark.parametrize(
    "body",
    [
        {"verdict": "great"},
        {"verdict": "good", "meal_slot": "brunch"},
        {"verdict": "good", "comment": "x" * 101},
    ],
)
async def test_invalid_payload_422(client, world, body):
    h = await _auth(client)
    r = await _post(client, h, dish_id=world["meat"], **body)
    assert r.status_code == 422
    assert r.json()["code"] == 422


async def test_daily_review_cap_429(client, world):
    async with world["db"]() as db:
        dishes = [
            Dish(name=f"菜{i}", price_cents=500, stall_id=world["stall_id"]) for i in range(16)
        ]
        db.add_all(dishes)
        await db.commit()
        ids = [d.id for d in dishes]
    h = await _auth(client)
    for dish_id in ids[:15]:
        assert (await _post(client, h, dish_id=dish_id, verdict="ok")).status_code == 201
    r = await _post(client, h, dish_id=ids[15], verdict="ok")
    assert r.status_code == 429
    assert r.json()["code"] == 429


async def test_delete_own_review_hides_it_and_recomputes(client, world):
    h = await _auth(client)
    created = (await _post(client, h, dish_id=world["meat"], verdict="good")).json()["data"]
    r = await client.delete(f"/api/v1/reviews/{created['review_id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["dish_stats"]["review_count_7d"] == 0
    async with world["db"]() as db:
        review = await db.get(Review, created["review_id"])
        assert review.is_hidden is True  # 软删，行还在
        assert (await db.get(DishStats, world["meat"])).review_count_all == 0


async def test_delete_others_review_403(client, world):
    h1 = await _auth(client, "a@test.edu.cn")
    h2 = await _auth(client, "b@test.edu.cn")
    created = (await _post(client, h1, dish_id=world["meat"], verdict="good")).json()["data"]
    r = await client.delete(f"/api/v1/reviews/{created['review_id']}", headers=h2)
    assert r.status_code == 403
    assert r.json()["code"] == 403


async def test_delete_unknown_review_404(client, world):
    h = await _auth(client)
    assert (await client.delete("/api/v1/reviews/9999", headers=h)).status_code == 404


async def test_my_reviews_newest_first_without_hidden(client, world):
    h = await _auth(client)
    first = (
        await _post(client, h, dish_id=world["meat"], verdict="good", tag_codes=["fresh"])
    ).json()["data"]
    second = (await _post(client, h, dish_id=world["veg"], verdict="bad")).json()["data"]
    await client.delete(f"/api/v1/reviews/{second['review_id']}", headers=h)

    r = await client.get("/api/v1/me/reviews", headers=h)
    assert r.status_code == 200
    data = r.json()["data"]
    assert [x["id"] for x in data] == [first["review_id"]]
    item = data[0]
    assert item["dish_name"] == "麻辣香锅(荤)"
    assert item["stall_name"] == "川味香锅"
    assert item["verdict"] == "good"
    assert item["tags"] == [{"code": "fresh", "label": "新鲜", "category": "taste"}]
    assert item["created_at"]


async def test_my_reviews_requires_login(client, world):
    assert (await client.get("/api/v1/me/reviews")).status_code == 401
