"""榜单接口只读快照，再关联菜名/窗口名。"""

from app.repositories.ranking_repo import RankingRepository
from app.schemas.ranking import RankingItemOut, RankingOut


class RankingService:
    def __init__(self, repo: RankingRepository) -> None:
        self.repo = repo

    async def today(
        self, ranking_type: str, canteen_id: int | None, campus_id: int | None
    ) -> RankingOut:
        if campus_id is None:
            campus_id = await self.repo.first_campus_id()
        empty = RankingOut(
            ranking_type=ranking_type,
            campus_id=campus_id,
            canteen_id=canteen_id,
            generated_at=None,
            items=[],
        )
        if campus_id is None:
            return empty
        snap = await self.repo.get_latest_snapshot(campus_id, canteen_id, ranking_type)
        if snap is None:
            return empty

        briefs = await self.repo.list_dish_briefs([i["dish_id"] for i in snap.payload_json])
        items = []
        for entry in snap.payload_json:
            found = briefs.get(entry["dish_id"])
            if found is None:  # 快照生成后菜被删了，跳过
                continue
            dish, stall, canteen = found
            items.append(
                RankingItemOut(
                    rank=entry["rank"],
                    dish_id=dish.id,
                    dish_name=dish.name,
                    stall_id=stall.id,
                    stall_name=stall.name,
                    canteen_id=canteen.id,
                    canteen_name=canteen.name,
                    price_cents=dish.price_cents,
                    image_url=dish.image_url,
                    score=entry["score"],
                    review_count_7d=entry["review_count_7d"],
                    delta=entry["delta"],
                )
            )
        return RankingOut(
            ranking_type=ranking_type,
            campus_id=campus_id,
            canteen_id=canteen_id,
            generated_at=snap.generated_at,
            items=items,
        )
