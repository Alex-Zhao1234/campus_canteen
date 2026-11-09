import { api } from "./client";
import type { DishReviewPage, MyReview, ReviewCreated, ReviewCreateIn, Tag } from "@/types/api";

export const reviewsApi = {
  tags: () => api.get<Tag[]>("/tags"),
  create: (body: ReviewCreateIn) => api.post<ReviewCreated>("/reviews", body),
  remove: (reviewId: number) => api.del<ReviewCreated>(`/reviews/${reviewId}`),
  mine: () => api.get<MyReview[]>("/me/reviews"),
  forDish: (dishId: number, beforeId: number | null, limit = 20) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (beforeId) qs.set("before_id", String(beforeId));
    return api.get<DishReviewPage>(`/dishes/${dishId}/reviews?${qs}`);
  },
};
