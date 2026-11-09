import { Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Canteens } from "@/pages/Canteens";
import { Canteen } from "@/pages/Canteen";
import { Stall } from "@/pages/Stall";
import { Dish } from "@/pages/Dish";
import { Me } from "@/pages/Me";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/canteens" element={<Canteens />} />
        <Route path="/canteen/:id" element={<Canteen />} />
        <Route path="/stall/:id" element={<Stall />} />
        <Route path="/dish/:id" element={<Dish />} />
        <Route path="/me" element={<Me />} />
      </Route>
    </Routes>
  );
}
