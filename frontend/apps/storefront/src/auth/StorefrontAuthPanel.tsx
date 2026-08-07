import { useState, type FormEvent } from "react";

import { AuthApiError } from "@homepilot/auth-client";

import { storefrontAuthClient, storefrontAuthStore } from "./store";

type AuthMode = "login" | "register";

export function StorefrontAuthPanel() {
  const status = storefrontAuthStore((state) => state.status);
  const user = storefrontAuthStore((state) => state.user);
  const acceptAuth = storefrontAuthStore((state) => state.acceptAuth);
  const clear = storefrontAuthStore((state) => state.clear);
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);

    try {
      await storefrontAuthClient.logout();
    } catch {
      // The browser must not retain an authenticated UI after a logout attempt.
    } finally {
      clear();
      setLoggingOut(false);
    }
  };

  if (status === "loading") {
    return (
      <section className="auth-panel auth-panel-loading" aria-label="正在恢复会话">
        正在恢复你的 HomePilot 会话…
      </section>
    );
  }

  if (status === "authenticated") {
    return (
      <section className="auth-panel auth-panel-authenticated" aria-label="已登录">
        <p>你已登录 HomePilot。</p>
        <p>{user?.email}</p>
        <button disabled={loggingOut} type="button" onClick={() => void handleLogout()}>
          {loggingOut ? "正在退出…" : "退出登录"}
        </button>
      </section>
    );
  }

  const isRegister = mode === "register";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = isRegister
        ? await storefrontAuthClient.register({ email, password })
        : await storefrontAuthClient.login({ email, password });
      acceptAuth(response);
    } catch (cause) {
      setError(cause instanceof AuthApiError ? cause.detail : "暂时无法完成请求，请稍后再试。");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-panel" aria-labelledby="auth-heading">
      <p className="auth-kicker">HomePilot / private living</p>
      <h1 id="auth-heading">{isRegister ? "创建你的 HomePilot 账户" : "欢迎回家"}</h1>
      <p className="auth-intro">
        {isRegister
          ? "保存你的家居灵感，随时继续探索。"
          : "从一件真正适合你的家居开始。"}
      </p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="auth-email">邮箱</label>
        <input
          id="auth-email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="auth-password">密码</label>
        <input
          id="auth-password"
          name="password"
          type="password"
          autoComplete={isRegister ? "new-password" : "current-password"}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error !== null && <p role="alert">{error}</p>}
        <button disabled={submitting} type="submit">
          {submitting ? "处理中…" : isRegister ? "创建账户" : "登录 HomePilot"}
        </button>
      </form>

      <button
        className="auth-mode-toggle"
        type="button"
        onClick={() => setMode(isRegister ? "login" : "register")}
      >
        {isRegister ? "登录" : "注册"}
      </button>
    </section>
  );
}
