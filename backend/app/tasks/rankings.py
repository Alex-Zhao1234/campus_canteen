"""榜单任务：全量重算 dish/stall stats（让时间衰减生效）→ 生成快照。

不知道调度器的存在：定时任务、命令行、测试都直接调用 rebuild_rankings。
用法：python -m app.tasks.rankings
"""

import asyncio
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models._mixins import utcnow
from app.recommender.ranking import RankingType, build_ranking, min_reviews_for
from app.recommender.stats import DishMetrics, compute_dish_metrics, compute_stall_metrics
from app.repositories.ranking_repo import RankingRepository

RANKING_TYPES_MVP: tuple[RankingType, ...] = ("good", "bad")


@dataclass(frozen=True)
class RebuildSummary:
    dishes: int
    stalls: int
    snapshots: int


async def rebuild_rankings(session: AsyncSession, now: datetime | None = None) -> RebuildSummary:
    now = now or utcnow()
    repo = RankingRepository(session)

    dishes = await repo.list_active_dishes()
    stall_ids = await repo.list_active_stall_ids()
    events = await repo.list_review_events()

    by_dish = defaultdict(list)
    by_stall = defaultdict(list)
    for dish_id, stall_id, ev in events:
        by_dish[dish_id].append(ev)
        by_stall[stall_id].append(ev)

    # 1) 刷新 stats
    dish_stats = await repo.load_dish_stats()
    metrics: dict[int, DishMetrics] = {}
    for dish_id, _, _, _ in dishes:
        m = compute_dish_metrics(by_dish.get(dish_id, []), now)
        metrics[dish_id] = m
        repo.set_dish_stats(dish_stats, dish_id, m)

    stall_stats = await repo.load_stall_stats()
    for stall_id in stall_ids:
        repo.set_stall_stats(
            stall_stats, stall_id, compute_stall_metrics(by_stall.get(stall_id, []), now)
        )

    # 2) 生成快照：每个校区 × (全部食堂 + 每个食堂) × 榜单类型
    min_reviews = min_reviews_for(await repo.count_reviews())
    canteens_by_campus: dict[int, list[int]] = defaultdict(list)
    for canteen_id, campus_id in await repo.list_canteens():
        canteens_by_campus[campus_id].append(canteen_id)

    snapshots = 0
    for campus_id in await repo.list_campus_ids():
        scopes: list[int | None] = [None, *sorted(canteens_by_campus.get(campus_id, []))]
        for canteen_id in scopes:
            candidates = [
                (dish_id, metrics[dish_id])
                for dish_id, _, c_id, camp_id in dishes
                if camp_id == campus_id and (canteen_id is None or c_id == canteen_id)
            ]
            for ranking_type in RANKING_TYPES_MVP:
                previous = await repo.get_latest_snapshot(campus_id, canteen_id, ranking_type)
                previous_ranks = (
                    {item["dish_id"]: item["rank"] for item in previous.payload_json}
                    if previous
                    else None
                )
                items = build_ranking(ranking_type, candidates, min_reviews, previous_ranks)
                await repo.replace_snapshot(
                    campus_id=campus_id,
                    canteen_id=canteen_id,
                    ranking_type=ranking_type,
                    payload=[asdict(i) for i in items],
                    generated_at=now,
                )
                snapshots += 1

    await session.commit()
    return RebuildSummary(dishes=len(dishes), stalls=len(stall_ids), snapshots=snapshots)


async def _main() -> None:
    from app.core.database import SessionLocal

    async with SessionLocal() as session:
        s = await rebuild_rankings(session)
    print(f"已重算 {s.dishes} 道菜、{s.stalls} 个窗口的 stats，写入 {s.snapshots} 份榜单快照")


if __name__ == "__main__":
    asyncio.run(_main())
