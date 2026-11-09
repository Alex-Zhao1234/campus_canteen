/** 极简全局提示。push 后 2.5 秒自动消失。 */
import { create } from "zustand";

export type ToastTone = "info" | "good" | "bad";
interface Toast {
  id: number;
  msg: string;
  tone: ToastTone;
}
interface ToastState {
  toasts: Toast[];
  push: (msg: string, tone?: ToastTone) => void;
  remove: (id: number) => void;
}

let seq = 0;
export const useToastStore = create<ToastState>()((set) => ({
  toasts: [],
  push: (msg, tone = "info") => {
    const id = ++seq;
    set((s) => ({ toasts: [...s.toasts, { id, msg, tone }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 2500);
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = (msg: string, tone?: ToastTone) => useToastStore.getState().push(msg, tone);
