/** 随机推荐不走缓存：每次打开/换一个都重抽；exclude 累积已看过的菜，用尽后清空。 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { recommendApi } from "@/api/recommend";
import type { RecommendFilters } from "@/types/api";

export function useRandomPick(filters: RecommendFilters, enabled: boolean) {
  const [exclude, setExclude] = useState<number[]>([]);
  const [exhausted, setExhausted] = useState(false);
  const filterKey = JSON.stringify(filters);
  const prevKey = useRef(filterKey);

  // 约束变化 → 清空已看过，重新开始
  useEffect(() => {
    if (prevKey.current !== filterKey) {
      prevKey.current = filterKey;
      setExclude([]);
      setExhausted(false);
    }
  }, [filterKey]);

  const query = useQuery({
    queryKey: ["recommend", "random", filterKey, exclude],
    queryFn: () => recommendApi.random(filters, exclude),
    enabled,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });

  const reroll = useCallback(() => {
    const data = query.data;
    if (!data) return;
    const seen = [data.pick?.dish_id, ...data.alternates.map((a) => a.dish_id)].filter(
      (x): x is number => x !== undefined,
    );
    const next = [...exclude, ...seen];
    // 候选都看过了：提示并从头来
    if (data.candidate_count <= seen.length) {
      setExhausted(true);
      setExclude([]);
      return;
    }
    setExhausted(false);
    setExclude(next);
  }, [query.data, exclude]);

  return { ...query, reroll, exhausted, seenCount: exclude.length };
}
