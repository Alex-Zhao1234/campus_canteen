import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  确保全部模型注册到 Base.metadata
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.static import mount_static

settings = get_settings()

# uvicorn 只配置自己的 logger；应用与 APScheduler 的 INFO 日志需要自己接上
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 表结构由 Alembic 管理：启动前执行 `make migrate`（alembic upgrade head）
    start_scheduler()
    yield
    stop_scheduler()
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
# 必须放在 api_router 之后：兜底路由把其余路径交给前端
mount_static(app, settings.static_dir)
