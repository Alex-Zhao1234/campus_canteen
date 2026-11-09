from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  确保全部模型注册到 Base.metadata
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # MVP 阶段直接建表；引入 Alembic 后改为迁移管理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
