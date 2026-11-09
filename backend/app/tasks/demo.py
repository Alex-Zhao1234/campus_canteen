"""演示评价：评价表为空时写入一批分布合理的评价，让榜单、踩雷标记一打开就有内容。

只在 SEED_DEMO_REVIEWS=true 的演示环境启用（Render 免费实例休眠后数据清空，每次唤醒重建）。
写入的是真实的 review 事件，之后由榜单任务按正常公式算分，不伪造 stats。
用法：python -m app.tasks.demo
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campus, Dish, Review, Tag, User
from app.models._mixins import utcnow
from app.services.auth_service import hash_email

DEMO_USERS = [
    ("demo-a@demo.edu.cn", "演示同学 A"),
    ("demo-b@demo.edu.cn", "演示同学 B"),
    ("demo-c@demo.edu.cn", "演示同学 C"),
    ("demo-d@demo.edu.cn", "演示同学 D"),
    ("demo-e@demo.edu.cn", "演示同学 E"),
]

# (菜名, 用户序号, verdict, 距今小时数, 标签 codes, 评论)
# 同一用户同一菜同一北京日只能一条，下面的组合已错开。
DEMO_REVIEWS: list[tuple[str, int, str, float, list[str], str | None]] = [
    # 麻辣香锅(荤)：口碑最好 → 好评榜第一
    ("麻辣香锅(荤)", 0, "good", 3, ["worth_it", "portion_good"], "料足，18 块很值"),
    ("麻辣香锅(荤)", 1, "good", 6, ["fresh"], None),
    ("麻辣香锅(荤)", 2, "good", 26, ["portion_good"], "分量实在"),
    ("麻辣香锅(荤)", 3, "good", 30, [], None),
    ("麻辣香锅(荤)", 4, "ok", 50, ["queue_long"], "中午排队有点久"),
    ("麻辣香锅(荤)", 0, "good", 75, [], None),
    # 番茄炒蛋：稳定好评
    ("番茄炒蛋", 1, "good", 4, ["worth_it"], "8 块钱吃饱"),
    ("番茄炒蛋", 2, "good", 28, [], None),
    ("番茄炒蛋", 3, "good", 52, ["fresh"], None),
    ("番茄炒蛋", 4, "ok", 100, [], None),
    # 肉包：早餐好评
    ("肉包", 0, "good", 5, ["worth_it"], None),
    ("肉包", 2, "good", 29, [], "皮薄馅大"),
    ("肉包", 4, "ok", 53, [], None),
    # 豆浆：一般偏好
    ("豆浆", 1, "good", 7, [], None),
    ("豆浆", 3, "ok", 31, ["bland"], "有点淡"),
    # 麻辣香锅(素)：褒贬不一
    ("麻辣香锅(素)", 2, "good", 8, [], None),
    ("麻辣香锅(素)", 3, "bad", 27, ["too_oily"], "太油了"),
    # 鱼香肉丝：近 24h 集中踩雷 → 踩雷榜 + 家常小炒窗口黄牌
    ("鱼香肉丝", 0, "bad", 2, ["too_salty", "quality_drop"], "换厨师了？齁咸"),
    ("鱼香肉丝", 1, "bad", 5, ["too_oily"], None),
    ("鱼香肉丝", 2, "bad", 9, ["quality_drop"], "不如以前"),
    ("鱼香肉丝", 3, "bad", 20, ["too_salty"], None),
    ("鱼香肉丝", 4, "ok", 70, [], None),
]


async def seed_demo_reviews(session: AsyncSession, now: datetime | None = None) -> int:
    """评价表为空且有菜品时写入演示评价。返回写入条数。"""
    now = now or utcnow()
    if await session.scalar(select(func.count()).select_from(Review)):
        return 0
    dishes = {d.name: d for d in (await session.scalars(select(Dish))).all()}
    if not dishes:
        return 0
    campus_id = await session.scalar(select(Campus.id).order_by(Campus.id).limit(1))
    tags = {t.code: t for t in (await session.scalars(select(Tag))).all()}

    users: list[User] = []
    for email, nickname in DEMO_USERS:
        h = hash_email(email)
        user = await session.scalar(select(User).where(User.email_hash == h))
        if user is None:
            user = User(email_hash=h, nickname=nickname, campus_id=campus_id)
            session.add(user)
        users.append(user)
    await session.flush()

    created = 0
    for dish_name, ui, verdict, hours_ago, codes, comment in DEMO_REVIEWS:
        dish = dishes.get(dish_name)
        if dish is None:
            continue  # 自定义 CSV 里没有这道菜就跳过
        review = Review(
            user_id=users[ui].id,
            dish_id=dish.id,
            stall_id=dish.stall_id,
            verdict=verdict,
            comment=comment,
            created_at=now - timedelta(hours=hours_ago),
        )
        review.tags = [tags[c] for c in codes if c in tags]
        session.add(review)
        created += 1
    await session.commit()
    return created


async def _main() -> None:
    from app.core.database import SessionLocal

    async with SessionLocal() as session:
        n = await seed_demo_reviews(session)
    print(f"演示评价写入 {n} 条" if n else "评价表非空或无菜品，跳过演示评价")


if __name__ == "__main__":
    asyncio.run(_main())
