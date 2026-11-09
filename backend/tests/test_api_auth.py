"""最简认证：邮箱验证码登录、JWT、/me。开发模式下验证码直接回传（echo）。"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, User
from app.services.auth_service import code_store

EMAIL = "zhang.san@test.edu.cn"


@pytest.fixture(autouse=True)
async def _campus_and_clean_store(engine):
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        db.add(Campus(name="主校区"))
        await db.commit()


async def _login(client, email=EMAIL) -> dict:
    code = (await client.post("/api/v1/auth/send-code", json={"email": email})).json()["data"][
        "dev_code"
    ]
    r = await client.post("/api/v1/auth/verify", json={"email": email, "code": code})
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_send_code_rejects_foreign_domain(client):
    r = await client.post("/api/v1/auth/send-code", json={"email": "a@gmail.com"})
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == 400
    assert "校园邮箱" in body["msg"]


async def test_send_code_echoes_code_in_dev(client):
    r = await client.post("/api/v1/auth/send-code", json={"email": EMAIL})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["sent"] is True
    assert len(data["dev_code"]) == 6 and data["dev_code"].isdigit()


async def test_verify_wrong_code_401(client):
    await client.post("/api/v1/auth/send-code", json={"email": EMAIL})
    r = await client.post("/api/v1/auth/verify", json={"email": EMAIL, "code": "000000"})
    assert r.status_code == 401
    assert r.json()["code"] == 401


async def test_verify_without_send_code_401(client):
    r = await client.post("/api/v1/auth/verify", json={"email": EMAIL, "code": "123456"})
    assert r.status_code == 401


async def test_verify_creates_user_and_returns_tokens(client, engine):
    data = await _login(client)
    assert data["access_token"] and data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["nickname"].startswith("同学#")
    assert data["user"]["trust_score"] == 1.0

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 1
        user = await db.scalar(select(User))
        assert user.email_hash != EMAIL  # 只存哈希
        assert len(user.email_hash) == 64


async def test_second_login_reuses_same_user(client):
    first = await _login(client)
    second = await _login(client)
    assert first["user"]["id"] == second["user"]["id"]


async def test_code_is_single_use(client):
    code = (await client.post("/api/v1/auth/send-code", json={"email": EMAIL})).json()["data"][
        "dev_code"
    ]
    assert (
        await client.post("/api/v1/auth/verify", json={"email": EMAIL, "code": code})
    ).status_code == 200
    assert (
        await client.post("/api/v1/auth/verify", json={"email": EMAIL, "code": code})
    ).status_code == 401


async def test_me_requires_token(client):
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json()["code"] == 401


async def test_me_rejects_garbage_token(client):
    r = await client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


async def test_me_returns_current_user(client):
    data = await _login(client)
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == data["user"]["id"]


async def test_refresh_issues_new_access_token(client):
    data = await _login(client)
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200, r.text
    new_access = r.json()["data"]["access_token"]
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_access_token_cannot_be_used_as_refresh(client):
    data = await _login(client)
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": data["access_token"]})
    assert r.status_code == 401


async def test_refresh_token_cannot_access_api(client):
    data = await _login(client)
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {data['refresh_token']}"})
    assert r.status_code == 401


# ---------- 验证码开关：AUTH_CODE_REQUIRED=false 时按回车直接登录 ----------


@pytest.fixture
def code_not_required():
    from app.core.config import get_settings

    settings = get_settings()
    settings.auth_code_required = False
    yield
    settings.auth_code_required = True


async def test_send_code_skips_code_when_not_required(client, code_not_required):
    r = await client.post("/api/v1/auth/send-code", json={"email": EMAIL})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data == {"sent": False, "code_required": False, "dev_code": None}


async def test_verify_without_code_logs_in_when_not_required(client, code_not_required):
    r = await client.post("/api/v1/auth/verify", json={"email": EMAIL})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["access_token"]
    # 域名限制仍然生效
    r = await client.post("/api/v1/auth/verify", json={"email": "a@gmail.com"})
    assert r.status_code == 400


async def test_verify_without_code_rejected_when_required(client):
    r = await client.post("/api/v1/auth/verify", json={"email": EMAIL})
    assert r.status_code == 401


async def test_send_code_reports_code_required_by_default(client):
    r = await client.post("/api/v1/auth/send-code", json={"email": EMAIL})
    assert r.json()["data"]["code_required"] is True
