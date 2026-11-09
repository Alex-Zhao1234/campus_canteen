import { Link } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/stores/toast";

export function Me() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  if (!user) {
    return (
      <div className="state">
        <p>登录后就能一键评价</p>
        <Link to="/login" className="primary block" style={{ display: "inline-block", width: "auto" }}>
          去登录
        </Link>
      </div>
    );
  }
  return (
    <>
      <h2 className="page-title">{user.nickname}</h2>
      <p className="subtitle">信任分 {user.trust_score.toFixed(1)}</p>
      {/* 第三步：我的评价列表 */}
      <button
        className="ghost block"
        onClick={() => {
          logout();
          toast("已退出登录");
        }}
      >
        退出登录
      </button>
    </>
  );
}
