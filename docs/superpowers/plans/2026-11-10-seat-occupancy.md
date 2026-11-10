# 食堂空余座位 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 后端存座位当前状态 → App 食堂列表页按层显示占用率/拥挤度/剩余座位，5 秒刷新；内置模拟器扮演传感器网关按餐段曲线产生座位进出。**传感器硬件与上报接口只在文档里做概念说明，不落码。**

**Architecture:** 新增 `seat`（静态）与 `seat_state`（当前状态）两表；`SeatService.apply_states()` 是读数写入的唯一入口（本期只有模拟器调用，将来传感器网关的路由层也调它）；`GET /seats/occupancy` 按食堂 × 楼层 `GROUP BY` 现算并套用 `app/seating/levels.py` 的阈值；前端 TanStack Query 5 秒轮询。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + aiosqlite + Alembic + APScheduler；React 18 + TS + TanStack Query；pytest + httpx。

**Spec:** `docs/superpowers/specs/2026-11-10-seat-occupancy-design.md`

## Global Constraints

- 分层 api → services → repositories → models，路由层不写业务逻辑；依赖注入用 `Annotated` 风格（`app/api/deps.py`）。
- 业务异常用 `app/services/errors.py` 的类，由 `api/errors.py` 统一转成响应壳 `{code, data, msg}`；成功用 `schemas/common.py` 的 `ok()`。
- 时间统一 UTC naive（`app/models/_mixins.py` 的 `utcnow`），"北京时间"= UTC + 8h。
- 表结构由 Alembic 管理，改模型必须配迁移；`tests/test_migrations.py` 校验迁移与模型一致、`downgrade base` 清空。
- 阈值常量集中在 `app/seating/levels.py`：empty < 0.25 ≤ low < 0.50 ≤ medium < 0.70 ≤ high < 0.85 ≤ full；total == 0 → unknown。
- 不写任何 `/sensors` 路由、设备鉴权、`SENSOR_API_KEY`；传感器链路只出现在文档里。
- 前端样式只写 `frontend/src/index.css`，无 UI 库；接口字段英文 snake_case。
- 所有命令在 `backend/` 下用 `.venv/bin/...`（uv 管理），前端在 `frontend/` 用 npm。
- 提交信息中文，结尾加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

## Review Focus

1. 同一批读数里同一个 `code` 出现两次（将来网关重发）：应以最后一条为准，`applied` 只计一次。（Task 4 测试覆盖）
2. 同状态重复读数（心跳）：`updated_at` 前进、`changed_at` 不动；翻转时两者一起前进。前端"x 秒前更新"依赖这个语义。（Task 4 测试覆盖）
3. 停用座位 `is_active=false` 仍有读数：应进 `unknown_codes`，不改状态，也不计入总数。（Task 4、Task 5 测试覆盖）
4. 食堂 `floors=3` 但 seats.csv 只给了 1、2 层：第 3 层要出现且 `level=unknown`、`total=0`，前端显示"暂无数据"而不是 NaN。（Task 5、Task 8 覆盖）
5. 模拟器在某层 `total=0` 或目标正好等于当前占用时：不能除零、不能死循环，tick 仍成功返回。（Task 7 测试覆盖）

---

### Task 1: 座位模型与迁移

**Files:**
- Create: `backend/app/models/seat.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20261110_c4d5e6f7a8b9_seat_tables.py`
- Test: `backend/tests/test_models_seat.py`

**Interfaces:**
- Produces: `Seat(id, canteen_id, floor, code, is_active)`、`SeatState(seat_id PK, is_occupied, changed_at, updated_at)`，从 `app.models` 导出。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_models_seat.py
"""座位表：code 全局唯一；seat_state 以 seat_id 为主键，一座一行。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Campus, Canteen, Seat, SeatState


async def _canteen(db) -> Canteen:
    canteen = Canteen(name="二食堂", floors=3, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.commit()
    return canteen


async def test_seat_code_is_unique(db):
    canteen = await _canteen(db)
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"))
    await db.commit()
    db.add(Seat(canteen_id=canteen.id, floor=2, code="C1-1F-001"))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_seat_defaults_active(db):
    canteen = await _canteen(db)
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"))
    await db.commit()
    seat = await db.scalar(select(Seat))
    assert seat.is_active is True


async def test_seat_state_is_one_row_per_seat(db):
    canteen = await _canteen(db)
    seat = Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001")
    db.add(seat)
    await db.commit()
    db.add(SeatState(seat_id=seat.id, is_occupied=True))
    await db.commit()
    state = await db.scalar(select(SeatState))
    assert state.is_occupied is True
    assert state.changed_at is not None and state.updated_at is not None
    db.add(SeatState(seat_id=seat.id, is_occupied=False))
    with pytest.raises(IntegrityError):
        await db.commit()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_models_seat.py -q`
Expected: ImportError `cannot import name 'Seat'`

- [ ] **Step 3: 写模型**

```python
# backend/app/models/seat.py
"""座位与座位当前状态。见 docs/superpowers/specs/2026-11-10-seat-occupancy-design.md 第 2 节。

seat 是静态信息（种子导入）；seat_state 由传感器上报 upsert，一座一行，没有记录视为空闲。
每层人数不建表，查询时 GROUP BY 现算。
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
    # 传感器上报用的座位编码，如 C2-1F-037
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    # 拆除/维修的座位置 false：不计入总数，上报时按未知 code 处理
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class SeatState(Base):
    __tablename__ = "seat_state"

    seat_id: Mapped[int] = mapped_column(ForeignKey("seat.id"), primary_key=True)
    is_occupied: Mapped[bool] = mapped_column(default=False, nullable=False)
    # 最近一次状态翻转时间（有人坐下 / 离开）
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    # 最近一次上报（心跳）时间；由服务层显式赋值，不用 onupdate
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
```

在 `backend/app/models/__init__.py` 加 `from app.models.seat import Seat, SeatState` 并把 `"Seat"`、`"SeatState"` 加进 `__all__`（保持字母序）。

- [ ] **Step 4: 运行模型测试通过**

Run: `cd backend && .venv/bin/pytest tests/test_models_seat.py -q`
Expected: 3 passed

- [ ] **Step 5: 生成迁移并校正**

Run: `cd backend && .venv/bin/alembic revision --autogenerate -m "seat_tables" --rev-id c4d5e6f7a8b9`
然后把生成的文件改名为 `alembic/versions/20261110_c4d5e6f7a8b9_seat_tables.py`，内容应等价于：

```python
"""seat_tables

Revision ID: c4d5e6f7a8b9
Revises: 7e3d1621946d
Create Date: 2026-11-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = '7e3d1621946d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'seat',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('canteen_id', sa.Integer(), nullable=False),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['canteen_id'], ['canteen.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_seat_code'),
    )
    with op.batch_alter_table('seat', schema=None) as batch_op:
        batch_op.create_index('ix_seat_canteen_floor', ['canteen_id', 'floor'], unique=False)

    op.create_table(
        'seat_state',
        sa.Column('seat_id', sa.Integer(), nullable=False),
        sa.Column('is_occupied', sa.Boolean(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['seat_id'], ['seat.id']),
        sa.PrimaryKeyConstraint('seat_id'),
    )


def downgrade() -> None:
    op.drop_table('seat_state')
    with op.batch_alter_table('seat', schema=None) as batch_op:
        batch_op.drop_index('ix_seat_canteen_floor')
    op.drop_table('seat')
```

检查 autogenerate **没有**顺手删掉 `uq_review_daily` 或其它已有对象；有则删掉那几行。

- [ ] **Step 6: 跑迁移测试与全量测试**

Run: `cd backend && .venv/bin/pytest tests/test_migrations.py tests/test_models_seat.py -q && .venv/bin/ruff check app tests`
Expected: all passed, ruff 无报错

- [ ] **Step 7: 提交**

```bash
git add backend/app/models/seat.py backend/app/models/__init__.py backend/alembic/versions/20261110_c4d5e6f7a8b9_seat_tables.py backend/tests/test_models_seat.py
git commit -m "feat(seat): 座位 seat / seat_state 模型与迁移

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 拥挤度分层纯函数

**Files:**
- Create: `backend/app/seating/__init__.py`（空文件，一行 docstring）
- Create: `backend/app/seating/levels.py`
- Test: `backend/tests/test_seat_levels.py`

**Interfaces:**
- Produces: `Level = Literal["unknown","empty","low","medium","high","full"]`；`LEVEL_LABELS: dict[Level, str]`；`occupancy_ratio(occupied: int, total: int) -> float`（total 0 → 0.0，结果四舍五入 3 位）；`level_for(occupied: int, total: int) -> Level`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_seat_levels.py
"""拥挤度分层阈值（spec 第 3 节）：边界值落在上一档还是下一档必须固定。"""

import pytest

from app.seating.levels import LEVEL_LABELS, level_for, occupancy_ratio


@pytest.mark.parametrize(
    ("occupied", "total", "expected"),
    [
        (0, 0, "unknown"),
        (5, 0, "unknown"),
        (0, 100, "empty"),
        (24, 100, "empty"),
        (25, 100, "low"),
        (49, 100, "low"),
        (50, 100, "medium"),
        (69, 100, "medium"),
        (70, 100, "high"),
        (84, 100, "high"),
        (85, 100, "full"),
        (100, 100, "full"),
        (3, 4, "high"),  # 0.75
    ],
)
def test_level_boundaries(occupied, total, expected):
    assert level_for(occupied, total) == expected


def test_ratio_rounds_to_three_places_and_handles_zero_total():
    assert occupancy_ratio(0, 0) == 0.0
    assert occupancy_ratio(1, 3) == 0.333
    assert occupancy_ratio(160, 160) == 1.0


def test_every_level_has_chinese_label():
    assert LEVEL_LABELS == {
        "unknown": "暂无数据",
        "empty": "空闲",
        "low": "较少",
        "medium": "适中",
        "high": "较多",
        "full": "爆满",
    }
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_seat_levels.py -q`
Expected: ModuleNotFoundError `app.seating`

- [ ] **Step 3: 实现**

```python
# backend/app/seating/__init__.py
"""座位拥挤度：纯函数与阈值常量，不依赖数据库。"""
```

```python
# backend/app/seating/levels.py
"""拥挤度分层。阈值见 docs/superpowers/specs/2026-11-10-seat-occupancy-design.md 第 3 节。

