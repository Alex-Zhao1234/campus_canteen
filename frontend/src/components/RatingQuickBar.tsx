/**
 * 一键评价（架构文档 7.5 / 9.3）。
 *
 * 状态机：idle ──点表情──▶ tagging(3 秒倒计时，可选最多 3 个标签) ──超时/完成──▶ submitting ──▶ done
 *
 * 取舍：表情点击时界面立即高亮（乐观），但请求推迟到标签窗口结束后一次性发出，
 * 这样 review 表只收到一条干净的事件，不需要 PATCH 接口，也保住了 append-only。
 */
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { useTags } from "@/hooks/queries";
import { useSubmitReview } from "@/hooks/useSubmitReview";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/stores/toast";
import type { Verdict } from "@/types/api";

const VERDICTS: { value: Verdict; emoji: string; label: string }[] = [
  { value: "good", emoji: "😋", label: "好吃" },
  { value: "ok", emoji: "😐", label: "一般" },
  { value: "bad", emoji: "🤢", label: "踩雷" },
];
const TAG_WINDOW_MS = 3000;
const MAX_TAGS = 3;

type Phase = "idle" | "tagging" | "submitting" | "done";

interface Props {
  dishId: number;
  stallId: number;
  dishName: string;
}

export function RatingQuickBar({ dishId, stallId, dishName }: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [timerKey, setTimerKey] = useState(0); // 变化即重启倒计时
  const timer = useRef<number | undefined>(undefined);

  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const location = useLocation();
  const tagsQuery = useTags();
  const submit = useSubmitReview(stallId, dishId);

  // 倒计时：进入 tagging 或点选标签后重新计 3 秒
  useEffect(() => {
    if (phase !== "tagging") return;
    timer.current = window.setTimeout(() => finish(), TAG_WINDOW_MS);
    return () => window.clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, timerKey]);

  function pick(v: Verdict) {
    if (!token) {
      toast("评价需要先登录");
      navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    if (phase === "submitting" || phase === "done") return;
    setVerdict(v);
    setTags([]);
    setPhase("tagging");
    setTimerKey((k) => k + 1);
  }

  function toggleTag(code: string) {
    setTags((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : prev.length < MAX_TAGS ? [...prev, code] : prev,
    );
    setTimerKey((k) => k + 1);
  }

  function finish() {
    window.clearTimeout(timer.current);
    if (!verdict) return;
    setPhase("submitting");
    submit.mutate(
      { dish_id: dishId, verdict, tag_codes: tags },
      {
        onSuccess: (created) => {
          setPhase("done");
          toast(`已评价「${dishName}」，当前 7 日评分 ${created.dish_stats.score_7d.toFixed(2)}`, "good");
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409) {
            setPhase("done"); // 今天已评过：保持选中态，不让再点
            toast("今天已经评价过这道菜了", "info");
          } else if (err instanceof ApiError && err.status === 401) {
            setPhase("idle");
            setVerdict(null);
            navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
          } else {
            setPhase("idle");
            setVerdict(null);
            toast(err instanceof Error ? err.message : "提交失败，请重试", "bad");
          }
        },
      },
    );
  }

  function cancel() {
    window.clearTimeout(timer.current);
    setPhase("idle");
    setVerdict(null);
    setTags([]);
  }

  const locked = phase === "submitting" || phase === "done";

  return (
    <div className="quickbar">
      <div className="verdicts" role="group" aria-label={`评价 ${dishName}`}>
        {VERDICTS.map((v) => (
          <button
            key={v.value}
            className={`verdict ${verdict === v.value ? `picked ${v.value}` : ""} ${locked && verdict !== v.value ? "dim" : ""}`}
            disabled={locked}
            onClick={() => pick(v.value)}
            aria-pressed={verdict === v.value}
          >
            <span aria-hidden>{v.emoji}</span>
            {v.label}
          </button>
        ))}
        {phase === "done" && <span className="quickbar-done">已评</span>}
        {phase === "submitting" && <span className="quickbar-done">提交中…</span>}
      </div>

      {phase === "tagging" && (
        <div className="sheet-backdrop" onClick={finish}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-head">
              <strong>
                {VERDICTS.find((v) => v.value === verdict)?.emoji} {dishName}
              </strong>
              <small>补几个标签？不选也行（{tags.length}/{MAX_TAGS}）</small>
            </div>
            <div className="tags">
              {tagsQuery.data?.map((t) => (
                <button
                  key={t.code}
                  className={tags.includes(t.code) ? "tag on" : "tag"}
                  onClick={() => toggleTag(t.code)}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="sheet-actions">
              <button className="ghost" onClick={cancel}>
                取消
              </button>
              <button className="primary" onClick={finish}>
                完成
              </button>
            </div>
            <div className="progress" key={timerKey} style={{ animationDuration: `${TAG_WINDOW_MS}ms` }} />
          </div>
        </div>
      )}
    </div>
  );
}
