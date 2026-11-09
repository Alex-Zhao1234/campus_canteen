"""迁移脚本必须与 ORM 模型一致：升到 head 后 autogenerate 应无差异，函数索引需存在。"""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.core.database import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _config(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg


@pytest.fixture
def migrated_db(tmp_path):
    db_path = tmp_path / "mig.db"
    command.upgrade(_config(db_path), "head")
    return db_path


# 函数索引 uq_review_daily 在 SQLite 下无法反射，compare 会跳过并告警；它由下面的测试单独校验
@pytest.mark.filterwarnings("ignore:.*uq_review_daily.*")
def test_upgrade_head_matches_models(migrated_db):
    engine = create_engine(f"sqlite:///{migrated_db}")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"迁移与模型不一致: {diff}"


def test_upgrade_head_creates_daily_unique_index(migrated_db):
    con = sqlite3.connect(migrated_db)
    row = con.execute(
        "select sql from sqlite_master where type='index' and name='uq_review_daily'"
    ).fetchone()
    assert row is not None
    # 按北京日切天（库存 UTC）
    assert "date(created_at, '+8 hours')" in row[0]
    assert row[0].startswith("CREATE UNIQUE INDEX")


def test_downgrade_to_base_removes_everything(migrated_db):
    command.downgrade(_config(migrated_db), "base")
    con = sqlite3.connect(migrated_db)
    names = {
        r[0]
        for r in con.execute(
            "select name from sqlite_master where type in ('table','index') "
            "and name not like 'sqlite_%' and name != 'alembic_version'"
        )
    }
    assert names == set()