找座难度非线性：70% 以前随便坐，70%–85% 要绕一圈，85% 以上剩的是散落单座，
所以高两档区间故意比低三档窄。
"""

from typing import Literal

Level = Literal["unknown", "empty", "low", "medium", "high", "full"]

# (占用率上限（不含）, 档位)，按升序；超过最后一档上限即 full
LEVEL_THRESHOLDS: tuple[tuple[float, Level], ...] = (
    (0.25, "empty"),
    (0.50, "low"),
    (0.70, "medium"),
    (0.85, "high"),
)

LEVEL_LABELS: dict[Level, str] = {
    "unknown": "暂无数据",
    "empty": "空闲",
    "low": "较少",
    "medium": "适中",
    "high": "较多",
    "full": "爆满",
}


def occupancy_ratio(occupied: int, total: int) -> float:
    """占用率，保留 3 位；没有座位时为 0。"""
    if total <= 0:
        return 0.0
    return round(occupied / total, 3)


def level_for(occupied: int, total: int) -> Level:
    if total <= 0:
        return "unknown"
    ratio = occupied / total  # 分档用未舍入的值，避免 0.2496 被舍成 0.25
    for upper, level in LEVEL_THRESHOLDS:
        if ratio < upper:
            return level
    return "full"
```

- [ ] **Step 4: 运行通过**

Run: `cd backend && .venv/bin/pytest tests/test_seat_levels.py -q && .venv/bin/ruff check app tests`
Expected: 15 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/seating backend/tests/test_seat_levels.py
git commit -m "feat(seat): 拥挤度分层阈值纯函数

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 配置项

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`（api.environment）
- Modify: `render.yaml`（envVars）
- Modify: `backend/tests/conftest.py`（固定开关）

**Interfaces:**
- Produces: `Settings.seat_simulator_enabled: bool = False`、`Settings.seat_sim_interval_seconds: int = 5`。

- [ ] **Step 1: 改 Settings**

在 `backend/app/core/config.py` 的 `ranking_interval_minutes` 之后加：

```python
    # 座位模拟器：没有真实传感器时扮演网关，按餐段曲线生成座位进出（演示用）
    seat_simulator_enabled: bool = False
    seat_sim_interval_seconds: int = 5
```

- [ ] **Step 2: 改 conftest 固定开关**

`backend/tests/conftest.py` 的 `_pinned_settings` 改成：

```python
@pytest.fixture(autouse=True)
def _pinned_settings():
    """测试不受本地 .env 影响：固定认证/调度/模拟器开关，用完还原。"""
    s = get_settings()
    saved = (
        s.auth_code_required,
        s.auth_echo_code,
        s.scheduler_enabled,
        s.seat_simulator_enabled,
    )
    s.auth_code_required, s.auth_echo_code = True, True
    s.scheduler_enabled, s.seat_simulator_enabled = False, False
    yield
    (
        s.auth_code_required,
        s.auth_echo_code,
        s.scheduler_enabled,
        s.seat_simulator_enabled,
    ) = saved
```

- [ ] **Step 3: 环境文件**

`.env.example` 末尾追加：

```
SEAT_SIMULATOR_ENABLED=true     # 没有真实传感器时按餐段曲线模拟座位进出
SEAT_SIM_INTERVAL_SECONDS=5
```

`docker-compose.yml` api.environment 追加：

```yaml
      SEAT_SIMULATOR_ENABLED: ${SEAT_SIMULATOR_ENABLED:-true}   # 演示：模拟座位进出
      SEAT_SIM_INTERVAL_SECONDS: ${SEAT_SIM_INTERVAL_SECONDS:-5}
```

`render.yaml` envVars 追加：

```yaml
      - key: SEAT_SIMULATOR_ENABLED
        value: "true"         # 没有真实传感器，模拟座位进出
      - key: SEAT_SIM_INTERVAL_SECONDS
        value: "5"
```

- [ ] **Step 4: 全量测试仍通过**

Run: `cd backend && .venv/bin/pytest -q`
Expected: all passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/core/config.py backend/tests/conftest.py .env.example docker-compose.yml render.yaml
git commit -m "chore(seat): 座位模拟器配置项

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 座位读数写入服务 `SeatService.apply_states`

> 概念上这是"传感器网关 → 后端"链路的最后一步。本期没有 HTTP 上报接口、没有设备鉴权，唯一调用方是 Task 7 的模拟器；将来接真硬件时加一个路由层文件调用同一个方法即可。

**Files:**
- Create: `backend/app/schemas/seat.py`
- Create: `backend/app/repositories/seat_repo.py`
- Create: `backend/app/services/seat_service.py`
- Test: `backend/tests/test_seat_service.py`

**Interfaces:**
- Consumes: `Seat`、`SeatState`（Task 1）。
- Produces:
  - `schemas/seat.py`：`SeatReading(code: str, is_occupied: bool, ts: datetime | None = None)`、`ApplyResult(applied: int, unknown_codes: list[str])`、`FloorOccupancyOut`、`CanteenOccupancyOut`（后两者 Task 5 用）。
  - `SeatRepository(db)`：`list_active_seats_by_codes(codes: Iterable[str]) -> list[Seat]`、`get_states(seat_ids: Iterable[int]) -> dict[int, SeatState]`、`add_state(state: SeatState) -> None`、`commit()`、`list_active_canteens(campus_id) -> list[Canteen]`、`floor_counts(canteen_ids) -> list[tuple[int, int, int, int, datetime | None]]`、`list_active_seats() -> list[tuple[Seat, SeatState | None]]`。
  - `SeatService(repo)`：`apply_states(readings: list[SeatReading], now: datetime | None = None) -> ApplyResult`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_seat_service.py
"""SeatService.apply_states：座位读数 upsert。本期由模拟器调用，将来传感器网关的路由也调它。"""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import Campus, Canteen, Seat, SeatState
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import SeatReading
from app.services.seat_service import SeatService

T1 = datetime(2026, 11, 10, 4, 0)
T2 = datetime(2026, 11, 10, 4, 5)
T3 = datetime(2026, 11, 10, 4, 10)


@pytest.fixture
async def svc(db) -> SeatService:
    """二食堂 1 层三个座位，其中 003 停用。"""
    canteen = Canteen(name="二食堂", floors=1, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.flush()
    db.add_all(
        [
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-001"),
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-002"),
            Seat(canteen_id=canteen.id, floor=1, code="C1-1F-003", is_active=False),
        ]
    )
    await db.commit()
    return SeatService(SeatRepository(db))


async def _states(db) -> dict[str, SeatState]:
    rows = (await db.execute(select(Seat.code, SeatState).join(SeatState))).all()
    return {code: state for code, state in rows}


async def test_upserts_and_reports_unknown_codes(db, svc):
    result = await svc.apply_states(
        [
            SeatReading(code="C1-1F-001", is_occupied=True),
            SeatReading(code="C1-1F-003", is_occupied=True),  # 停用座位
            SeatReading(code="C9-9F-999", is_occupied=False),  # 不存在
        ],
        now=T1,
    )
    assert result.applied == 1
    assert result.unknown_codes == ["C1-1F-003", "C9-9F-999"]
    states = await _states(db)
    assert set(states) == {"C1-1F-001"}
    assert states["C1-1F-001"].is_occupied is True
    assert states["C1-1F-001"].changed_at == states["C1-1F-001"].updated_at == T1


async def test_changed_at_only_moves_on_flip(db, svc):
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=True, ts=T1)])
    # 同状态心跳：updated_at 前进，changed_at 不动
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=True, ts=T2)])
    s = (await _states(db))["C1-1F-001"]
    assert s.changed_at == T1
    assert s.updated_at == T2
    # 翻转：两者都前进
    await svc.apply_states([SeatReading(code="C1-1F-001", is_occupied=False, ts=T3)])
    s = (await _states(db))["C1-1F-001"]
    assert s.is_occupied is False
    assert s.changed_at == s.updated_at == T3


async def test_reading_without_ts_uses_now(db, svc):
    await svc.apply_states([SeatReading(code="C1-1F-002", is_occupied=True)], now=T2)
    assert (await _states(db))["C1-1F-002"].updated_at == T2


async def test_duplicate_code_in_batch_last_one_wins(db, svc):
    result = await svc.apply_states(
        [
            SeatReading(code="C1-1F-001", is_occupied=True),
            SeatReading(code="C1-1F-001", is_occupied=False),
        ]
    )
    assert result.applied == 1
    assert (await _states(db))["C1-1F-001"].is_occupied is False


async def test_empty_batch_is_noop(db, svc):
    result = await svc.apply_states([])
    assert result.applied == 0 and result.unknown_codes == []
    assert await _states(db) == {}
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_seat_service.py -q`
Expected: ModuleNotFoundError `app.repositories.seat_repo`

- [ ] **Step 3: schema**

```python
# backend/app/schemas/seat.py
"""座位相关 DTO：读数（模拟器 / 将来的传感器网关 → 服务层）与空位查询出参。"""

from datetime import datetime

from pydantic import BaseModel

from app.seating.levels import Level


class SeatReading(BaseModel):
    """一条座位读数。ts 缺省由服务层取当前 UTC。"""

    code: str
    is_occupied: bool
    ts: datetime | None = None


class ApplyResult(BaseModel):
    applied: int
    unknown_codes: list[str]


class FloorOccupancyOut(BaseModel):
    floor: int
    total: int
    occupied: int
    free: int
    ratio: float
    level: Level
    updated_at: datetime | None


class CanteenOccupancyOut(BaseModel):
    canteen_id: int
    canteen_name: str
    floors: int
    levels: list[FloorOccupancyOut]
```

- [ ] **Step 4: repository**

```python
# backend/app/repositories/seat_repo.py
"""座位数据访问：按 code 找座位、读写当前状态、按食堂 × 楼层聚合。不含业务判断。"""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Canteen, Seat, SeatState


class SeatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active_seats_by_codes(self, codes: Iterable[str]) -> list[Seat]:
        codes = list(codes)
        if not codes:
            return []
        stmt = select(Seat).where(Seat.code.in_(codes), Seat.is_active.is_(True))
        return list((await self.db.scalars(stmt)).all())

    async def get_states(self, seat_ids: Iterable[int]) -> dict[int, SeatState]:
        ids = list(seat_ids)
        if not ids:
            return {}
        rows = await self.db.scalars(select(SeatState).where(SeatState.seat_id.in_(ids)))
        return {s.seat_id: s for s in rows}

    def add_state(self, state: SeatState) -> None:
        self.db.add(state)

    async def commit(self) -> None:
        await self.db.commit()

    async def list_active_canteens(self, campus_id: int | None) -> list[Canteen]:
        stmt = select(Canteen).where(Canteen.is_active.is_(True)).order_by(Canteen.id)
        if campus_id is not None:
            stmt = stmt.where(Canteen.campus_id == campus_id)
        return list((await self.db.scalars(stmt)).all())

    async def floor_counts(
        self, canteen_ids: Iterable[int]
    ) -> list[tuple[int, int, int, int, datetime | None]]:
        """每个 (canteen_id, floor) 的 (total, occupied, 最新 updated_at)，只算在用座位。"""
        ids = list(canteen_ids)
        if not ids:
            return []
        occupied = func.coalesce(
            func.sum(case((SeatState.is_occupied.is_(True), 1), else_=0)), 0
        )
        stmt = (
            select(
                Seat.canteen_id,
                Seat.floor,
                func.count(Seat.id),
                occupied,
                func.max(SeatState.updated_at),
            )
            .select_from(Seat)
            .outerjoin(SeatState, SeatState.seat_id == Seat.id)
            .where(Seat.is_active.is_(True), Seat.canteen_id.in_(ids))
            .group_by(Seat.canteen_id, Seat.floor)
            .order_by(Seat.canteen_id, Seat.floor)
        )
        return [tuple(r) for r in (await self.db.execute(stmt)).all()]

    async def list_active_seats(self) -> list[tuple[Seat, SeatState | None]]:
        """模拟器用：全部在用座位及其状态（没有记录为 None）。"""
        stmt = (
            select(Seat, SeatState)
            .outerjoin(SeatState, SeatState.seat_id == Seat.id)
            .where(Seat.is_active.is_(True))
            .order_by(Seat.id)
        )
        return [(seat, state) for seat, state in (await self.db.execute(stmt)).all()]
```

注意：`func.max(SeatState.updated_at)` 在 SQLite 里返回字符串，SQLAlchemy 会按 `DateTime` 类型转回 `datetime`；Task 5 的测试会验证。

- [ ] **Step 5: service（本任务只实现 apply_states）**

```python
# backend/app/services/seat_service.py
"""座位服务：读数写入（upsert seat_state）、按食堂 × 楼层聚合拥挤度。

