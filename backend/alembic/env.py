"""Alembic 环境。数据库地址来自项目 Settings，元数据来自 app.models。

SQLite 不支持大部分 ALTER TABLE，开启 render_as_batch 让后续改列的迁移以"建新表-拷贝-改名"方式执行。
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection

import app.models  # noqa: F401  注册全部模型
from app.core.config import get_settings
from app.core.database import Base, make_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 测试可通过 set_main_option 覆盖；否则用 .env 中的 DATABASE_URL
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连库。"""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # 用项目的 make_engine，迁移时同样开启 WAL 与外键约束
    connectable = make_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
