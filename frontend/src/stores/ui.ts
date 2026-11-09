/** 界面本地状态：当前食堂（null = 全部）与随机推荐的约束。persist 到 localStorage。 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UiState {
  canteenId: number | null;
  setCanteenId: (id: number | null) => void;
  budget: number | null;
  spicy: number | null;
  veg: boolean;
  setBudget: (v: number | null) => void;
  setSpicy: (v: number | null) => void;
  setVeg: (v: boolean) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      canteenId: null,
      setCanteenId: (canteenId) => set({ canteenId }),
      budget: null,
      spicy: null,
      veg: false,
      setBudget: (budget) => set({ budget }),
      setSpicy: (spicy) => set({ spicy }),
      setVeg: (veg) => set({ veg }),
    }),
    { name: "cc-ui" },
  ),
);
