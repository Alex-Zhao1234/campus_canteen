import type { ReactNode } from "react";

export function Loading() {
  return <p className="state">加载中…</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="state">{children}</p>;
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : "请求失败";
  return <p className="state state-error">出错了：{msg}</p>;
}
