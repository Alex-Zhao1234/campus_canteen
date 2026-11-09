import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reviewsApi } from "@/api/reviews";
import { keys } from "@/hooks/queries";
import { useAuthStore } from "@/stores/auth";
import type { MyReview } from "@/types/api";

export function useMyReviews() {
  const token = useAuthStore((s) => s.token);
  return useQuery({ queryKey: keys.myReviews, queryFn: reviewsApi.mine, enabled: !!token });
}

/** 删除所需的最少信息；MyReview 直接满足，评论区条目补上 dish_id / stall_id 即可 */
export interface ReviewRef {
  id: number;
  dish_id: number;
  stall_id: number;
}

/** 删除（后端软删）：乐观从"我的评价"移除，失败回滚，成功后失效相关缓存让分数回落、评论区刷新。 */
export function useDeleteReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (review: ReviewRef) => reviewsApi.remove(review.id),
    onMutate: async (review) => {
      await qc.cancelQueries({ queryKey: keys.myReviews });
      const prev = qc.getQueryData<MyReview[]>(keys.myReviews);
      if (prev) qc.setQueryData<MyReview[]>(keys.myReviews, prev.filter((r) => r.id !== review.id));
      return { prev };
    },
    onError: (_e, _r, ctx) => {
      if (ctx?.prev) qc.setQueryData(keys.myReviews, ctx.prev);
    },
    onSettled: (_d, _e, review) => {
      qc.invalidateQueries({ queryKey: keys.myReviews });
      qc.invalidateQueries({ queryKey: keys.stall(review.stall_id) });
      qc.invalidateQueries({ queryKey: keys.dish(review.dish_id) });
      qc.invalidateQueries({ queryKey: keys.rankings });
    },
  });
}