apply_states 是"传感器网关 → 后端"链路的落点。本期没有上报 HTTP 接口，唯一调用方是
app/tasks/seat_sim.py 的模拟器；将来接真硬件时加一个路由层调用它即可。
"""

from datetime import datetime

from app.models import SeatState
from app.models._mixins import utcnow
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import ApplyResult, SeatReading


class SeatService:
    def __init__(self, repo: SeatRepository) -> None:
        self.repo = repo

    async def apply_states(
        self, readings: list[SeatReading], now: datetime | None = None
    ) -> ApplyResult:
        """批量 upsert。同批同 code 以最后一条为准；未知/停用 code 收集返回，不整批失败。

        changed_at 只在 is_occupied 翻转时更新，updated_at 每条读数都更新（心跳）。
        """
        now = now or utcnow()
        latest: dict[str, SeatReading] = {}
        for r in readings:
            latest[r.code] = r

        seats = {seat.code: seat for seat in await self.repo.list_active_seats_by_codes(latest)}
        unknown = sorted(code for code in latest if code not in seats)
        existing = await self.repo.get_states(seat.id for seat in seats.values())

        applied = 0
        for code, reading in latest.items():
            seat = seats.get(code)
            if seat is None:
                continue
            ts = reading.ts or now
            state = existing.get(seat.id)
            if state is None:
                self.repo.add_state(
                    SeatState(
                        seat_id=seat.id,
                        is_occupied=reading.is_occupied,
                        changed_at=ts,
                        updated_at=ts,
                    )
                )
            else:
                if state.is_occupied != reading.is_occupied:
                    state.is_occupied = reading.is_occupied
                    state.changed_at = ts
                state.updated_at = ts
            applied += 1

        await self.repo.commit()
        return ApplyResult(applied=applied, unknown_codes=unknown)
```

- [ ] **Step 6: 运行通过**

Run: `cd backend && .venv/bin/pytest tests/test_seat_service.py -q && .venv/bin/ruff check app tests`
Expected: 5 passed

- [ ] **Step 7: 提交**

```bash
git add backend/app/schemas/seat.py backend/app/repositories/seat_repo.py backend/app/services/seat_service.py backend/tests/test_seat_service.py
git commit -m "feat(seat): 座位读数写入服务 SeatService.apply_states（模拟器 / 将来传感器网关共用）

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 空位查询接口 `GET /seats/occupancy`

**Files:**
- Modify: `backend/app/services/seat_service.py`
- Create: `backend/app/api/v1/seats.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_api_seats.py`

**Interfaces:**
- Consumes: `SeatRepository.list_active_canteens` / `floor_counts`（Task 4）；`level_for` / `occupancy_ratio`（Task 2）；`CurrentUser`（已有）。
- Produces（deps）：`get_seat_service(db: DbDep) -> SeatService`、`SeatServiceDep = Annotated[SeatService, Depends(get_seat_service)]`。
- Produces: `SeatService.occupancy(campus_id: int | None) -> list[CanteenOccupancyOut]`；`GET /api/v1/seats/occupancy?campus_id=`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_api_seats.py
"""GET /seats/occupancy：登录用户按食堂 × 楼层看占用率与拥挤度。"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Campus, Canteen, Seat, SeatState
from app.services.auth_service import code_store

