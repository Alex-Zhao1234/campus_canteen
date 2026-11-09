"""评价事件流（append-only）。见 docs/架构设计.md 5.2。

review 表只做 INSERT；唯一允许的 UPDATE 是 is_hidden 软删除。
"""

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import CreatedAtMixin, IdMixin

VERDICTS = ("good", "ok", "bad")
MEAL_SLOTS = ("breakfast", "lunch", "dinner", "night")


def _in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


class Tag(IdMixin, Base):
    """预设标签。category: taste / price / portion / service / change。"""

    __tablename__ = "tag"

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(10), nullable=False)


class ReviewTag(Base):
    __tablename__ = "review_tag"

    review_id: Mapped[int] = mapped_column(ForeignKey("review.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class Review(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint(f"verdict IN ({_in_list(VERDICTS)})", name="ck_review_verdict"),
        CheckConstraint(
            f"meal_slot IS NULL OR meal_slot IN ({_in_list(MEAL_SLOTS)})",
            name="ck_review_meal_slot",
        ),
        Index("ix_review_dish_created", "dish_id", "created_at"),
        Index("ix_review_stall_created", "stall_id", "created_at"),
        Index("ix_review_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dish.id"), nullable=False)
    # 冗余 stall_id，便于窗口级聚合与预警
    stall_id: Mapped[int] = mapped_column(ForeignKey("stall.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(4), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(100))
    meal_slot: Mapped[str | None] = mapped_column(String(10))
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)

    tags: Mapped[list[Tag]] = relationship(secondary=ReviewTag.__table__, lazy="selectin")


# 单人单菜单日限评一次。created_at 存 UTC，按北京日（+8h）切天。
# 函数索引，Alembic autogenerate 识别不了，迁移脚本需手写。
Index(
    "uq_review_daily",
    Review.user_id,
    Review.dish_id,
    func.date(Review.created_at, "+8 hours"),
    unique=True,
)
