import { api } from "./client";
import type { AccessTokenOut, SendCodeOut, TokenPair } from "@/types/api";

export const authApi = {
  sendCode: (email: string) => api.post<SendCodeOut>("/auth/send-code", { email }),
  verify: (email: string, code?: string) => api.post<TokenPair>("/auth/verify", { email, code }),
  refresh: (refresh_token: string) => api.post<AccessTokenOut>("/auth/refresh", { refresh_token }),
};
