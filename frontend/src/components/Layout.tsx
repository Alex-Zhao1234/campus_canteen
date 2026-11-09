import { Navigate, NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/Toaster";
import { useAuthStore } from "@/stores/auth";

const tabs = [
  { to: "/", label: "首页", icon: "🏠" },
  { to: "/canteens", label: "食堂", icon: "🍽️" },
  { to: "/me", label: "我的", icon: "👤" },
];

export function Layout() {
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const token = useAuthStore((s) => s.token);
  const isRoot = tabs.some((t) => t.to === pathname);

  // 进入产品即登录：未登录时一律先去登录页，登录后回到原本想看的页面
  if (!token && pathname !== "/login") {
    return <Navigate to={`/login?next=${encodeURIComponent(pathname + search)}`} replace />;
  }
  return (
    <div className="app">
      <header className="topbar">
        {!isRoot && (
          <button className="back" onClick={() => navigate(-1)} aria-label="返回">
            ‹
          </button>
        )}
        <h1 className="brand">食堂点评</h1>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <Toaster />
      <nav className="tabbar">
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end className={({ isActive }) => (isActive ? "tab active" : "tab")}>
            <span aria-hidden>{t.icon}</span>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
