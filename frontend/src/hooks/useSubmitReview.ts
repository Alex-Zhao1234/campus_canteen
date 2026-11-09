/** 提交评价：乐观更新评价数 → 成功后用后端返回的真实 dish_stats 覆盖 → 失效相关缓存。 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewsApi } from "@/api/reviews";
import { keys } from "@/hooks/queries";
import type { DishDetail, DishStats, ReviewCreateIn, StallDetail } from "@/types/api";

function bump(stats: DishStats): DishStats {
  return { ...stats, review_count_7d: stats.review_count_7d + 1, review_count_all: stats.review_count_all + 1 };
}

export function useSubmitReview(stallId: number, dishId: number) {
  const qc = useQueryClient();
  const stallKey = keys.stall(stallId);
  const dishKey = keys.dish(dishId);

  return useMutation({
    mutationFn: (body: ReviewCreateIn) => reviewsApi.create(body),

    onMutate: async () => {
      // 先取消进行中的读请求，避免旧数据覆盖乐观结果
      await Promise.all([qc.cancelQueries({ queryKey: stallKey }), qc.cancelQueries({ queryKey: dishKey })]);
      const prevStall = qc.getQueryData<StallDetail>(stallKey);
      const prevDish = qc.getQueryData<DishDetail>(dishKey);
      if (prevStall) {
        qc.setQueryData<StallDetail>(stallKey, {
          ...prevStall,
          dishes: prevStall.dishes.map((d) => (d.id === dishId ? { ...d, stats: bump(d.stats) } : d)),
        });
      }
      if (prevDish) qc.setQueryData<DishDetail>(dishKey, { ...prevDish, stats: bump(prevDish.stats) });
      return { prevStall, prevDish };
    },

    onError: (_err, _body, ctx) => {
      // 回滚快照；具体错误提示由组件处理
      if (ctx?.prevStall) qc.setQueryData(stallKey, ctx.prevStall);
      if (ctx?.prevDish) qc.setQueryData(dishKey, ctx.prevDish);
    },

    onSuccess: (created) => {
      // 分数公式前端算不准，用后端返回的真值覆盖
      const stall = qc.getQueryData<StallDetail>(stallKey);
      if (stall) {
        qc.setQueryData<StallDetail>(stallKey, {
          ...stall,
          dishes: stall.dishes.map((d) => (d.id === dishId ? { ...d, stats: created.dish_stats } : d)),
        });
      }
      const dish = qc.getQueryData<DishDetail>(dishKey);
      if (dish) qc.setQueryData<DishDetail>(dishKey, { ...dish, stats: created.dish_stats });
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: stallKey });
      qc.invalidateQueries({ queryKey: dishKey });
      qc.invalidateQueries({ queryKey: keys.rankings });
      qc.invalidateQueries({ queryKey: keys.myReviews });
    },
  });
}
