/** 食堂空位区块：每食堂一张卡，每层一行「N层 ● 拥挤度  剩 x / y」+ 进度条。5 秒轮询。 */
import { useEffect, useState } from "react";
import { useSeatOccupancy } from "@/hooks/queries";
import type { CanteenOccupancy, FloorOccupancy, SeatLevel } from "@/types/api";

const LEVEL_LABEL: Record<SeatLevel, string> = {
  unknown: "暂无数据",
  empty: "空闲",
  low: "较少",
  medium: "适中",
  high: "较多",
  full: "爆满",
};

function latestUpdate(c: CanteenOccupancy): number | null {
  const ts = c.levels
    .map((l) => l.updated_at)
    .filter((t): t is string => t !== null)
    .map((t) => Date.parse(t.endsWith("Z") ? t : t + "Z"));
  return ts.length ? Math.max(...ts) : null;
}

function agoText(ms: number | null, now: number): string {
  if (ms === null) return "暂无数据";
  const sec = Math.max(0, Math.round((now - ms) / 1000));
  if (sec < 60) return `${sec} 秒前更新`;
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前更新`;
  return "超过 1 小时未更新";
}

function FloorRow({ f }: { f: FloorOccupancy }) {
  const pct = Math.round(f.ratio * 100);
  return (
    <li className={`seat-floor level-${f.level}`}>
      <span className="seat-floor-name">{f.floor}层</span>
      <span className="seat-dot" aria-hidden />
      <span className="seat-level">{LEVEL_LABEL[f.level]}</span>
      <span className="seat-free">{f.level === "unknown" ? "—" : `剩 ${f.free} / ${f.total}`}</span>
      <span
        className="seat-bar"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span style={{ width: `${pct}%` }} />
      </span>
    </li>
  );
}

export function SeatOccupancy() {
  const { data, isLoading, error } = useSeatOccupancy();
  // 每秒重算「x 秒前更新」文案
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (isLoading) return <p className="state">加载空位中…</p>;
  // 后台刷新失败时保留上一次数据继续显示（头部"x 秒前更新"会自然变旧），只有从未拿到数据才报错
  if (error && !data) return <p className="state state-error">空位数据暂时不可用</p>;
  if (!data?.length) return null;

  return (
    <section>
      <h2 className="section-title">食堂空位</h2>
      <ul className="cards">
        {data.map((c) => (
          <li key={c.canteen_id} className="seat-card">
            <div className="seat-card-head">
              <strong>
                {c.canteen_name} <small>{c.floors}层</small>
              </strong>
              <small>{agoText(latestUpdate(c), now)}</small>
            </div>
            <ul className="seat-floors">
              {c.levels.map((f) => (
                <FloorRow key={f.floor} f={f} />
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
