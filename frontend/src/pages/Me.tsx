import { useAuthStore } from "@/stores/auth";
import { Empty } from "@/components/State";

export function Me() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Empty>登录功能下一步上线，先去逛逛榜单吧</Empty>;
  return <p className="state">你好，{user.nickname}</p>;
}
