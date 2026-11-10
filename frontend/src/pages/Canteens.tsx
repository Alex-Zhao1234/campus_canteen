import { Link } from "react-router-dom";
import { useCanteens } from "@/hooks/queries";
import { Empty, ErrorState, Loading } from "@/components/State";
import { SeatOccupancy } from "@/components/SeatOccupancy";

export function Canteens() {
  const { data, isLoading, error } = useCanteens();
  if (isLoading) return <Loading />;
  if (error) return <ErrorState error={error} />;
  if (!data?.length) return <Empty>还没有食堂数据，请先导入种子数据</Empty>;
  return (
    <>
      <ul className="cards">
        {data.map((c) => (
          <li key={c.id}>
            <Link to={`/canteen/${c.id}`} className="card">
              <strong>{c.name}</strong>
              <small>{c.floors} 层</small>
            </Link>
          </li>
        ))}
      </ul>
      <SeatOccupancy />
    </>
  );
}
