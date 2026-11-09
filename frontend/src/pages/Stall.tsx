import { Link, useParams } from "react-router-dom";
import { useStall } from "@/hooks/queries";
import { RatingQuickBar } from "@/components/RatingQuickBar";
import { ScoreBadge } from "@/components/ScoreBadge";
import { Empty, ErrorState, Loading } from "@/components/State";
import { formatPrice, formatSpicy } from "@/lib/format";

export function Stall() {
  const id = Number(useParams().id);
  const { data, isLoading, error } = useStall(id);
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  return (
    <>
      <h2 className="page-title">{data.name}</h2>
      <p className="subtitle">
        <Link to={`/canteen/${data.canteen_id}`}>← 所在食堂</Link> · {data.floor} 楼
        {data.cuisine_type && ` · ${data.cuisine_type}`}
      </p>
      {data.dishes.length === 0 && <Empty>这个窗口还没有菜品</Empty>}
      <ul className="cards">
        {data.dishes.map((d) => (
          <li key={d.id} className="dish-item">
            <Link to={`/dish/${d.id}`} className="card">
              <span className="card-main">
                <strong>{d.name}</strong>
                <small>
                  {formatPrice(d.price_cents)} · {formatSpicy(d.spicy_level)}
                  {d.is_veg && " · 素"}
                </small>
              </span>
              <span className="card-side">
                <ScoreBadge score={d.stats.score_7d} count={d.stats.review_count_7d} />
              </span>
            </Link>
            <RatingQuickBar dishId={d.id} stallId={data.id} dishName={d.name} />
          </li>
        ))}
      </ul>
    </>
  );
}
