"""单容器部署时由 FastAPI 顺便托管前端构建产物（Render 等只跑一个容器的平台）。

本地开发与 docker-compose 仍由 Vite / Nginx 托管前端，此处 STATIC_DIR 为空时什么都不做。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


def mount_static(app: FastAPI, static_dir: str | None) -> bool:
    if not static_dir:
        return False
    root = Path(static_dir)
    index = root / "index.html"
    if not index.is_file():
        return False

    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # /api 下未匹配的路径仍按接口 404 处理，不要吐 index.html
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404, content={"code": 404, "data": None, "msg": "接口不存在"}
            )
        candidate = root / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    return True
