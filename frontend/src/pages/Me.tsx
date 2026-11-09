import { Link } from "react-router-dom";
import { useDeleteReview, useMyReviews } from "@/hooks/useMyReviews";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/stores/toast";
import { Empty, ErrorState, Loading } from "@/components/State";
import { formatTime } from "@/lib/format";
import type { Verdict } from "@/types/api";

const EMOJI: Record<Verdict, string> = { good: "😋", ok: "😐", bad: "🤢" };

export function Me() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const reviews = useMyReviews();
  const del = useDeleteReview();

  if (!user) {
    return (
      <div className="state">
        <p>登录后就能一键评价</p>
        <Link to="/login" className="primary inline">
          去登录
        </Link>
      </div>
    );
  }

  return (
    <>
      <h2 className="page-title">{user.nickname}</h2>
      <p className="subtitle">信任分 {user.trust_score.toFixed(1)}</p>

      <h3 className="section-title">我的评价</h3>
      {reviews.isLoading && <Loading />}
      {reviews.error && <ErrorState error={reviews.error} />}
      {reviews.data && reviews.data.length === 0 && (
        <Empty>
          还没有评价，<Link to="/">去首页看看</Link>
        </Empty>
      )}
      {reviews.data && reviews.data.length > 0 && (
        <ul className="cards">
          {reviews.data.map((r) => (
            <li key={r.id} className="card review">
              <span className={`review-emoji ${r.verdict}`} aria-label={r.verdict}>
                {EMOJI[r.verdict]}
              </span>
              <span className="card-main">
                <Link to={`/dish/${r.dish_id}`}>
                  <strong>{r.dish_name}</strong>
                </Link>
                <small>
                  {r.stall_name} · {formatTime(r.created_at)}
                </small>
                {r.tags.length > 0 && (
                  <span className="mini-tags">
                    {r.tags.map((t) => (
                      <span key={t.code}>{t.label}</span>
                    ))}
                  </span>
                )}
              </span>
              <button
                className="link-btn"
                disabled={del.isPending}
                onClick={() => {
                  if (!window.confirm(`删除对「${r.dish_name}」的评价？`)) return;
                  del.mutate(r, {
                    onSuccess: () => toast("已删除，分数会随之更新"),
                    onError: (e) => toast(e instanceof Error ? e.message : "删除失败", "bad"),
                  });
                }}
              >
                删除
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        className="ghost block"
        style={{ marginTop: "1.5rem" }}
        onClick={() => {
          logout();
          toast("已退出登录");
        }}
      >
        退出登录
      </button>
    </>
  );
}
