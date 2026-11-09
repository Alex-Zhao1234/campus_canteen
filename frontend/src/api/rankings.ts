import { api } from "./client";
import type { Ranking, RankingType } from "@/types/api";

export const rankingsApi = {
  today: (type: RankingType, canteenId: number | null) => {
    const q = new URLSearchParams({ type });
    if (canteenId !== null) q.set("canteen_id", String(canteenId));
    return api.get<Ranking>(`/rankings/today?${q}`);
  },
};
