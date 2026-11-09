"""单容器模式：托管前端产物并做 SPA 回退；未配置时不挂载。"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.static import mount_static


def _app_with_static(static_dir) -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/health")
    async def health():
        return {"code": 0}

    mount_static(app, str(static_dir) if static_dir else None)
    return app


async def test_not_mounted_when_dir_missing(tmp_path):
    app = _app_with_static(None)
    assert mount_static(app, str(tmp_path / "nope")) is False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/stall/1")).status_code == 404


async def test_serves_index_assets_and_spa_fallback(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<title>app</title>")
    (tmp_path / "assets" / "a.js").write_text("console.log(1)")
    (tmp_path / "favicon.ico").write_bytes(b"ico")
    app = _app_with_static(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/")).text == "<title>app</title>"
        assert (await c.get("/stall/1")).text == "<title>app</title>"  # SPA 回退
        assert (await c.get("/assets/a.js")).text == "console.log(1)"
        assert (await c.get("/favicon.ico")).content == b"ico"
        assert (await c.get("/api/v1/health")).json() == {"code": 0}  # 接口优先
        r = await c.get("/api/v1/nope")
        assert r.status_code == 404 and r.json()["code"] == 404
