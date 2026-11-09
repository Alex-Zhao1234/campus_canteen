/** 统一响应壳：{ code, data, msg }，与后端 app/schemas/common.py 对应。 */
import { useAuthStore } from "@/stores/auth";

type Envelope<T> = { code: number; data: T; msg: string };

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: number,
    msg: string,
  ) {
    super(msg);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(BASE + path, { ...init, headers: { ...headers, ...(init?.headers ?? {}) } });

  // 后端把所有错误都包成响应壳；解析失败则退回 HTTP 状态
  let body: Envelope<T> | null = null;
  try {
    body = (await res.json()) as Envelope<T>;
  } catch {
    body = null;
  }

  if (res.status === 401) useAuthStore.getState().logout();
  if (!res.ok || !body || body.code !== 0) {
    throw new ApiError(res.status, body?.code ?? res.status, body?.msg ?? `HTTP ${res.status}`);
  }
  return body.data;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