URL = "/api/v1/seats/occupancy"
T0 = datetime(2026, 11, 10, 4, 0)
T1 = datetime(2026, 11, 10, 4, 5)


@pytest.fixture
async def world(engine):
    """主校区二食堂 floors=3：1 层 4 座(3 占, 其中一座停用且占用)、2 层 2 座(0 占)、3 层无座位；
    三食堂 floors=1 停用；东校区东苑食堂 1 层 1 座。"""
    code_store.clear()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        main = Campus(name="主校区")
        east = Campus(name="东校区")
        c2 = Canteen(name="二食堂", floors=3, campus=main)
        c3 = Canteen(name="三食堂", floors=1, campus=main, is_active=False)
        ce = Canteen(name="东苑食堂", floors=1, campus=east)
        db.add_all([c2, c3, ce])
        await db.flush()
        seats = [
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-001"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-002"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-003"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-004"),
            Seat(canteen_id=c2.id, floor=1, code="C1-1F-005", is_active=False),
            Seat(canteen_id=c2.id, floor=2, code="C1-2F-001"),
            Seat(canteen_id=c2.id, floor=2, code="C1-2F-002"),
            Seat(canteen_id=c3.id, floor=1, code="C2-1F-001"),
            Seat(canteen_id=ce.id, floor=1, code="C3-1F-001"),
        ]
        db.add_all(seats)
        await db.flush()
        by_code = {s.code: s for s in seats}
        db.add_all(
            [
                SeatState(seat_id=by_code["C1-1F-001"].id, is_occupied=True, changed_at=T0, updated_at=T0),
                SeatState(seat_id=by_code["C1-1F-002"].id, is_occupied=True, changed_at=T0, updated_at=T1),
                SeatState(seat_id=by_code["C1-1F-003"].id, is_occupied=True, changed_at=T0, updated_at=T0),
                SeatState(seat_id=by_code["C1-1F-004"].id, is_occupied=False, changed_at=T0, updated_at=T0),
                SeatState(seat_id=by_code["C1-1F-005"].id, is_occupied=True, changed_at=T0, updated_at=T0),
            ]
        )
        await db.commit()
        return {"main_id": main.id, "east_id": east.id, "c2_id": c2.id, "ce_id": ce.id}


async def _auth(client, email="u1@test.edu.cn") -> dict:
    code = (await client.post("/api/v1/auth/send-code", json={"email": email})).json()["data"][
        "dev_code"
    ]
    r = await client.post("/api/v1/auth/verify", json={"email": email, "code": code})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_requires_login(client, world):
    r = await client.get(URL)
    assert r.status_code == 401


async def test_aggregates_per_floor(client, world):
    r = await client.get(URL, headers=await _auth(client))
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    # 停用的三食堂不出现；全部校区 → 二食堂 + 东苑食堂
    assert [c["canteen_name"] for c in data] == ["二食堂", "东苑食堂"]
    c2 = data[0]
    assert c2["canteen_id"] == world["c2_id"] and c2["floors"] == 3
    f1, f2, f3 = c2["levels"]
    # 1 层：停用座位不计 → 4 座 3 占
    assert f1 == {
        "floor": 1, "total": 4, "occupied": 3, "free": 1, "ratio": 0.75,
        "level": "high", "updated_at": "2026-11-10T04:05:00",
    }
    # 2 层：有座位没状态 → 全空
    assert f2["total"] == 2 and f2["occupied"] == 0 and f2["free"] == 2
    assert f2["level"] == "empty" and f2["updated_at"] is None
    # 3 层：floors=3 但没有座位 → unknown
    assert f3 == {
        "floor": 3, "total": 0, "occupied": 0, "free": 0, "ratio": 0.0,
        "level": "unknown", "updated_at": None,
    }


async def test_filters_by_campus(client, world):
    headers = await _auth(client)
    r = await client.get(URL, params={"campus_id": world["east_id"]}, headers=headers)
    data = r.json()["data"]
    assert [c["canteen_name"] for c in data] == ["东苑食堂"]
    assert data[0]["levels"][0]["total"] == 1


async def test_unknown_campus_returns_empty_list(client, world):
    r = await client.get(URL, params={"campus_id": 9999}, headers=await _auth(client))
    assert r.status_code == 200
    assert r.json()["data"] == []
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_api_seats.py -q`
Expected: 404

- [ ] **Step 3: service 加 occupancy**

`backend/app/services/seat_service.py` 导入 `CanteenOccupancyOut, FloorOccupancyOut` 与 `level_for, occupancy_ratio`，在类里加：

```python
    async def occupancy(self, campus_id: int | None = None) -> list[CanteenOccupancyOut]:
        """每个在营食堂按 1..floors 列出每层；有座位但超出 floors 的层也列出。"""
        canteens = await self.repo.list_active_canteens(campus_id)
        counts = {
            (cid, floor): (total, occupied, updated_at)
            for cid, floor, total, occupied, updated_at in await self.repo.floor_counts(
                c.id for c in canteens
            )
        }
        result: list[CanteenOccupancyOut] = []
        for c in canteens:
            seat_floors = [f for (cid, f) in counts if cid == c.id]
            top = max([c.floors, *seat_floors])
            levels = []
            for floor in range(1, top + 1):
                total, occupied, updated_at = counts.get((c.id, floor), (0, 0, None))
                levels.append(
                    FloorOccupancyOut(
                        floor=floor,
                        total=total,
                        occupied=occupied,
                        free=total - occupied,
                        ratio=occupancy_ratio(occupied, total),
                        level=level_for(occupied, total),
                        updated_at=updated_at,
                    )
                )
            result.append(
                CanteenOccupancyOut(
                    canteen_id=c.id, canteen_name=c.name, floors=c.floors, levels=levels
                )
            )
        return result
