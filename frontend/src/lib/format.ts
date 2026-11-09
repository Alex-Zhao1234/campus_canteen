export function formatPrice(cents: number): string {
  const yuan = cents / 100;
  return `¥${Number.isInteger(yuan) ? yuan : yuan.toFixed(1)}`;
}

export function formatSpicy(level: number): string {
  return level > 0 ? "🌶".repeat(level) : "不辣";
}

export function formatTime(iso: string): string {
  // 后端存 UTC naive，补 Z 后按本地时区显示
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
