"""模型公共片段。时间统一为 UTC naive，Python 侧赋值。"""

from datetime import UTC, datetime

from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class IdMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