```

- [ ] **Step 4: 依赖与路由**

`backend/app/api/deps.py`：导入 `SeatRepository`、`SeatService`，加：

```python
def get_seat_service(db: DbDep) -> SeatService:
    return SeatService(SeatRepository(db))


SeatServiceDep = Annotated[SeatService, Depends(get_seat_service)]
```

```python
# backend/app/api/v1/seats.py
"""空位查询：登录用户看每个食堂每层的占用率与拥挤度。前端 5 秒轮询。"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SeatServiceDep
from app.schemas.common import Envelope, ok
from app.schemas.seat import CanteenOccupancyOut

router = APIRouter(prefix="/seats")


@router.get("/occupancy", response_model=Envelope[list[CanteenOccupancyOut]])
async def seat_occupancy(user: CurrentUser, svc: SeatServiceDep, campus_id: int | None = None):
    return ok(await svc.occupancy(campus_id))
```

`router.py` import 加 `seats`，`api_router.include_router(seats.router, tags=["seats"])`。

- [ ] **Step 5: 运行通过**

Run: `cd backend && .venv/bin/pytest tests/test_api_seats.py tests/test_seat_service.py -q && .venv/bin/ruff check app tests`
Expected: 9 passed。若 `updated_at` 断言拿到的是字符串而非 `2026-11-10T04:05:00`，在 `floor_counts` 的 `func.max(...)` 外套 `type_coerce(..., DateTime)`。

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/seat_service.py backend/app/api/v1/seats.py backend/app/api/deps.py backend/app/api/v1/router.py backend/tests/test_api_seats.py
git commit -m "feat(seat): GET /seats/occupancy 按食堂 × 楼层现算占用率与拥挤度

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 座位种子

**Files:**
- Create: `data/seed/seats.csv`
- Modify: `backend/app/tasks/seed.py`
- Modify: `Makefile`（seed 目标）
- Modify: `backend/docker-entrypoint.sh`
- Test: `backend/tests/test_seed.py`

**Interfaces:**
- Produces: `seed_seats(session, csv_path, campus_name=DEFAULT_CAMPUS) -> dict[str, int]`，返回 `{"seat": 新建数, "skipped_rows": 找不到食堂的行数}`；座位编码 `f"C{canteen.id}-{floor}F-{n:03d}"`（n 从 1 起）。

- [ ] **Step 1: 写 CSV**

```
canteen_name,floor,seat_count
二食堂,1,160
二食堂,2,120
二食堂,3,80
三食堂,1,140
三食堂,2,100
```

- [ ] **Step 2: 写失败测试**

在 `backend/tests/test_seed.py` 末尾追加：

```python
SEATS_CSV = CSV_PATH.with_name("seats.csv")


async def test_seed_seats_creates_seats_per_floor(db):
    await seed_dishes(db, CSV_PATH)
    stats = await seed_seats(db, SEATS_CSV)
    assert stats == {"seat": 600, "skipped_rows": 0}
    assert await _count(db, Seat) == 600
    c2 = await db.scalar(select(Canteen).where(Canteen.name == "二食堂"))
    first = await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-1F-001"))
    assert first is not None and first.canteen_id == c2.id and first.floor == 1
    assert await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-3F-080")) is not None
    assert await db.scalar(select(Seat).where(Seat.code == f"C{c2.id}-3F-081")) is None


async def test_seed_seats_is_idempotent(db):
    await seed_dishes(db, CSV_PATH)
    await seed_seats(db, SEATS_CSV)
    again = await seed_seats(db, SEATS_CSV)
    assert again["seat"] == 0
    assert await _count(db, Seat) == 600


async def test_seed_seats_skips_unknown_canteen(db, tmp_path):
    await seed_dishes(db, CSV_PATH)
    csv_file = tmp_path / "seats.csv"
    csv_file.write_text("canteen_name,floor,seat_count\n不存在食堂,1,10\n二食堂,1,2\n", encoding="utf-8")
    stats = await seed_seats(db, csv_file)
    assert stats == {"seat": 2, "skipped_rows": 1}
```

并把文件顶部的 import 改成 `from app.models import Campus, Canteen, Dish, Seat, Stall, Tag` 与 `from app.tasks.seed import PRESET_TAGS, seed_dishes, seed_seats, seed_tags`。

- [ ] **Step 3: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_seed.py -q`
Expected: ImportError `seed_seats`

- [ ] **Step 4: 实现 seed_seats 与入口**

`backend/app/tasks/seed.py`：导入 `Seat`，模块 docstring 用法改为 `python -m app.tasks.seed ../data/seed/dishes.csv [../data/seed/seats.csv]`，在 `seed_dishes` 之后加：

```python
async def seed_seats(
    session: AsyncSession, csv_path: str | Path, campus_name: str = DEFAULT_CAMPUS
) -> dict[str, int]:
    """按 (食堂, 楼层, 座位数) 生成座位，编码 C{食堂id}-{层}F-{序号:03d}，按 code 幂等。

    依赖 dishes.csv 先导入：找不到的食堂整行跳过并计入 skipped_rows。seat_count 变小不删座位。
    """
    stats = {"seat": 0, "skipped_rows": 0}
    campus = await session.scalar(select(Campus).where(Campus.name == campus_name))
    with Path(csv_path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            canteen = None
            if campus is not None:
                canteen = await session.scalar(
                    select(Canteen).where(
                        Canteen.campus_id == campus.id,
                        Canteen.name == row["canteen_name"].strip(),
                    )
                )
            if canteen is None:
                print(f"警告：食堂不存在，跳过座位行 {row}", file=sys.stderr)
                stats["skipped_rows"] += 1
                continue
            floor = int(row["floor"])
            count = int(row["seat_count"])
            prefix = f"C{canteen.id}-{floor}F-"
            existing = set(
                (await session.scalars(select(Seat.code).where(Seat.code.like(prefix + "%")))).all()
            )
            for n in range(1, count + 1):
                code = f"{prefix}{n:03d}"
                if code in existing:
                    continue
                session.add(Seat(canteen_id=canteen.id, floor=floor, code=code))
                stats["seat"] += 1
    await session.commit()
    return stats
```

`_main` 改为接收可选的第二个参数：

```python
async def _main(csv_path: str, seats_csv: str | None) -> None:
    async with SessionLocal() as session:
        tag_count = await seed_tags(session)
        stats = await seed_dishes(session, csv_path)
        seat_stats = await seed_seats(session, seats_csv) if seats_csv else None
    print(f"预设标签新增 {tag_count} 个")
    print(
        "组织结构新增："
        f"校区 {stats['campus']}，食堂 {stats['canteen']}，"
        f"窗口 {stats['stall']}，菜品 {stats['dish']}"
    )
    if seat_stats is not None:
        print(f"座位新增 {seat_stats['seat']} 个，跳过 {seat_stats['skipped_rows']} 行")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("用法：python -m app.tasks.seed <dishes.csv> [seats.csv]", file=sys.stderr)
        sys.exit(2)
    asyncio.run(_main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None))
```

`Makefile` seed 目标改为：
```
seed:
	cd backend && .venv/bin/python -m app.tasks.seed ../data/seed/dishes.csv ../data/seed/seats.csv
```

`backend/docker-entrypoint.sh` 的 seed 段改为：
```sh
if [ -f ../data/seed/dishes.csv ]; then
  echo "==> seed"
  if [ -f ../data/seed/seats.csv ]; then
    python -m app.tasks.seed ../data/seed/dishes.csv ../data/seed/seats.csv
  else
    python -m app.tasks.seed ../data/seed/dishes.csv
  fi
fi
```

- [ ] **Step 5: 运行通过**

Run: `cd backend && .venv/bin/pytest tests/test_seed.py -q && .venv/bin/ruff check app tests`
Expected: all passed

- [ ] **Step 6: 本地库实际导入一次**

Run: `make migrate && make seed`
Expected: 输出含「座位新增 600 个，跳过 0 行」；再跑一次 `make seed` 输出「座位新增 0 个」。

- [ ] **Step 7: 提交**

```bash
git add data/seed/seats.csv backend/app/tasks/seed.py backend/tests/test_seed.py Makefile backend/docker-entrypoint.sh
git commit -m "feat(seat): 座位种子 seats.csv 与幂等导入

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 座位模拟器与调度

**Files:**
- Create: `backend/app/tasks/seat_sim.py`
- Modify: `backend/app/core/scheduler.py`
- Modify: `Makefile`
- Test: `backend/tests/test_seat_sim.py`

**Interfaces:**
- Consumes: `SeatRepository.list_active_seats()`、`SeatService.apply_states()`（Task 4）；`Settings.seat_simulator_enabled` / `seat_sim_interval_seconds`（Task 3）。
- Consumes（补充）: `SeatReading`（Task 4）。
- Produces: `target_ratio(beijing_minutes: int) -> float`；`floor_target(beijing_minutes: int, floor: int, rng: random.Random) -> float`；`plan_flips(seats: list[tuple[str, bool]], target: float, rng: random.Random) -> list[tuple[str, bool]]`；`simulate_tick(session, now: datetime | None = None, rng: random.Random | None = None) -> int`（返回 applied 数）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_seat_sim.py
"""座位模拟器：餐段曲线插值、单 tick 翻转朝目标靠拢且不越界、走 apply_states 写入。"""

import random
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.models import Campus, Canteen, Seat, SeatState
from app.tasks.seat_sim import floor_target, plan_flips, simulate_tick, target_ratio


def _m(h: int, m: int = 0) -> int:
    return h * 60 + m


def test_target_curve_key_points():
    assert target_ratio(_m(3)) == pytest.approx(0.03)
    assert target_ratio(_m(12)) == pytest.approx(0.90)
    assert target_ratio(_m(18)) == pytest.approx(0.85)
    assert target_ratio(_m(15)) == pytest.approx(0.08)
    assert target_ratio(_m(22)) == pytest.approx(0.05)


def test_target_curve_interpolates_between_points():
    # 11:00 → 0.08，11:30 → 0.90，11:15 应在中间
    mid = target_ratio(_m(11, 15))
    assert 0.08 < mid < 0.90
    assert mid == pytest.approx(0.49, abs=0.01)


def test_floor_target_decreases_with_floor_and_is_clamped():
    rng = random.Random(1)
    f1 = [floor_target(_m(12), 1, rng) for _ in range(50)]
    f3 = [floor_target(_m(12), 3, rng) for _ in range(50)]
    assert all(0.0 <= x <= 0.98 for x in f1 + f3)
    assert sum(f1) / 50 > sum(f3) / 50


def test_plan_flips_moves_toward_target_without_overshoot():
    rng = random.Random(7)
    seats = [(f"S{i:03d}", False) for i in range(100)]  # 全空，目标 50%
    flips = plan_flips(seats, 0.5, rng)
    turned_on = [c for c, occ in flips if occ]
    # 每 tick 最多翻 5% 朝目标 + 1% 随机进出
    assert 5 <= len(turned_on) <= 6
    assert len(flips) <= 6
    assert len({c for c, _ in flips}) == len(flips)  # 同一座位不重复出现


def test_plan_flips_at_target_only_churns():
    rng = random.Random(3)
    seats = [(f"S{i:03d}", i < 50) for i in range(100)]
    flips = plan_flips(seats, 0.5, rng)
    assert len(flips) == 1  # 1% 随机进出


def test_plan_flips_handles_empty_floor():
    assert plan_flips([], 0.9, random.Random(0)) == []


async def test_simulate_tick_writes_states_via_service(db):
    canteen = Canteen(name="二食堂", floors=1, campus=Campus(name="主校区"))
    db.add(canteen)
    await db.flush()
    db.add_all([Seat(canteen_id=canteen.id, floor=1, code=f"C1-1F-{i:03d}") for i in range(1, 41)])
    db.add(Seat(canteen_id=canteen.id, floor=1, code="C1-1F-OFF", is_active=False))
    await db.commit()

    noon_beijing = datetime(2026, 11, 10, 4, 0)  # UTC 04:00 = 北京 12:00，目标 0.9
    applied = await simulate_tick(db, now=noon_beijing, rng=random.Random(42))
    assert applied >= 1
    occupied = await db.scalar(
        select(func.count()).select_from(SeatState).where(SeatState.is_occupied.is_(True))
    )
    # 40 座 × 5% = 2 个朝目标，最多再 0 个随机（int(40*0.01)=0）
    assert 1 <= occupied <= 2
    # 停用座位不会被写入
    off_id = await db.scalar(select(Seat.id).where(Seat.code == "C1-1F-OFF"))
    assert await db.scalar(select(SeatState).where(SeatState.seat_id == off_id)) is None


async def test_simulate_tick_with_no_seats_is_noop(db):
    assert await simulate_tick(db, now=datetime(2026, 11, 10, 4, 0)) == 0
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && .venv/bin/pytest tests/test_seat_sim.py -q`
Expected: ModuleNotFoundError `app.tasks.seat_sim`

- [ ] **Step 3: 实现模拟器**

```python
# backend/app/tasks/seat_sim.py
"""座位模拟器：没有真实传感器时，按餐段曲线生成座位进出。

