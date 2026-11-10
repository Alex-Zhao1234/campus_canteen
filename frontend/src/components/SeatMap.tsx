/** 某层座位平面图：按 cols 列铺圆圈，空位绿、有人红。只在楼层行展开时挂载。 */
import { useSeatMap } from "@/hooks/queries";

export function SeatMap({ canteenId, floor }: { canteenId: number; floor: number }) {
  const { data, isLoading, error } = useSeatMap(canteenId, floor, true);

  if (isLoading) return <p className="seat-map-state">加载座位图…</p>;
  if (error && !data) return <p className="seat-map-state state-error">座位图暂时不可用</p>;
  if (!data) return null;
  if (!data.seats.length) return <p className="seat-map-state">这一层还没有座位数据</p>;

  return (
    <div className="seat-map" aria-label={`${floor}层座位平面图`}>
      <div className="seat-legend">
        <span>
          <i className="seat-dot-sm free" /> 空位 {data.total - data.occupied}
        </span>
        <span>
          <i className="seat-dot-sm busy" /> 有人 {data.occupied}
        </span>
      </div>
      <ul className="seat-grid" style={{ gridTemplateColumns: `repeat(${data.cols}, 1fr)` }}>
        {data.seats.map((s) => (
          <li
            key={s.code}
            className={`seat-circle ${s.is_occupied ? "busy" : "free"}`}
            title={`${s.code} ${s.is_occupied ? "有人" : "空位"}`}
          />
        ))}
      </ul>
    </div>
  );
}
