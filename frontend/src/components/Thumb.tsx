import { useState } from "react";

/** 列表用小缩略图：没图或加载失败显示占位 */
export function Thumb({ src, alt }: { src: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <span className="thumb placeholder" aria-hidden>
        🍽️
      </span>
    );
  }
  return <img className="thumb" src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />;
}
