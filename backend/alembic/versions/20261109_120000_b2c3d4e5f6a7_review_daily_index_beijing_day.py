"""uq_review_daily 改为按北京日切天

review.created_at 存 UTC，原索引 date(created_at) 按 UTC 日切天，
北京时间当天中午与次日清晨会落在同一 UTC 日被误拦。改为 date(created_at, '+8 hours')。

Revision ID: b2c3d4e5f6a7
Revises: 041509049adb
Create Date: 2026-11-09 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "041509049adb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_review_daily", table_name="review")
    op.create_index(
        "uq_review_daily",
        "review",
        ["user_id", "dish_id", sa.text("date(created_at, '+8 hours')")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_review_daily", table_name="review")
    op.create_index(
        "uq_review_daily",
        "review",
        ["user_id", "dish_id", sa.text("date(created_at)")],
        unique=True,
    )
