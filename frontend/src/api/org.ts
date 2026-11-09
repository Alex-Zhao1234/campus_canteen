import { api } from "./client";
import type { Canteen, DishDetail, Stall, StallDetail } from "@/types/api";

export const orgApi = {
  canteens: () => api.get<Canteen[]>("/canteens"),
  stalls: (canteenId: number) => api.get<Stall[]>(`/canteens/${canteenId}/stalls`),
  stall: (stallId: number) => api.get<StallDetail>(`/stalls/${stallId}`),
  dish: (dishId: number) => api.get<DishDetail>(`/dishes/${dishId}`),
};
