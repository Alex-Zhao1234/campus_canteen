import { Link, useParams } from "react-router-dom";
import { useDish } from "@/hooks/queries";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ErrorState, Loading } from "@/components/State";
import { formatPrice, formatSpicy } from "@/lib/format";

export function Dish() {
  const id = Number(useParams().id);
  const { data, isLoading, error } = useDish(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;
  const s = data.stats;

  return (
    <>
      <h2 className="page-title">{data.name}</h2>
      <p className="subtitle">
        <Link to={`/stall/${data.stall.id}`}>{data.stall.name}</Link> · {data.stall.canteen_name} {data.stall.floor} 楼
      </p>
      <p className="meta">
        {formatPrice(data.price_cents)} · {formatSpicy(data.spicy_level)}
        {data.is_veg && " · 素"} · {data.dish_type}
        {data.portion_hint && ` · ${data.portion_hint}`}
      </p>

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
      {/* 第二步：一键评价；第三步之后：评价流 */}
    </>
  );
}
