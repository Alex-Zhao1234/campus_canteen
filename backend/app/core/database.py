from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


def _set_sqlite_pragma(dbapi_conn, _):
    """开启 WAL 与外键约束。sqlite-vec 扩展在第二阶段于此处加载。"""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def make_engine(url: str, **kwargs: Any) -> AsyncEngine:
    """创建带 SQLite PRAGMA 监听的异步引擎。测试用内存库时也走这里。"""
    eng = create_async_engine(url, echo=False, **kwargs)
    event.listen(eng.sync_engine, "connect", _set_sqlite_pragma)
    return eng


engine = make_engine(settings.database_url)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
