import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useDish } from "@/hooks/queries";
import { CommentComposer } from "@/components/CommentComposer";
import { ReviewList } from "@/components/ReviewList";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ErrorState, Loading } from "@/components/State";
import { formatPrice, formatSpicy } from "@/lib/format";

/** 菜品配图：有图显示，加载失败或没图时显示占位 */
function DishPhoto({ src, alt }: { src: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div className="dish-photo placeholder" aria-label="暂无图片">
        🍽️
      </div>
    );
  }
  return <img className="dish-photo" src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}

export function Dish() {
  const id = Number(useParams().id);
  const { data, isLoading, error } = useDish(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;
  const s = data.stats;

  return (
    <>
      <header className="dish-head">
        <div className="dish-head-text">
          <h2 className="page-title">{data.name}</h2>
          <p className="subtitle">
            <Link to={`/stall/${data.stall.id}`}>{data.stall.name}</Link> · {data.stall.canteen_name} {data.stall.floor} 楼
          </p>
          <p className="meta">
            {formatPrice(data.price_cents)} · {formatSpicy(data.spicy_level)}
            {data.is_veg && " · 素"} · {data.dish_type}
            {data.portion_hint && ` · ${data.portion_hint}`}
          </p>
        </div>
        <DishPhoto src={data.image_url} alt={data.name} />
      </header>

      <section className="stats">
        <div>
          <ScoreBadge score={s.score_7d} count={s.review_count_7d} />
        </div>
        <dl>
          <dt>7 日好评率</dt>
          <dd>{s.review_count_7d ? `${Math.round(s.good_rate_7d * 100)}%` : "—"}</dd>
          <dt>7 日评价</dt>
          <dd>{s.review_count_7d}</dd>
          <dt>累计评价</dt>
          <dd>{s.review_count_all}</dd>
        </dl>
      </section>
      <section className="dish-rate">
        <h3 className="section-title">评论区</h3>
        <CommentComposer dishId={data.id} stallId={data.stall.id} dishName={data.name} />
        <ReviewList dishId={data.id} stallId={data.stall.id} />
      </section>
    </>
  );
}
