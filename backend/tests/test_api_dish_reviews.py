"""菜品评论区：GET /dishes/{id}/reviews（只读、游标分页、含无文字评价）。"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Dish, Stall
from app.services.auth_service import code_store
from app.tasks.seed import seed_tags


@pytest.fixture
async def world(engine):
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        stall = Stall(
            name="川味香锅", floor=3, canteen=Canteen(name="二食堂", campus=Campus(name="主校区"))
        )
        meat = Dish(name="麻辣香锅(荤)", price_cents=1800, stall=stall)
        off = Dish(name="下架菜", price_cents=100, stall=stall, is_active=False)
        db.add_all([meat, off])
        await db.commit()
        await seed_tags(db)
        return {"meat": meat.id, "off": off.id, "db": factory}


async def _auth(client, email) -> dict:
    code = (await client.post("/api/v1/auth/send-code", json={"email": email})).json()["data"][
        "dev_code"
    ]
    r = await client.post("/api/v1/auth/verify", json={"email": email, "code": code})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _post(client, headers, **body) -> int:
    r = await client.post("/api/v1/reviews", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]["review_id"]


def _url(dish_id, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"/api/v1/dishes/{dish_id}/reviews" + (f"?{qs}" if qs else "")


async def test_lists_newest_first_with_nickname_verdict_comment_tags(client, world):
    h1 = await _auth(client, "a@test.edu.cn")
    h2 = await _auth(client, "b@test.edu.cn")
    await _post(
        client,
        h1,
        dish_id=world["meat"],
        verdict="good",
        comment="量大实惠",
        tag_codes=["worth_it"],
    )
    await _post(client, h2, dish_id=world["meat"], verdict="bad")  # 只点表情没写字

    r = await client.get(_url(world["meat"]))
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    items = data["items"]
    assert [i["verdict"] for i in items] == ["bad", "good"]  # 新的在前
    assert items[0]["comment"] is None  # 无文字评价也要出现在评论区
    assert items[1]["comment"] == "量大实惠"
    assert items[1]["tags"] == [{"code": "worth_it", "label": "性价比高", "category": "price"}]
    assert items[1]["user_nickname"].startswith("同学#")
    assert items[1]["created_at"]
    assert data["next_before_id"] is None


async def test_hidden_reviews_are_excluded(client, world):
    h = await _auth(client, "a@test.edu.cn")
    rid = await _post(client, h, dish_id=world["meat"], verdict="good", comment="还行")
    assert (await client.delete(f"/api/v1/reviews/{rid}", headers=h)).status_code == 200

    r = await client.get(_url(world["meat"]))
    assert r.json()["data"]["items"] == []


async def test_unknown_or_inactive_dish_404(client, world):
    assert (await client.get(_url(9999))).status_code == 404
    assert (await client.get(_url(world["off"]))).status_code == 404


async def test_cursor_pagination_by_before_id(client, world):
    ids = []
    for mail in ("a", "b", "c"):
        h = await _auth(client, f"{mail}@test.edu.cn")
        ids.append(await _post(client, h, dish_id=world["meat"], verdict="ok"))

    page1 = (await client.get(_url(world["meat"], limit=2))).json()["data"]
    assert [i["id"] for i in page1["items"]] == [ids[2], ids[1]]
    assert page1["next_before_id"] == ids[1]

    r = await client.get(_url(world["meat"], limit=2, before_id=page1["next_before_id"]))
    page2 = r.json()["data"]
    assert [i["id"] for i in page2["items"]] == [ids[0]]
    assert page2["next_before_id"] is None


async def test_is_mine_marks_only_own_reviews(client, world):
    h1 = await _auth(client, "a@test.edu.cn")
    h2 = await _auth(client, "b@test.edu.cn")
    mine = await _post(client, h1, dish_id=world["meat"], verdict="good")
    await _post(client, h2, dish_id=world["meat"], verdict="bad")

    items = (await client.get(_url(world["meat"]), headers=h1)).json()["data"]["items"]
    assert {i["id"]: i["is_mine"] for i in items} == {mine: True, items[0]["id"]: False}

    guest = (await client.get(_url(world["meat"]))).json()["data"]["items"]
    assert all(i["is_mine"] is False for i in guest)
