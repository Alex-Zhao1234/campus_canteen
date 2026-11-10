/** 服务端状态都走这里。queryKey 集中定义，评价提交后按键失效缓存。 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { orgApi } from "@/api/org";
import { rankingsApi } from "@/api/rankings";
import { reviewsApi } from "@/api/reviews";
import { seatsApi } from "@/api/seats";
import type { RankingType } from "@/types/api";

export const keys = {
  canteens: ["canteens"] as const,
  stalls: (canteenId: number) => ["stalls", canteenId] as const,
  stall: (stallId: number) => ["stall", stallId] as const,
  dish: (dishId: number) => ["dish", dishId] as const,
  dishReviews: (dishId: number) => ["dish", dishId, "reviews"] as const,
  rankings: ["rankings"] as const,
  tags: ["tags"] as const,
  myReviews: ["me", "reviews"] as const,
  seatOccupancy: ["seats", "occupancy"] as const,
  seatMap: (canteenId: number, floor: number) => ["seats", "map", canteenId, floor] as const,
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

/** 菜品评论区：游标分页，next_before_id 为 null 表示到底了 */
export const useDishReviews = (dishId: number) =>
  useInfiniteQuery({
    queryKey: keys.dishReviews(dishId),
    queryFn: ({ pageParam }) => reviewsApi.forDish(dishId, pageParam),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => last.next_before_id,
  });

/** 食堂空位：5 秒轮询，页面在后台时暂停 */
export const useSeatOccupancy = () =>
  useQuery({
    queryKey: keys.seatOccupancy,
    queryFn: seatsApi.occupancy,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });

/** 某层座位平面图：只在展开时请求（enabled），同样 5 秒轮询 */
export const useSeatMap = (canteenId: number, floor: number, enabled: boolean) =>
  useQuery({
    queryKey: keys.seatMap(canteenId, floor),
    queryFn: () => seatsApi.map(canteenId, floor),
    enabled,
    refetchInterval: enabled ? 5000 : false,
    refetchIntervalInBackground: false,
  });
