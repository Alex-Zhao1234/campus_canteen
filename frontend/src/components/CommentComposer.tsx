/**
 * 菜品页评论区的输入框：文字（可选，限 100 字）+ 下面一小行三档态度（必选）+ 发布。
 *
 * 写入仍走 POST /reviews，和窗口页的一键评价是同一种事件，所以"单人单菜单日一评"同样适用。
 */
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { useSubmitReview } from "@/hooks/useSubmitReview";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/stores/toast";
import type { Verdict } from "@/types/api";

export const VERDICT_OPTIONS: { value: Verdict; emoji: string; label: string }[] = [
  { value: "good", emoji: "😋", label: "喜欢" },
  { value: "ok", emoji: "😐", label: "一般" },
  { value: "bad", emoji: "🤢", label: "不喜欢" },
];
const MAX_LEN = 100;

interface Props {
  dishId: number;
  stallId: number;
  dishName: string;
}

export function CommentComposer({ dishId, stallId, dishName }: Props) {
  const [text, setText] = useState("");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const location = useLocation();
  const submit = useSubmitReview(stallId, dishId);

  function requireLogin(): boolean {
    if (token) return true;
    toast("评论需要先登录");
    navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
    return false;
  }

  function publish() {
    if (!requireLogin() || !verdict || submit.isPending) return;
    const comment = text.trim();
    submit.mutate(
      { dish_id: dishId, verdict, comment: comment || null },
      {
        onSuccess: () => {
          setText("");
          setVerdict(null);
          toast(`已发布对「${dishName}」的评论`, "good");
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409) toast("今天已经评价过这道菜了", "info");
          else if (err instanceof ApiError && err.status === 401)
            navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
          else toast(err instanceof Error ? err.message : "发布失败，请重试", "bad");
        },
      },
    );
  }

  return (
    <div className="composer">
      <textarea
        className="composer-input"
        placeholder={`说说「${dishName}」怎么样…`}
        value={text}
        maxLength={MAX_LEN}
        rows={3}
        onFocus={() => requireLogin()}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="composer-row">
        <div className="verdict-row" role="radiogroup" aria-label="你的态度">
          {VERDICT_OPTIONS.map((v) => (
            <button
              key={v.value}
              type="button"
              role="radio"
              aria-checked={verdict === v.value}
              className={`verdict small ${verdict === v.value ? `picked ${v.value}` : ""}`}
              onClick={() => setVerdict(v.value)}
            >
              <span aria-hidden>{v.emoji}</span>
              {v.label}
            </button>
          ))}
        </div>
        <span className="composer-count">
          {text.length}/{MAX_LEN}
        </span>
        <button className="primary small" disabled={!verdict || submit.isPending} onClick={publish}>
          {submit.isPending ? "发布中…" : "发布"}
        </button>
      </div>
    </div>
  );
}
