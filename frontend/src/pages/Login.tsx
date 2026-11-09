import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/stores/toast";

/** 演示环境固定账号：登录页预填，直接回车即可进入 */
const DEMO_EMAIL = "you@zxx.edu.cn";

export function Login() {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [step, setStep] = useState<"email" | "code">("email");
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/me";

  const verify = useMutation({
    mutationFn: (c?: string) => authApi.verify(email.trim(), c),
    onSuccess: (r) => {
      login(r.access_token, r.refresh_token, r.user);
      toast(`欢迎，${r.user.nickname}`, "good");
      navigate(next, { replace: true });
    },
    onError: (e) => toast(e instanceof Error ? e.message : "验证失败", "bad"),
  });

  const send = useMutation({
    mutationFn: () => authApi.sendCode(email.trim()),
    onSuccess: (r) => {
      if (!r.code_required) {
        verify.mutate(undefined); // 邮件服务关闭：按一次回车直接登录
        return;
      }
      setStep("code");
      setDevCode(r.dev_code);
      if (r.dev_code) setCode(r.dev_code); // 开发模式：后端回显验证码，自动填入
      else toast("验证码已发送到邮箱", "good");
    },
    onError: (e) => toast(e instanceof Error ? e.message : "发送失败", "bad"),
  });

  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        step === "email" ? send.mutate() : verify.mutate(code.trim());
      }}
    >
      <h2 className="page-title">校园邮箱登录</h2>
      <p className="subtitle">只接受学校邮箱，只保存邮箱哈希，不保存明文。</p>

      <label>
        邮箱
        <input
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@xxx.edu.cn"
          value={email}
          disabled={step === "code"}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <small className="hint muted">固定演示账号，{DEMO_EMAIL}</small>
      </label>

      {step === "code" && (
        <label>
          验证码
          <input
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          {devCode && <small className="hint">开发模式：验证码 {devCode} 已自动填入</small>}
        </label>
      )}

      <button className="primary block" type="submit" disabled={send.isPending || verify.isPending}>
        {send.isPending || verify.isPending ? "登录中…" : step === "email" ? "登录" : "确认验证码"}
      </button>
      {step === "code" && (
        <button type="button" className="ghost block" onClick={() => setStep("email")}>
          换个邮箱
        </button>
      )}
    </form>
  );
}
