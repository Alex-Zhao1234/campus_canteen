import { useState } from "react";
import { Link } from "react-router-dom";
import { useCanteens, useRanking } from "@/hooks/queries";
import { useUiStore } from "@/stores/ui";
import { ScoreBadge } from "@/components/ScoreBadge";
import { Empty, ErrorState, Loading } from "@/components/State";
import { formatPrice, formatTime } from "@/lib/format";
import type { RankingType } from "@/types/api";

function Delta({ value }: { value: number | null }) {
  if (value === null) return <span className="delta new">新</span>;
  if (value === 0) return <span className="delta flat">–</span>;
  return <span className={value > 0 ? "delta up" : "delta down"}>{value > 0 ? `↑${value}` : `↓${-value}`}</span>;
}

export function Home() {
  const [type, setType] = useState<RankingType>("good");
  const canteenId = useUiStore((s) => s.canteenId);
  const setCanteenId = useUiStore((s) => s.setCanteenId);
  const canteens = useCanteens();
  const ranking = useRanking(type, canteenId);

  return (
    <>
      <section className="chips">
        <button className={canteenId === null ? "chip active" : "chip"} onClick={() => setCanteenId(null)}>
          全部食堂
        </button>
        {canteens.data?.map((c) => (
          <button
            key={c.id}
            className={canteenId === c.id ? "chip active" : "chip"}
            onClick={() => setCanteenId(c.id)}
          >
            {c.name}
          </button>
        ))}
      </section>

      <section className="segmented">
        <button className={type === "good" ? "active" : ""} onClick={() => setType("good")}>
          😋 好评榜
        </button>
        <button className={type === "bad" ? "active bad" : ""} onClick={() => setType("bad")}>
          🤢 踩雷榜
        </button>
      </section>

      {ranking.isLoading && <Loading />}
      {ranking.error && <ErrorState error={ranking.error} />}
      {ranking.data && ranking.data.items.length === 0 && (
        <Empty>{type === "good" ? "还没有上榜的菜，去评价第一道吧" : "暂无踩雷，放心吃"}</Empty>
      )}
      {ranking.data && ranking.data.items.length > 0 && (
        <ol className="ranking">
          {ranking.data.items.map((it) => (
            <li key={it.dish_id}>
              <Link to={`/dish/${it.dish_id}`} className="rank-row">
                <span className={`rank-no ${it.rank <= 3 ? "top" : ""}`}>{it.rank}</span>
                <span className="rank-main">
                  <strong>{it.dish_name}</strong>
                  <small>
                    {it.canteen_name} · {it.stall_name} · {formatPrice(it.price_cents)}
                  </small>
                </span>
                <span className="rank-side">
                  <ScoreBadge score={it.score} count={it.review_count_7d} />
                  <Delta value={it.delta} />
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}
      {ranking.data?.generated_at && (
        <p className="footnote">榜单更新于 {formatTime(ranking.data.generated_at)}，每 10 分钟重算</p>
      )}
    </>
  );
}
