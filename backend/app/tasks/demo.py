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
    ("demo-f@demo.edu.cn", "演示同学 F"),
]

# 每道菜的口碑画像：(good, ok, bad, recent_bad)
# recent_bad=True 的踩雷落在近 24h 内 → 触发所在窗口黄牌；其余踩雷都在 24h 之外，避免误伤整个窗口。
# 好评榜 ≥ 10 道正分、踩雷榜 ≥ 10 道 < -0.3，榜首分别是 麻辣香锅(荤) 与 鱼香肉丝。
DEMO_PROFILES: dict[str, tuple[int, int, int, bool]] = {
    # ---- 好评阵营 ----
    "麻辣香锅(荤)": (6, 1, 0, False),
    "番茄炒蛋": (4, 1, 0, False),
    "叉烧饭": (4, 0, 0, False),
    "牛肉面": (3, 1, 0, False),
    "肉包": (3, 1, 0, False),
    "咖喱鸡排饭": (3, 0, 0, False),
    "石锅拌饭": (3, 0, 0, False),
    "肉夹馍": (2, 1, 0, False),
    "锅包肉": (2, 0, 0, False),
    "豆浆": (2, 1, 0, False),
    "红烧肉": (2, 0, 0, False),
    "羊肉泡馍": (1, 1, 0, False),
    # ---- 中性 ----
    "麻辣香锅(素)": (1, 1, 1, False),
    "小米粥": (0, 2, 0, False),
    "刀削面": (1, 0, 1, False),
    # ---- 踩雷阵营 ----
    "鱼香肉丝": (0, 0, 5, True),
    "酸辣土豆丝": (0, 0, 2, False),
    "油条": (0, 1, 3, False),
    "炸酱面": (0, 0, 2, False),
    "冒菜": (0, 1, 3, False),
    "青椒肉丝盖饭": (0, 0, 2, False),
    "白切鸡饭": (0, 1, 2, False),
    "铁板鱿鱼": (0, 0, 3, False),
    "部队锅": (0, 0, 2, False),
    "酸菜白肉": (0, 1, 2, False),
    "农家小炒肉": (0, 0, 2, False),
}

_TAGS = {
    "good": ["worth_it", "portion_good", "fresh"],
    "ok": ["queue_long", "bland", "portion_less"],
    "bad": ["too_salty", "too_oily", "quality_drop", "price_up"],
}
_COMMENTS = {
    "good": ["料足，很值", "分量实在", "今天这个不错", None],
    "ok": ["中午排队有点久", "一般般", None],
    "bad": ["换厨师了？齁咸", "太油了", "不如以前", None],
}


def _demo_events() -> list[tuple[str, int, str, float, list[str], str | None]]:
    """把口碑画像展开成 (菜名, 用户序号, verdict, 距今小时, 标签, 评论) 列表。

    同一道菜的评价依次用不同用户、间隔 ~1 天，天然满足"单人单菜单日一评"。
    """
    events = []
    for dish, (good, ok, bad, recent) in DEMO_PROFILES.items():
        k = 0
        for verdict, count in (("good", good), ("ok", ok), ("bad", bad)):
            for _ in range(count):
                hours = 2 + k * 5 if (recent and verdict == "bad") else 3 + k * 23
                tags = [_TAGS[verdict][k % len(_TAGS[verdict])]] if k % 2 == 0 else []
                comment = _COMMENTS[verdict][k % len(_COMMENTS[verdict])]
                events.append((dish, k % len(DEMO_USERS), verdict, hours, tags, comment))
                k += 1
    return events


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
    for dish_name, ui, verdict, hours_ago, codes, comment in _demo_events():
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