扮演"传感器网关"的角色：算出要翻转的座位后，走 SeatService.apply_states 写入；
将来真硬件接入也会调同一个方法。不知道调度器的存在：定时任务、命令行、测试都直接调 simulate_tick。
用法：python -m app.tasks.seat_sim
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models._mixins import utcnow
from app.repositories.seat_repo import SeatRepository
from app.schemas.seat import SeatReading
from app.services.seat_service import SeatService

BEIJING_OFFSET = timedelta(hours=8)

# (北京时间分钟数, 目标占用率)，分段线性插值。spec 第 5 节的表展开成折线。
TARGET_CURVE: tuple[tuple[int, float], ...] = (
    (0, 0.03),
    (390, 0.03),  # 06:30
    (420, 0.35),  # 07:00 早餐
    (510, 0.35),  # 08:30
    (570, 0.08),  # 09:30
    (660, 0.08),  # 11:00
    (690, 0.90),  # 11:30 午高峰
    (750, 0.90),  # 12:30
    (810, 0.08),  # 13:30
    (990, 0.08),  # 16:30
    (1050, 0.85),  # 17:30 晚高峰
    (1110, 0.85),  # 18:30
    (1200, 0.05),  # 20:00
    (1440, 0.05),
)
# 层间系数：1 层最挤，越高越空；未列出的楼层用 DEFAULT_FLOOR_FACTOR
FLOOR_FACTOR: dict[int, float] = {1: 1.0, 2: 0.9}
DEFAULT_FLOOR_FACTOR = 0.8
NOISE = 0.05  # 目标占用率随机噪声 ±
MAX_RATIO = 0.98
MAX_FLIP_SHARE = 0.05  # 每 tick 朝目标最多翻转的座位比例
CHURN_SHARE = 0.01  # 每 tick 额外随机进出比例


def target_ratio(beijing_minutes: int) -> float:
    m = beijing_minutes % 1440
    for (m0, r0), (m1, r1) in zip(TARGET_CURVE, TARGET_CURVE[1:], strict=False):
        if m0 <= m <= m1:
            if m1 == m0:
                return r1
            return r0 + (r1 - r0) * (m - m0) / (m1 - m0)
    return TARGET_CURVE[-1][1]


def floor_target(beijing_minutes: int, floor: int, rng: random.Random) -> float:
    base = target_ratio(beijing_minutes) * FLOOR_FACTOR.get(floor, DEFAULT_FLOOR_FACTOR)
    return min(MAX_RATIO, max(0.0, base + rng.uniform(-NOISE, NOISE)))


