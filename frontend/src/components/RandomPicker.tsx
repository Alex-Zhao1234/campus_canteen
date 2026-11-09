import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useRandomPick } from "@/hooks/useRandomPick";
import { useCanteens } from "@/hooks/queries";
import { useUiStore } from "@/stores/ui";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ErrorState, Loading } from "@/components/State";
import { formatPrice, formatSpicy } from "@/lib/format";
import type { RecommendItem } from "@/types/api";

const BUDGETS: { label: string; value: number | null }[] = [
  { label: "不限", value: null },
  { label: "≤10 元", value: 1000 },
  { label: "≤15 元", value: 1500 },
  { label: "≤20 元", value: 2000 },
];
const SPICY: { label: string; value: number | null }[] = [
  { label: "不限", value: null },
  { label: "不辣", value: 0 },
  { label: "微辣", value: 1 },
];

function Card({ item, big, onPick }: { item: RecommendItem; big?: boolean; onPick: () => void }) {
  return (
    <Link to={`/dish/${item.dish_id}`} className={big ? "pick-card big" : "pick-card"} onClick={onPick}>
      <strong>{item.dish_name}</strong>
      <small>
        {item.canteen_name} · {item.stall_name}
      </small>
      <small>
        {formatPrice(item.price_cents)} · {formatSpicy(item.spicy_level)}
        {item.is_veg && " · 素"}
      </small>
      <ScoreBadge score={item.score_7d} count={item.review_count_7d} />
    </Link>
  );
}

export function RandomPicker() {
  const [open, setOpen] = useState(false);
  const ui = useUiStore();
  const canteens = useCanteens();
  const filters = { canteenId: ui.canteenId, budget: ui.budget, spicy: ui.spicy, veg: ui.veg };
  const pick = useRandomPick(filters, open);

  // 打开抽屉时锁住背景滚动
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button className="fab" onClick={() => setOpen(true)} aria-label="随机推荐">
        🎲 吃什么
      </button>

      {open && (
        <div className="sheet-backdrop" onClick={() => setOpen(false)}>
          <div className="sheet picker" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-head row">
              <strong>🎲 今天吃什么</strong>
              <button className="close" onClick={() => setOpen(false)} aria-label="关闭">
                ✕
              </button>
            </div>

            <div className="filters">
              <div className="chips">
                <button className={ui.canteenId === null ? "chip active" : "chip"} onClick={() => ui.setCanteenId(null)}>
                  全部食堂
                </button>
                {canteens.data?.map((c) => (
                  <button key={c.id} className={ui.canteenId === c.id ? "chip active" : "chip"} onClick={() => ui.setCanteenId(c.id)}>
                    {c.name}
                  </button>
                ))}
              </div>
              <div className="chips">
                {BUDGETS.map((b) => (
                  <button key={b.label} className={ui.budget === b.value ? "chip active" : "chip"} onClick={() => ui.setBudget(b.value)}>
                    {b.label}
                  </button>
                ))}
              </div>
              <div className="chips">
                {SPICY.map((s) => (
                  <button key={s.label} className={ui.spicy === s.value ? "chip active" : "chip"} onClick={() => ui.setSpicy(s.value)}>
                    {s.label}
                  </button>
                ))}
                <button className={ui.veg ? "chip active" : "chip"} onClick={() => ui.setVeg(!ui.veg)}>
                  🥬 只要素菜
                </button>
              </div>
            </div>

            <div className="pick-body">
              {pick.isPending && <Loading />}
              {pick.error && <ErrorState error={pick.error} />}
              {pick.data && !pick.data.pick && (
                <p className="state">没有符合条件的菜，放宽一下条件试试</p>
              )}
              {pick.data?.pick && (
                <>
                  <Card item={pick.data.pick} big onPick={() => setOpen(false)} />
                  {pick.data.alternates.length > 0 && (
                    <div className="alternates">
                      {pick.data.alternates.map((a) => (
                        <Card key={a.dish_id} item={a} onPick={() => setOpen(false)} />
                      ))}
                    </div>
                  )}
                </>
              )}
              {pick.exhausted && <p className="footnote">都看过一轮了，从头再来</p>}
            </div>

            <button className="primary block" onClick={pick.reroll} disabled={pick.isFetching || !pick.data?.pick}>
              {pick.isFetching ? "抽取中…" : "换一个"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
