import { Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";

function Home() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: () => api.get<{ status: string }>("/health") });
  return (
    <main style={{ padding: "2rem", textAlign: "center" }}>
      <h1>校园食堂点评推荐</h1>
      <p>后端状态：{data?.status ?? "连接中…"}</p>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      {/* 后续：/canteen/:id  /stall/:id  /dish/:id  /search  /me */}
    </Routes>
  );
}
