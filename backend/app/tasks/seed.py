"""种子导入：预设标签（架构文档附录 A）+ 组织结构 CSV（附录 B）。

所有函数幂等：按业务键 get-or-create，重复执行不会产生重复数据。
用法：python -m app.tasks.seed ../data/seed/dishes.csv
"""

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import Campus, Canteen, Dish, Stall, Tag

# (category, code, label)，与 docs/架构设计.md 附录 A 保持一致
PRESET_TAGS: tuple[tuple[str, str, str], ...] = (
    ("taste", "too_salty", "偏咸"),
    ("taste", "too_oily", "太油"),
    ("taste", "bland", "没味道"),
    ("taste", "fresh", "新鲜"),
    ("portion", "portion_less", "份量少了"),
    ("portion", "portion_good", "份量实在"),
    ("price", "price_up", "涨价了"),
    ("price", "worth_it", "性价比高"),
    ("service", "queue_long", "排队久"),
    ("service", "attitude_bad", "态度差"),
    ("change", "chef_changed", "换厨师了"),
    ("change", "quality_drop", "不如以前"),
    ("change", "new_dish", "新菜"),
    ("status", "closed_today", "今天没开"),
)

DEFAULT_CAMPUS = "主校区"


async def seed_tags(session: AsyncSession) -> int:
    """写入预设标签，按 code 去重。返回新建数量。"""
    existing = set((await session.scalars(select(Tag.code))).all())
    created = 0
    for category, code, label in PRESET_TAGS:
        if code in existing:
            continue
        session.add(Tag(code=code, label=label, category=category))
        created += 1
    await session.commit()
    return created


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


async def seed_dishes(
    session: AsyncSession, csv_path: str | Path, campus_name: str = DEFAULT_CAMPUS
) -> dict[str, int]:
    """按 CSV 逐行 get-or-create 校区 → 食堂 → 窗口 → 菜品。返回各层新建数量。"""
    stats = {"campus": 0, "canteen": 0, "stall": 0, "dish": 0}

    campus = await session.scalar(select(Campus).where(Campus.name == campus_name))
    if campus is None:
        campus = Campus(name=campus_name)
        session.add(campus)
        await session.flush()
        stats["campus"] += 1

    # 同一次导入内用缓存避免对同一食堂/窗口重复查库
    canteens: dict[str, Canteen] = {}
    stalls: dict[tuple[int, str], Stall] = {}

    with Path(csv_path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            canteen_name = row["canteen_name"].strip()
            floor = int(row["floor"])
            stall_name = row["stall_name"].strip()

            canteen = canteens.get(canteen_name)
            if canteen is None:
                canteen = await session.scalar(
                    select(Canteen).where(
                        Canteen.campus_id == campus.id, Canteen.name == canteen_name
                    )
                )
                if canteen is None:
                    canteen = Canteen(name=canteen_name, floors=floor, campus_id=campus.id)
                    session.add(canteen)
                    await session.flush()
                    stats["canteen"] += 1
                canteens[canteen_name] = canteen
            # 食堂楼层数取 CSV 中出现过的最大楼层
            if floor > canteen.floors:
                canteen.floors = floor

            stall = stalls.get((canteen.id, stall_name))
            if stall is None:
                stall = await session.scalar(
                    select(Stall).where(Stall.canteen_id == canteen.id, Stall.name == stall_name)
                )
                if stall is None:
                    stall = Stall(
                        name=stall_name,
                        floor=floor,
                        cuisine_type=row.get("cuisine_type", "").strip() or None,
                        canteen_id=canteen.id,
                    )
                    session.add(stall)
                    await session.flush()
                    stats["stall"] += 1
                stalls[(canteen.id, stall_name)] = stall

            dish_name = row["dish_name"].strip()
            image_url = (row.get("image_url") or "").strip() or None
            dish = await session.scalar(
                select(Dish).where(Dish.stall_id == stall.id, Dish.name == dish_name)
            )
            if dish is None:
                session.add(
                    Dish(
                        stall_id=stall.id,
                        name=dish_name,
                        price_cents=int(row["price_cents"]),
                        spicy_level=int(row.get("spicy_level") or 0),
                        is_veg=_to_bool(row.get("is_veg") or "0"),
                        dish_type=(row.get("dish_type") or "常驻").strip(),
                        image_url=image_url,
                    )
                )
                stats["dish"] += 1
            elif image_url and not dish.image_url:
                # 已有菜品补图：只填空值，不覆盖人工改过的
                dish.image_url = image_url

    await session.commit()
    return stats


async def _main(csv_path: str) -> None:
    async with SessionLocal() as session:
        tag_count = await seed_tags(session)
        stats = await seed_dishes(session, csv_path)
    print(f"预设标签新增 {tag_count} 个")
    print(
        "组织结构新增："
        f"校区 {stats['campus']}，食堂 {stats['canteen']}，"
        f"窗口 {stats['stall']}，菜品 {stats['dish']}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python -m app.tasks.seed <dishes.csv>", file=sys.stderr)
        sys.exit(2)
    asyncio.run(_main(sys.argv[1]))
