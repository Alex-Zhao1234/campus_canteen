/** 界面本地状态：当前选中的食堂（null = 全部）。 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UiState {
  canteenId: number | null;
  setCanteenId: (id: number | null) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      canteenId: null,
      setCanteenId: (canteenId) => set({ canteenId }),
    }),
    { name: "cc-ui" },
  ),
);
