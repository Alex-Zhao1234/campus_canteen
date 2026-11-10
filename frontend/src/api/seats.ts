import { api } from "./client";
import type { CanteenOccupancy } from "@/types/api";

export const seatsApi = {
  occupancy: () => api.get<CanteenOccupancy[]>("/seats/occupancy"),
};
