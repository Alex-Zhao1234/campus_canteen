import { api } from "./client";
import type { RandomRecommend, RecommendFilters } from "@/types/api";

export const recommendApi = {
  random: (f: RecommendFilters, exclude: number[]) => {
    const q = new URLSearchParams();
    if (f.canteenId !== null) q.set("canteen_id", String(f.canteenId));
    if (f.budget !== null) q.set("budget", String(f.budget));
    if (f.spicy !== null) q.set("spicy", String(f.spicy));
    if (f.veg) q.set("veg", "true");
    if (exclude.length) q.set("exclude", exclude.join(","));
    const qs = q.toString();
    return api.get<RandomRecommend>(`/recommend/random${qs ? `?${qs}` : ""}`);
  },
};
