"""组织结构：校区 → 食堂 → 窗口 → 菜品。见 docs/架构设计.md 5.2。"""

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import CreatedAtMixin, IdMixin


class Campus(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "campus"

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    canteens: Mapped[list["Canteen"]] = relationship(back_populates="campus")


class Canteen(IdMixin, Base):
    __tablename__ = "canteen"

    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    floors: Mapped[int] = mapped_column(default=1, nullable=False)
    open_hours_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    campus: Mapped["Campus"] = relationship(back_populates="canteens", lazy="selectin")
    stalls: Mapped[list["Stall"]] = relationship(back_populates="canteen")


class Stall(IdMixin, Base):
    __tablename__ = "stall"

    canteen_id: Mapped[int] = mapped_column(ForeignKey("canteen.id"), nullable=False)
    floor: Mapped[int] = mapped_column(default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    cuisine_type: Mapped[str | None] = mapped_column(String(20))
    position_desc: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # open / closed / unknown
    today_status: Mapped[str] = mapped_column(String(10), default="unknown", nullable=False)

    canteen: Mapped["Canteen"] = relationship(back_populates="stalls", lazy="selectin")
    dishes: Mapped[list["Dish"]] = relationship(back_populates="stall")


class Dish(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "dish"
    __table_args__ = (Index("ix_dish_stall_active", "stall_id", "is_active"),)

    stall_id: Mapped[int] = mapped_column(ForeignKey("stall.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price_cents: Mapped[int] = mapped_column(nullable=False)
    spicy_level: Mapped[int] = mapped_column(default=0, nullable=False)  # 0-3
    is_veg: Mapped[bool] = mapped_column(default=False, nullable=False)
    portion_hint: Mapped[str | None] = mapped_column(String(50))
    # 常驻 / 限时 / 每周X
    dish_type: Mapped[str] = mapped_column(String(10), default="常驻", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    stall: Mapped["Stall"] = relationship(back_populates="dishes", lazy="selectin")
