import type { CSSProperties } from "react";

interface Props {
  score: number;
  count: number;
  /** 评价数的说明文字，如 "7 日" */
  countLabel?: string;
}

/** 7 日评分徽标：按正负着色；没有评价时显示"暂无评价"。 */
export function ScoreBadge({ score, count, countLabel = "7 日" }: Props) {
  if (count === 0) return <span className="badge badge-muted">暂无评价</span>;
  const tone = score >= 0.3 ? "good" : score <= -0.3 ? "bad" : "neutral";
  const label = tone === "good" ? "好评" : tone === "bad" ? "踩雷" : "一般";
  const style: CSSProperties = { "--tone": `var(--${tone})` } as CSSProperties;
  return (
    <span className={`badge badge-${tone}`} style={style} title={`${countLabel}评分 ${score.toFixed(2)}`}>
      {label} {score > 0 ? "+" : ""}
      {score.toFixed(2)}
      <small> · {count} 评</small>
    </span>
  );
}
