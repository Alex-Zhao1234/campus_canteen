import { api } from "./client";
import type { CanteenOccupancy, SeatMap } from "@/types/api";

export const seatsApi = {
  occupancy: () => api.get<CanteenOccupancy[]>("/seats/occupancy"),
  map: (canteenId: number, floor: number) =>
    api.get<SeatMap>(`/seats/map?canteen_id=${canteenId}&floor=${floor}`),
};
