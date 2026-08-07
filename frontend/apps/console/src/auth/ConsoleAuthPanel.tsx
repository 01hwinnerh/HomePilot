import { useState, type FormEvent } from "react";

import { AuthApiError } from "@homepilot/auth-client";

import { consoleAuthClient, consoleAuthStore } from "./store";

const roleLabels = {
  OWNER: "店主",
  STAFF: "员工",
} as const;

export function ConsoleAuthPanel() {
  const status = consoleAuthStore((state) => state.status);
  const user = consoleAuthStore((state) => state.user);
  const acceptAuth = consoleAuthStore((state) => state.acceptAuth);
  const clear = consoleAuthStore((state) => state.clear);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await consoleAuthClient.logout();
    } catch {
      // Clear local identity even if the server cannot be reached.
    } finally {
      clear();
      setLoggingOut(false);
    }
  };

  if (status === "loading") {
    return (
      <main className="console-auth-shell" aria-label="正在恢复控制台会话">
        <p className="console-loading">正在恢复控制台会话…</p>
      </main>
    );
  }

  if (status !== "authenticated" || user === null) {
    return (
      <main className="console-auth-shell">
        <aside className="console-rail" aria-label="HomePilot 控制台介绍">
          <p className="console-mark">HomePilot / console</p>
          <p className="console-rail-index">01 / quiet operations</p>
          <p className="console-rail-copy">让每一家独立家居品牌，都能从容经营自己的空间。</p>
        </aside>
        <section className="console-auth-card" aria-labelledby="console-auth-heading">
          <p className="console-kicker">身份验证 / private workspace</p>
          <h1 id="console-auth-heading">登录控制台</h1>
          <p className="console-intro">查看你的店铺、商品与售后工作。</p>
        <form
          onSubmit={async (event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            setError(null);
            setSubmitting(true);

            try {
              acceptAuth(await consoleAuthClient.login({ email, password }));
            } catch (cause) {
              setError(cause instanceof AuthApiError ? cause.detail : "暂时无法完成登录，请稍后再试。");
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <label htmlFor="console-email">邮箱</label>
          <input
            id="console-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <label htmlFor="console-password">密码</label>
          <input
            id="console-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error !== null && <p role="alert">{error}</p>}
          <button disabled={submitting} type="submit">
            {submitting ? "处理中…" : "登录控制台"}
          </button>
        </form>
        </section>
      </main>
    );
  }

  return (
    <main className="console-workspace" aria-labelledby="console-heading">
      <header className="console-header">
        <div>
          <p className="console-mark">HomePilot / console</p>
          <p className="console-header-caption">运营工作台 / 01</p>
        </div>
        <button disabled={loggingOut} type="button" onClick={() => void handleLogout()}>
          {loggingOut ? "正在退出…" : "退出登录"}
        </button>
      </header>
      <section className="console-identity-card">
        <p className="console-kicker">当前身份 / verified identity</p>
        <h1 id="console-heading">商家控制台</h1>
        <p className="console-email">{user.email}</p>
        {user.is_platform_admin && <p className="console-role console-role-platform">平台管理员</p>}
        {user.memberships.length === 0 && !user.is_platform_admin ? (
          <p className="console-no-access">当前没有控制台访问权限</p>
        ) : (
          <div className="console-memberships">
            {user.memberships.map((membership) => (
              <article key={membership.merchant_id} className="console-membership">
                <p className="console-membership-label">已授权店铺</p>
                <h2>{membership.merchant_name}</h2>
                <p className="console-role">{roleLabels[membership.role]}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
