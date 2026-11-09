import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db, make_engine
from app.main import app


@pytest.fixture(autouse=True)
def _pinned_settings():
    """测试不受本地 .env 影响：固定认证相关开关，用完还原。"""
    s = get_settings()
    saved = (s.auth_code_required, s.auth_echo_code, s.scheduler_enabled)
    s.auth_code_required, s.auth_echo_code, s.scheduler_enabled = True, True, False
    yield
    s.auth_code_required, s.auth_echo_code, s.scheduler_enabled = saved


@pytest.fixture
async def engine():
    """每个测试一个独立的内存库；StaticPool 保证所有连接共享同一个内存库。"""
    eng = make_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
