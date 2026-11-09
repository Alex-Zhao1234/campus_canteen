/** 菜品页评论区列表：全部未隐藏评价，没写字的显示"用户未给出评价"，只看态度。 */
import { useDishReviews } from "@/hooks/queries";
import { useDeleteReview } from "@/hooks/useMyReviews";
import { toast } from "@/stores/toast";
import { Empty, ErrorState, Loading } from "@/components/State";
import { VERDICT_OPTIONS } from "@/components/CommentComposer";
import { formatTime } from "@/lib/format";
import type { DishReview, Verdict } from "@/types/api";

const BY_VERDICT = Object.fromEntries(VERDICT_OPTIONS.map((v) => [v.value, v])) as Record<
  Verdict,
  (typeof VERDICT_OPTIONS)[number]
>;

interface Props {
  dishId: number;
  stallId: number;
}

export function ReviewList({ dishId, stallId }: Props) {
  const q = useDishReviews(dishId);
  const del = useDeleteReview();

  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const items: DishReview[] = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (items.length === 0) return <Empty>还没有人评论，来当第一个</Empty>;

  function remove(r: DishReview) {
    if (!window.confirm("删除这条评论？")) return;
    del.mutate(
      { id: r.id, dish_id: dishId, stall_id: stallId },
      {
        onSuccess: () => toast("已删除，分数会随之更新"),
        onError: (e) => toast(e instanceof Error ? e.message : "删除失败", "bad"),
      },
    );
  }

  return (
    <>
      <ul className="comments">
        {items.map((r) => {
          const v = BY_VERDICT[r.verdict];
          return (
            <li key={r.id} className="comment">
              <div className="comment-head">
                <strong>{r.user_nickname}</strong>
                <span className={`verdict-mark ${r.verdict}`}>
                  <span aria-hidden>{v.emoji}</span> {v.label}
                </span>
                <small>{formatTime(r.created_at)}</small>
                {r.is_mine && (
                  <button className="link-btn" disabled={del.isPending} onClick={() => remove(r)}>
                    删除
                  </button>
                )}
              </div>
              {r.comment ? (
                <p className="comment-text">{r.comment}</p>
              ) : (
                <p className="comment-text muted">用户未给出评价</p>
              )}
              {r.tags.length > 0 && (
                <span className="mini-tags">
                  {r.tags.map((t) => (
                    <span key={t.code}>{t.label}</span>
                  ))}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      {q.hasNextPage && (
        <button className="ghost block" disabled={q.isFetchingNextPage} onClick={() => q.fetchNextPage()}>
          {q.isFetchingNextPage ? "加载中…" : "加载更多"}
        </button>
      )}
    </>
  );
}