def plan_flips(
    seats: list[tuple[str, bool]], target: float, rng: random.Random
) -> list[tuple[str, bool]]:
    """给定一层的 (code, is_occupied) 与目标占用率，返回本 tick 要翻转的 (code, 新状态)。"""
    total = len(seats)
    if total == 0:
        return []
    occupied = [c for c, occ in seats if occ]
    free = [c for c, occ in seats if not occ]
    gap = round(target * total) - len(occupied)
    step = min(abs(gap), max(1, int(total * MAX_FLIP_SHARE)))

    flips: dict[str, bool] = {}
    if gap > 0:
        for c in rng.sample(free, min(step, len(free))):
            flips[c] = True
    elif gap < 0:
        for c in rng.sample(occupied, min(step, len(occupied))):
            flips[c] = False

    # 随机进出：高峰时也有人起身、有人坐下
    churn = int(total * CHURN_SHARE)
    remaining = [(c, occ) for c, occ in seats if c not in flips]
    for c, occ in rng.sample(remaining, min(churn, len(remaining))):
        flips[c] = not occ
    return list(flips.items())


def _beijing_minutes(now: datetime) -> int:
    local = now + BEIJING_OFFSET
    return local.hour * 60 + local.minute


async def simulate_tick(
    session: AsyncSession, now: datetime | None = None, rng: random.Random | None = None
) -> int:
    """跑一个 tick：每个食堂每层朝目标占用率翻转少量座位。返回写入的座位数。"""
    now = now or utcnow()
    rng = rng or random.Random()
    repo = SeatRepository(session)
    rows = await repo.list_active_seats()
    if not rows:
        return 0

    by_floor: dict[tuple[int, int], list[tuple[str, bool]]] = {}
    for seat, state in rows:
        occ = bool(state.is_occupied) if state is not None else False
        by_floor.setdefault((seat.canteen_id, seat.floor), []).append((seat.code, occ))

    minutes = _beijing_minutes(now)
    readings: list[SeatReading] = []
    for (_, floor), seats in by_floor.items():
        target = floor_target(minutes, floor, rng)
        readings.extend(
            SeatReading(code=code, is_occupied=occ, ts=now)
            for code, occ in plan_flips(seats, target, rng)
        )
    if not readings:
        return 0
    result = await SeatService(repo).apply_states(readings, now=now)
    return result.applied


async def _main() -> None:
    async with SessionLocal() as session:
        applied = await simulate_tick(session)
    print(f"座位模拟器：本 tick 写入 {applied} 个座位状态")


if __name__ == "__main__":
    asyncio.run(_main())
```

- [ ] **Step 4: 运行模拟器测试通过**

Run: `cd backend && .venv/bin/pytest tests/test_seat_sim.py -q`
Expected: 8 passed。若 `test_plan_flips_moves_toward_target_without_overshoot` 的随机进出把一个已翻开的座位又翻回去导致 `turned_on` 为 4，说明 `remaining` 过滤失效，检查 `c not in flips`。

- [ ] **Step 5: 接调度器与 Makefile**

`backend/app/core/scheduler.py`：导入 `from app.tasks.seat_sim import simulate_tick`，加任务函数：

```python
async def seat_sim_job() -> None:
    async with SessionLocal() as session:
        applied = await simulate_tick(session)
    log.debug("座位模拟器 tick：写入 %d 个座位", applied)
```

在 `start_scheduler` 的 `scheduler.start()` 之前加：

```python
    if settings.seat_simulator_enabled:
        scheduler.add_job(
            seat_sim_job,
            "interval",
            seconds=settings.seat_sim_interval_seconds,
            id="seat_sim",
            next_run_time=datetime.now(),
            coalesce=True,
            max_instances=1,
        )
        log.info("座位模拟器已启用：每 %d 秒一个 tick", settings.seat_sim_interval_seconds)
```

`Makefile`：`.PHONY` 加 `seat-sim`，在 `rankings` 目标后加：

```
# 手动跑一个座位模拟 tick（服务运行时 SEAT_SIMULATOR_ENABLED=true 每 5 秒自动跑）
seat-sim:
	cd backend && .venv/bin/python -m app.tasks.seat_sim
```

- [ ] **Step 6: 全量测试 + 实跑一个 tick**

Run: `cd backend && .venv/bin/pytest -q && .venv/bin/ruff check app tests && cd .. && make seat-sim`
Expected: 全部通过；`make seat-sim` 输出「本 tick 写入 N 个座位状态」且 N ≥ 1（本地库已有 Task 6 的 600 个座位）。

- [ ] **Step 7: 提交**

```bash
git add backend/app/tasks/seat_sim.py backend/app/core/scheduler.py backend/tests/test_seat_sim.py Makefile
git commit -m "feat(seat): 座位模拟器按餐段曲线生成进出，APScheduler 每 5 秒一个 tick

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 前端「食堂空位」区块

**Files:**
- Modify: `frontend/src/types/api.ts`
- Create: `frontend/src/api/seats.ts`
- Modify: `frontend/src/hooks/queries.ts`
- Create: `frontend/src/components/SeatOccupancy.tsx`
- Modify: `frontend/src/pages/Canteens.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `GET /api/v1/seats/occupancy`（Task 5）。
- Produces: `useSeatOccupancy()`；`<SeatOccupancy />`。

- [ ] **Step 1: 类型**

`frontend/src/types/api.ts` 末尾追加：

```ts
/* ---------- 座位空位 ---------- */

export type SeatLevel = "unknown" | "empty" | "low" | "medium" | "high" | "full";

export interface FloorOccupancy {
  floor: number;
  total: number;
  occupied: number;
  free: number;
  /** occupied / total，3 位小数；total 为 0 时 0 */
  ratio: number;
  level: SeatLevel;
  /** 该层最近一次传感器心跳（UTC naive），没有座位状态时 null */
  updated_at: string | null;
}

export interface CanteenOccupancy {
  canteen_id: number;
  canteen_name: string;
  floors: number;
  levels: FloorOccupancy[];
}
```

- [ ] **Step 2: API 与 hook**

```ts
// frontend/src/api/seats.ts
import { api } from "./client";
import type { CanteenOccupancy } from "@/types/api";

export const seatsApi = {
  occupancy: () => api.get<CanteenOccupancy[]>("/seats/occupancy"),
};
```

`frontend/src/hooks/queries.ts`：导入 `seatsApi`，`keys` 加 `seatOccupancy: ["seats", "occupancy"] as const`，末尾加：

```ts
/** 食堂空位：5 秒轮询，页面在后台时暂停 */
export const useSeatOccupancy = () =>
  useQuery({
    queryKey: keys.seatOccupancy,
    queryFn: seatsApi.occupancy,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
```

- [ ] **Step 3: 组件**

```tsx
// frontend/src/components/SeatOccupancy.tsx
/** 食堂空位区块：每食堂一张卡，每层一行「N层 ● 拥挤度  剩 x / y」+ 进度条。5 秒轮询。 */
import { useEffect, useState } from "react";
import { useSeatOccupancy } from "@/hooks/queries";
import type { CanteenOccupancy, FloorOccupancy, SeatLevel } from "@/types/api";

const LEVEL_LABEL: Record<SeatLevel, string> = {
  unknown: "暂无数据",
  empty: "空闲",
  low: "较少",
  medium: "适中",
  high: "较多",
  full: "爆满",
};

function latestUpdate(c: CanteenOccupancy): number | null {
  const ts = c.levels
    .map((l) => l.updated_at)
    .filter((t): t is string => t !== null)
    .map((t) => Date.parse(t.endsWith("Z") ? t : t + "Z"));
  return ts.length ? Math.max(...ts) : null;
}

function agoText(ms: number | null, now: number): string {
  if (ms === null) return "暂无数据";
  const sec = Math.max(0, Math.round((now - ms) / 1000));
  if (sec < 60) return `${sec} 秒前更新`;
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前更新`;
  return "超过 1 小时未更新";
}

function FloorRow({ f }: { f: FloorOccupancy }) {
  const pct = Math.round(f.ratio * 100);
  return (
    <li className={`seat-floor level-${f.level}`}>
      <span className="seat-floor-name">{f.floor}层</span>
      <span className="seat-dot" aria-hidden />
      <span className="seat-level">{LEVEL_LABEL[f.level]}</span>
      <span className="seat-free">
        {f.level === "unknown" ? "—" : `剩 ${f.free} / ${f.total}`}
      </span>
      <span className="seat-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${pct}%` }} />
      </span>
    </li>
  );
}

