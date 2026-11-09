"""GET /rankings/today 只读快照，并关联菜名/窗口名。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Dish, Review, Stall, User
from app.tasks.rankings import rebuild_rankings

NOW = datetime(2026, 11, 9, 12, 0)


@pytest.fixture
async def snapshot(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        campus = Campus(name="主校区")
        c2 = Canteen(name="二食堂", campus=campus)
        c3 = Canteen(name="三食堂", campus=campus)
        hotpot = Stall(name="川味香锅", floor=3, canteen=c2)
        noodle = Stall(name="面窗", floor=1, canteen=c3)
        meat = Dish(name="香锅(荤)", price_cents=1800, stall=hotpot)
        veg = Dish(name="香锅(素)", price_cents=1200, stall=hotpot)
        beef = Dish(name="牛肉面", price_cents=1500, stall=noodle)
        u = User(email_hash="a" * 64, nickname="甲", campus=campus)
        db.add_all([meat, veg, beef, u])
        await db.flush()
        db.add_all(
            [
                Review(
                    user_id=u.id,
                    dish_id=meat.id,
                    stall_id=hotpot.id,
                    verdict="good",
                    created_at=NOW,
                ),
                Review(
                    user_id=u.id, dish_id=veg.id, stall_id=hotpot.id, verdict="bad", created_at=NOW
                ),
                Review(
                    user_id=u.id,
                    dish_id=beef.id,
                    stall_id=noodle.id,
                    verdict="good",
                    created_at=NOW - timedelta(days=1),
                ),
            ]
        )
        await db.commit()
        await rebuild_rankings(db, now=NOW)
        return {"campus": campus.id, "c2": c2.id, "c3": c3.id, "meat": meat.id, "beef": beef.id}


async def test_today_good_ranking_campus_wide(client, snapshot):
    r = await client.get("/api/v1/rankings/today?type=good")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["ranking_type"] == "good"
    assert data["campus_id"] == snapshot["campus"]
    assert data["canteen_id"] is None
    assert data["generated_at"].startswith("2026-11-09T12:00:00")
    assert [i["dish_id"] for i in data["items"]] == [snapshot["meat"], snapshot["beef"]]
    top = data["items"][0]
    assert top == {
        "rank": 1,
        "dish_id": snapshot["meat"],
        "dish_name": "香锅(荤)",
        "stall_id": top["stall_id"],
        "stall_name": "川味香锅",
        "canteen_id": snapshot["c2"],
        "canteen_name": "二食堂",
        "price_cents": 1800,
        "image_url": None,
        "score": pytest.approx(1 / 3),
        "review_count_7d": 1,
        "delta": None,
    }


async def test_today_bad_ranking_filtered_by_canteen(client, snapshot):
    r = await client.get(f"/api/v1/rankings/today?type=bad&canteen_id={snapshot['c2']}")
    data = r.json()["data"]
    assert data["canteen_id"] == snapshot["c2"]
    assert [i["dish_name"] for i in data["items"]] == ["香锅(素)"]

    r = await client.get(f"/api/v1/rankings/today?type=bad&canteen_id={snapshot['c3']}")
    assert r.json()["data"]["items"] == []


async def test_type_defaults_to_good(client, snapshot):
    r = await client.get("/api/v1/rankings/today")
    assert r.json()["data"]["ranking_type"] == "good"


async def test_invalid_type_422(client, snapshot):
    r = await client.get("/api/v1/rankings/today?type=trending")
    assert r.status_code == 422


async def test_no_snapshot_yet_returns_empty(client):
    r = await client.get("/api/v1/rankings/today?type=good")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["items"] == [] and data["generated_at"] is None
