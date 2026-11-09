import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";

const tabs = [
  { to: "/", label: "首页", icon: "🏠" },
  { to: "/canteens", label: "食堂", icon: "🍽️" },
  { to: "/me", label: "我的", icon: "👤" },
];

export function Layout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isRoot = tabs.some((t) => t.to === pathname);
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
