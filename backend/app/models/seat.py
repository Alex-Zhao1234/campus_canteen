"""座位与座位当前状态。见 docs/superpowers/specs/2026-11-10-seat-occupancy-design.md 第 2 节。

seat 是静态信息（种子导入）；seat_state 由读数来源（本期是模拟器，将来是传感器网关）upsert，
一座一行，没有记录视为空闲。每层人数不建表，查询时 GROUP BY 现算。
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._mixins import IdMixin, utcnow


class Seat(IdMixin, Base):
    __tablename__ = "seat"
    __table_args__ = (
        UniqueConstraint("code", name="uq_seat_code"),
        Index("ix_seat_canteen_floor", "canteen_id", "floor"),
    )

    canteen_id: Mapped[int] = mapped_column(ForeignKey("canteen.id"), nullable=False)
    floor: Mapped[int] = mapped_column(default=1, nullable=False)
    # 座位编码，如 C2-1F-037；概念上也是传感器侧的设备标识
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    # 拆除/维修的座位置 false：不计入总数，读数按未知 code 处理
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class SeatState(Base):
    __tablename__ = "seat_state"

    seat_id: Mapped[int] = mapped_column(ForeignKey("seat.id"), primary_key=True)
    is_occupied: Mapped[bool] = mapped_column(default=False, nullable=False)
    # 最近一次状态翻转时间（有人坐下 / 离开）
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    # 最近一次读数（心跳）时间；由服务层显式赋值，不用 onupdate
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
