import { api } from "./client";
import type { MyReview, ReviewCreated, ReviewCreateIn, Tag } from "@/types/api";

export const reviewsApi = {
  tags: () => api.get<Tag[]>("/tags"),
  create: (body: ReviewCreateIn) => api.post<ReviewCreated>("/reviews", body),
  remove: (reviewId: number) => api.del<ReviewCreated>(`/reviews/${reviewId}`),
  mine: () => api.get<MyReview[]>("/me/reviews"),
};
