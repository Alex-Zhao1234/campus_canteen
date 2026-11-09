/** 服务端状态都走这里。queryKey 集中定义，评价提交后按键失效缓存。 */
import { useQuery } from "@tanstack/react-query";
import { orgApi } from "@/api/org";
import { rankingsApi } from "@/api/rankings";
import { reviewsApi } from "@/api/reviews";
import type { RankingType } from "@/types/api";

export const keys = {
  canteens: ["canteens"] as const,
  stalls: (canteenId: number) => ["stalls", canteenId] as const,
  stall: (stallId: number) => ["stall", stallId] as const,
  dish: (dishId: number) => ["dish", dishId] as const,
  rankings: ["rankings"] as const,
  tags: ["tags"] as const,
  myReviews: ["me", "reviews"] as const,
  ranking: (type: RankingType, canteenId: number | null) =>
    ["rankings", type, canteenId] as const,
};

export const useCanteens = () =>
  useQuery({ queryKey: keys.canteens, queryFn: orgApi.canteens, staleTime: 60 * 60 * 1000 });

export const useStalls = (canteenId: number) =>
  useQuery({ queryKey: keys.stalls(canteenId), queryFn: () => orgApi.stalls(canteenId) });

export const useStall = (stallId: number) =>
  useQuery({ queryKey: keys.stall(stallId), queryFn: () => orgApi.stall(stallId) });

export const useDish = (dishId: number) =>
  useQuery({ queryKey: keys.dish(dishId), queryFn: () => orgApi.dish(dishId) });

export const useRanking = (type: RankingType, canteenId: number | null) =>
  useQuery({
    queryKey: keys.ranking(type, canteenId),
    queryFn: () => rankingsApi.today(type, canteenId),
  });

export const useTags = () =>
  useQuery({ queryKey: keys.tags, queryFn: reviewsApi.tags, staleTime: 60 * 60 * 1000 });
