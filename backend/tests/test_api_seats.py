"""GET /seats/occupancy：登录用户按食堂 × 楼层看占用率与拥挤度。"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Seat, SeatState
from app.services.auth_service import code_store

URL = "/api/v1/seats/occupancy"
T0 = datetime(2026, 11, 10, 4, 0)
T1 = datetime(2026, 11, 10, 4, 5)


@pytest.fixture
async def world(engine):
    """主校区二食堂 floors=3：1 层 4 座(3 占, 另一座停用且占用)、2 层 2 座(0 占)、3 层无座位；
    三食堂 floors=1 停用；东校区东苑食堂 1 层 1 座。"""
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        main = Campus(name="主校区")
        east = Campus(name="东校区")
        c2 = Canteen(name="二食堂", floors=3, campus=main)
        c3 = Canteen(name="三食堂", floors=1, campus=main, is_active=False)
        ce = Canteen(name="东苑食堂", floors=1, campus=east)
        db.add_all([c2, c3, ce])
        await db.flush()
        seats = [
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-001"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-002"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-003"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-004"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-005", is_active=False),
            Seat(canteen_id=c2.id, floor=2, code="C1-2F-001"),
            Seat(canteen_id=c2.id, floor=2, code="C1-2F-002"),
            Seat(canteen_id=c3.id, floor=1, code="C2-1F-001"),
            Seat(canteen_id=ce.id, floor=1, code="C3-1F-001"),
        ]
        db.add_all(seats)
        await db.flush()
        by_code = {s.code: s for s in seats}

        def st(code, occ, updated):
            return SeatState(
                seat_id=by_code[code].id, is_occupied=occ, changed_at=T0, updated_at=updated
            )

        db.add_all(
            [
                st("C1-1F-001", True, T0),
                st("C1-1F-002", True, T1),
                st("C1-1F-003", True, T0),
                st("C1-1F-004", False, T0),
                st("C1-1F-005", True, T0),
            ]
        )
        await db.commit()
        return {"main_id": main.id, "east_id": east.id, "c2_id": c2.id, "ce_id": ce.id}


async def _auth(client, email="u1@test.edu.cn") -> dict:
    code = (await client.post("/api/v1/auth/send-code", json={"email": email})).json()["data"][
        "dev_code"
    ]
    r = await client.post("/api/v1/auth/verify", json={"email": email, "code": code})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_requires_login(client, world):
    r = await client.get(URL)
    assert r.status_code == 401


async def test_aggregates_per_floor(client, world):
    r = await client.get(URL, headers=await _auth(client))
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    # 停用的三食堂不出现；全部校区 → 二食堂 + 东苑食堂
    assert [c["canteen_name"] for c in data] == ["二食堂", "东苑食堂"]
    c2 = data[0]
    assert c2["canteen_id"] == world["c2_id"] and c2["floors"] == 3
    f1, f2, f3 = c2["levels"]
    # 1 层：停用座位不计 → 4 座 3 占
    assert f1 == {
        "floor": 1,
        "total": 4,
        "occupied": 3,
        "free": 1,
        "ratio": 0.75,
        "level": "high",
        "updated_at": "2026-11-10T04:05:00",
    }
    # 2 层：有座位没状态 → 全空
    assert f2["total"] == 2 and f2["occupied"] == 0 and f2["free"] == 2
    assert f2["level"] == "empty" and f2["updated_at"] is None
    # 3 层：floors=3 但没有座位 → unknown
    assert f3 == {
        "floor": 3,
        "total": 0,
        "occupied": 0,
        "free": 0,
        "ratio": 0.0,
        "level": "unknown",
        "updated_at": None,
    }


async def test_filters_by_campus(client, world):
    headers = await _auth(client)
    r = await client.get(URL, params={"campus_id": world["east_id"]}, headers=headers)
    data = r.json()["data"]
    assert [c["canteen_name"] for c in data] == ["东苑食堂"]
    assert data[0]["levels"][0]["total"] == 1


async def test_unknown_campus_returns_empty_list(client, world):
    r = await client.get(URL, params={"campus_id": 9999}, headers=await _auth(client))
    assert r.status_code == 200
    assert r.json()["data"] == []
