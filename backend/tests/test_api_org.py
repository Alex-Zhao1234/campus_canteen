"""组织结构只读接口：/canteens、/canteens/{id}/stalls、/stalls/{id}、/dishes/{id}。"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Dish, DishStats, Stall, StallStats


@pytest.fixture
async def seeded(engine):
    """两个校区；主校区二食堂下两个窗口（一个停用），川味香锅下两道菜（一道停用）。"""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        main = Campus(name="主校区")
        other = Campus(name="东校区")
        c2 = Canteen(name="二食堂", floors=3, campus=main)
        c_other = Canteen(name="东苑食堂", floors=1, campus=other)
        c_closed = Canteen(name="已关停食堂", floors=1, campus=main, is_active=False)
        hotpot = Stall(name="川味香锅", floor=3, cuisine_type="川菜", canteen=c2)
        gone = Stall(name="停业窗口", floor=1, canteen=c2, is_active=False)
        dish_meat = Dish(name="麻辣香锅(荤)", price_cents=1800, spicy_level=3, stall=hotpot)
        dish_veg = Dish(
            name="麻辣香锅(素)", price_cents=1200, spicy_level=3, is_veg=True, stall=hotpot
        )
        dish_off = Dish(name="下架菜", price_cents=100, stall=hotpot, is_active=False)
        # 分层 flush，保证 id 顺序与书写顺序一致（列表接口按 id 排序）
        db.add_all([main, other])
        await db.flush()
        db.add_all([c2, c_other, c_closed])
        await db.flush()
        db.add_all([hotpot, gone])
        await db.flush()
        db.add_all([dish_meat, dish_veg, dish_off])
        await db.flush()
        db.add(StallStats(stall_id=hotpot.id, score_7d=0.42, bad_count_24h=1, review_count_24h=5))
        db.add(
            DishStats(
                dish_id=dish_meat.id,
                score_7d=0.8,
                good_rate_7d=0.9,
                review_count_7d=10,
                review_count_all=30,
            )
        )
        await db.commit()
        return {
            "main_id": main.id,
            "other_id": other.id,
            "c2_id": c2.id,
            "hotpot_id": hotpot.id,
            "gone_id": gone.id,
            "meat_id": dish_meat.id,
            "veg_id": dish_veg.id,
            "off_id": dish_off.id,
        }


def _ok(r):
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0 and body["msg"] == "ok"
    return body["data"]


async def test_list_canteens_returns_active_only(client, seeded):
    data = _ok(await client.get("/api/v1/canteens"))
    names = [c["name"] for c in data]
    assert names == ["二食堂", "东苑食堂"]
    assert data[0] == {
        "id": seeded["c2_id"],
        "campus_id": seeded["main_id"],
        "name": "二食堂",
        "floors": 3,
    }


async def test_list_canteens_filters_by_campus(client, seeded):
    data = _ok(await client.get(f"/api/v1/canteens?campus_id={seeded['other_id']}"))
    assert [c["name"] for c in data] == ["东苑食堂"]


async def test_list_stalls_attaches_stats(client, seeded):
    data = _ok(await client.get(f"/api/v1/canteens/{seeded['c2_id']}/stalls"))
    assert [s["name"] for s in data] == ["川味香锅"]  # 停用窗口不出现
    stall = data[0]
    assert stall["floor"] == 3
    assert stall["cuisine_type"] == "川菜"
    assert stall["today_status"] == "unknown"
    assert stall["stats"] == {"score_7d": 0.42, "bad_count_24h": 1, "review_count_24h": 5}


async def test_list_stalls_unknown_canteen_404(client, seeded):
    r = await client.get("/api/v1/canteens/9999/stalls")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == 404
    assert body["data"] is None
    assert "食堂" in body["msg"]


async def test_stall_detail_lists_active_dishes_with_stats(client, seeded):
    data = _ok(await client.get(f"/api/v1/stalls/{seeded['hotpot_id']}"))
    assert data["id"] == seeded["hotpot_id"]
    assert data["canteen_id"] == seeded["c2_id"]
    assert data["name"] == "川味香锅"
    dishes = {d["name"]: d for d in data["dishes"]}
    assert set(dishes) == {"麻辣香锅(荤)", "麻辣香锅(素)"}  # 下架菜不出现
    meat = dishes["麻辣香锅(荤)"]
    assert meat["price_cents"] == 1800
    assert meat["is_veg"] is False
    assert meat["stats"] == {
        "score_7d": 0.8,
        "good_rate_7d": 0.9,
        "review_count_7d": 10,
        "review_count_all": 30,
    }
    # 没有 dish_stats 记录时给全零，而不是 null
    assert dishes["麻辣香锅(素)"]["stats"] == {
        "score_7d": 0.0,
        "good_rate_7d": 0.0,
        "review_count_7d": 0,
        "review_count_all": 0,
    }


async def test_stall_detail_404(client, seeded):
    r = await client.get("/api/v1/stalls/9999")
    assert r.status_code == 404
    assert r.json()["code"] == 404


async def test_dish_detail_includes_stall_brief(client, seeded):
    data = _ok(await client.get(f"/api/v1/dishes/{seeded['veg_id']}"))
    assert data["name"] == "麻辣香锅(素)"
    assert data["is_veg"] is True
    assert data["dish_type"] == "常驻"
    assert data["stall"] == {
        "id": seeded["hotpot_id"],
        "name": "川味香锅",
        "floor": 3,
        "canteen_id": seeded["c2_id"],
        "canteen_name": "二食堂",
    }


async def test_dish_detail_404(client, seeded):
    r = await client.get("/api/v1/dishes/9999")
    assert r.status_code == 404
    assert r.json()["code"] == 404
