import { Link, useParams } from "react-router-dom";
import { useCanteens, useStalls } from "@/hooks/queries";
import { ScoreBadge } from "@/components/ScoreBadge";
import { Empty, ErrorState, Loading } from "@/components/State";
import type { Stall } from "@/types/api";

function groupByFloor(stalls: Stall[]): [number, Stall[]][] {
  const map = new Map<number, Stall[]>();
  for (const s of stalls) map.set(s.floor, [...(map.get(s.floor) ?? []), s]);
  return [...map.entries()].sort((a, b) => a[0] - b[0]);
}

export function Canteen() {
  const id = Number(useParams().id);
  const canteens = useCanteens();
  const { data, isLoading, error } = useStalls(id);
  const canteen = canteens.data?.find((c) => c.id === id);

  return (
    <>
      <h2 className="page-title">{canteen?.name ?? "食堂"}</h2>
      {isLoading && <Loading />}
      {error && <ErrorState error={error} />}
      {data && data.length === 0 && <Empty>这个食堂还没有窗口数据</Empty>}
      {data &&
        groupByFloor(data).map(([floor, stalls]) => (
          <section key={floor}>
            <h3 className="section-title">{floor} 楼</h3>
            <ul className="cards">
              {stalls.map((s) => (
                <li key={s.id}>
                  <Link to={`/stall/${s.id}`} className="card">
                    <span className="card-main">
                      <strong>{s.name}</strong>
                      <small>{s.cuisine_type ?? "—"}</small>
                    </span>
                    <span className="card-side">
                      <ScoreBadge score={s.stats.score_7d} count={s.stats.review_count_24h} countLabel="24h" />
                      {s.stats.bad_count_24h >= 3 && <span className="flag">⚠️ 今日踩雷 {s.stats.bad_count_24h}</span>}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
    </>
  );
}