export function SeatOccupancy() {
  const { data, isLoading, error } = useSeatOccupancy();
  // 每秒重算「x 秒前更新」文案
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (isLoading) return <p className="state">加载空位中…</p>;
  if (error) return <p className="state state-error">空位数据暂时不可用</p>;
  if (!data?.length) return null;

  return (
    <section>
      <h2 className="section-title">食堂空位</h2>
      <ul className="cards">
        {data.map((c) => (
          <li key={c.canteen_id} className="seat-card">
            <div className="seat-card-head">
              <strong>
                {c.canteen_name} <small>{c.floors}层</small>
              </strong>
              <small>{agoText(latestUpdate(c), now)}</small>
            </div>
            <ul className="seat-floors">
              {c.levels.map((f) => (
                <FloorRow key={f.floor} f={f} />
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: 挂到食堂列表页**

`frontend/src/pages/Canteens.tsx` 改为（原列表不动，下面挂区块；列表为空时区块也不显示）：

```tsx
import { Link } from "react-router-dom";
import { useCanteens } from "@/hooks/queries";
import { Empty, ErrorState, Loading } from "@/components/State";
import { SeatOccupancy } from "@/components/SeatOccupancy";

export function Canteens() {
  const { data, isLoading, error } = useCanteens();
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!data?.length) return <Empty>还没有食堂数据，请先导入种子数据</Empty>;
  return (
    <>
      <ul className="cards">
        {data.map((c) => (
          <li key={c.id}>
            <Link to={`/canteen/${c.id}`} className="card">
              <strong>{c.name}</strong>
              <small>{c.floors} 层</small>
            </Link>
          </li>
        ))}
      </ul>
      <SeatOccupancy />
    </>
  );
}
```

- [ ] **Step 5: 样式**

`frontend/src/index.css` 追加一段：

```css
/* ---------- 食堂空位 ---------- */
.seat-card {
  display: flex; flex-direction: column; gap: .6rem; padding: .85rem 1rem; border-radius: .9rem;
  background: color-mix(in srgb, var(--fg) 4%, transparent);
}
.seat-card-head { display: flex; justify-content: space-between; align-items: baseline; }
.seat-card-head strong small { color: var(--muted); font-weight: 400; margin-left: .35rem; }
.seat-card-head > small { color: var(--muted); font-size: .75rem; font-variant-numeric: tabular-nums; }
.seat-floors { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .45rem; }
.seat-floor {
  --tone: var(--muted);
  display: grid; grid-template-columns: 2.4rem .6rem 4rem 1fr; grid-template-rows: auto auto;
  align-items: center; column-gap: .4rem; row-gap: .3rem; font-size: .9rem;
}
.seat-floor-name { font-weight: 600; }
.seat-dot { width: .6rem; height: .6rem; border-radius: 50%; background: var(--tone); }
.seat-level { color: var(--tone); font-weight: 600; }
.seat-free { text-align: right; color: var(--muted); font-size: .85rem; font-variant-numeric: tabular-nums; }
.seat-bar {
  grid-column: 1 / -1; display: block; height: .3rem; border-radius: 999px; overflow: hidden;
  background: color-mix(in srgb, var(--fg) 8%, transparent);
}
.seat-bar span { display: block; height: 100%; background: var(--tone); transition: width .6s ease; }
.level-empty, .level-low { --tone: var(--good); }
.level-medium { --tone: #d9a400; }
.level-high { --tone: #e8761e; }
.level-full { --tone: var(--bad); }
.level-unknown { --tone: var(--muted); }
```

- [ ] **Step 6: 类型检查与构建**

Run: `cd frontend && npm run build`
Expected: `tsc -b` 无错误，vite 构建成功。

- [ ] **Step 7: 本地联调看一眼**

启动 `make dev-api`（`.env` 里 `SEAT_SIMULATOR_ENABLED=true`）与 `make dev-web`，登录后打开 `/canteens`：
- 上方两张食堂卡不变；下方「食堂空位」两张卡，二食堂 3 行、三食堂 2 行。
- 每行有颜色点、档位中文、`剩 x / y`、进度条；右上「x 秒前更新」每秒变化，5 秒左右数字会跳（模拟器每 tick 翻几个座位）。
- 用无头浏览器（npx 缓存的 playwright）截一张 `/canteens` 页截图确认布局与原型一致。

- [ ] **Step 8: 提交**

```bash
git add frontend/src/types/api.ts frontend/src/api/seats.ts frontend/src/hooks/queries.ts frontend/src/components/SeatOccupancy.tsx frontend/src/pages/Canteens.tsx frontend/src/index.css
git commit -m "feat(web): 食堂列表页「食堂空位」区块，按层显示拥挤度与剩余座位，5 秒轮询

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: 文档同步与全量验证

**Files:**
- Modify: `docs/架构设计.md`（5.2 节、6 节、7 章）
- Modify: `CLAUDE.md`（当前状态）
- Modify: `README.md`（如有接口清单/环境变量表则同步）

- [ ] **Step 1: 架构文档**

`docs/架构设计.md`：
- 5.2「派生 / 快照表」之前新增小节：

```markdown
#### 座位（M2 新增）

```sql
seat        (id, canteen_id, floor, code UNIQUE,   -- 传感器编码 C{食堂id}-{层}F-{序号}
             is_active)
seat_state  (seat_id PK, is_occupied, changed_at,   -- 最近一次翻转
             updated_at)                            -- 最近一次心跳；无记录视为空闲
```

每层人数不建表，查询时按 `(canteen_id, floor)` GROUP BY 现算。
```

- 6.3 表格追加一行：

```markdown
| GET | `/seats/occupancy?campus_id=` | 每个在营食堂每层的 total / occupied / free / ratio / level（需登录，前端 5 秒轮询） |
```

- 第 7 章 7.6「座位拥挤度与传感器接入」**已在设计阶段写入**（含概念链路、分层阈值、模拟器曲线），本任务只核对内容与实现一致（阈值、曲线、方法名 `SeatService.apply_states`）；不一致处以代码为准改文档。

- [ ] **Step 2: CLAUDE.md**

「当前状态」在「下一步」之前加一条：

```markdown
- 已有：食堂空余座位。表 `seat`（静态，`data/seed/seats.csv` 幂等导入，编码 `C{食堂id}-{层}F-{序号}`）+ `seat_state`（当前状态，迁移 c4d5e6f7a8b9），每层人数现算不建表。**传感器硬件与上报接口只在 `docs/架构设计.md` 7.6 做概念说明，不落码**；读数写入唯一入口 `SeatService.apply_states(readings)`（同批同 code 取最后一条；`changed_at` 只在翻转时动、`updated_at` 每条读数动；未知/停用 code 进 `unknown_codes`），本期只有模拟器调用。`GET /seats/occupancy?campus_id=`（需登录）按食堂 × 1..floors 列每层 total/occupied/free/ratio/level，阈值在 `app/seating/levels.py`（空闲 <25% / 较少 / 适中 / 较多 / 爆满 ≥85%，无座位 unknown）。模拟器 `app/tasks/seat_sim.py`（`SEAT_SIMULATOR_ENABLED`，每 `SEAT_SIM_INTERVAL_SECONDS`=5 秒一个 tick，按北京时间餐段曲线、每 tick 最多翻 5% 座位 + 1% 随机进出，走 apply_states 同一条路径；`make seat-sim`）。前端 `/canteens` 页下方 `components/SeatOccupancy.tsx`，`useSeatOccupancy` 5 秒轮询。没有做：`/sensors` 上报接口与设备鉴权、座位点阵图、历史曲线、`seat_event` 流。
```

- [ ] **Step 3: 全量验证**

Run: `make test && make lint && cd frontend && npm run build`
Expected: 后端全部通过、ruff 干净、前端构建成功。

- [ ] **Step 4: 提交**

```bash
git add docs/架构设计.md CLAUDE.md README.md
git commit -m "docs: 架构文档与 CLAUDE.md 同步食堂空余座位功能

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```
