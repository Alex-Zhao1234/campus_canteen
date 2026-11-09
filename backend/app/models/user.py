"""用户。只存校园邮箱哈希，不存学号明文。trust_score 用于防刷（第 10 章）。"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import CreatedAtMixin, IdMixin
from app.models.org import Campus


class User(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "user"

    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    avatar_seed: Mapped[str | None] = mapped_column(String(32))
    trust_score: Mapped[float] = mapped_column(default=1.0, nullable=False)
    last_active_at: Mapped[datetime | None]

    campus: Mapped[Campus] = relationship(lazy="selectin")
