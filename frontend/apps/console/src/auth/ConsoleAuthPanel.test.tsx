import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConsoleAuthPanel } from "./ConsoleAuthPanel";
import { consoleAuthClient, consoleAuthStore } from "./store";

describe("ConsoleAuthPanel", () => {
  beforeEach(() => {
    consoleAuthStore.getState().clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows the merchant and role returned by the backend", () => {
    consoleAuthStore.getState().acceptAuth({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
      },
    });

    render(<ConsoleAuthPanel />);

    expect(screen.getByRole("heading", { name: "商家控制台" })).toBeTruthy();
    expect(screen.getByText("owner@example.com")).toBeTruthy();
    expect(screen.getByText("榫卯之家")).toBeTruthy();
    expect(screen.getByText("店主")).toBeTruthy();
    expect(document.body.textContent).not.toContain("access-token");
  });

  it("does not create a console entry for a customer without memberships", () => {
    consoleAuthStore.getState().acceptAuth({
      access_token: "customer-token",
      token_type: "bearer",
      user: {
        id: 13,
        email: "customer@example.com",
        is_platform_admin: false,
        memberships: [],
      },
    });

    render(<ConsoleAuthPanel />);

    expect(screen.getByText("当前没有控制台访问权限")).toBeTruthy();
    expect(screen.queryByText("榫卯之家")).toBeNull();
    expect(document.body.textContent).not.toContain("customer-token");
  });

  it("shows the platform administrator marker from the backend identity", () => {
    consoleAuthStore.getState().acceptAuth({
      access_token: "platform-token",
      token_type: "bearer",
      user: {
        id: 1,
        email: "admin@homepilot.dev",
        is_platform_admin: true,
        memberships: [],
      },
    });

    render(<ConsoleAuthPanel />);

    expect(screen.getByText("平台管理员")).toBeTruthy();
    expect(screen.getByText("admin@homepilot.dev")).toBeTruthy();
    expect(document.body.textContent).not.toContain("platform-token");
  });

  it("allows an anonymous user to sign in and then shows the returned identity", async () => {
    const login = vi.spyOn(consoleAuthClient, "login").mockResolvedValue({
      access_token: "merchant-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
      },
    });
    vi.spyOn(consoleAuthClient, "me").mockResolvedValue({
      id: 12,
      email: "owner@example.com",
      is_platform_admin: false,
      memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
    });
    consoleAuthStore.getState().clear();
    render(<ConsoleAuthPanel />);

    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "safe-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "登录控制台" }));

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({
        email: "owner@example.com",
        password: "safe-password",
      }),
    );
    expect(await screen.findByText("榫卯之家")).toBeTruthy();
    expect(document.body.textContent).not.toContain("merchant-token");
  });

  it("loads live memberships from /me after sign-in", async () => {
    const login = vi.spyOn(consoleAuthClient, "login").mockResolvedValue({
      access_token: "merchant-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [],
      },
    });
    const me = vi.spyOn(consoleAuthClient, "me").mockResolvedValue({
      id: 12,
      email: "owner@example.com",
      is_platform_admin: false,
      memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
    });
    consoleAuthStore.getState().clear();
    render(<ConsoleAuthPanel />);

    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "safe-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "登录控制台" }));

    await waitFor(() => expect(login).toHaveBeenCalledOnce());
    await waitFor(() => expect(me).toHaveBeenCalledWith("merchant-token"));
    expect(await screen.findByText("榫卯之家")).toBeTruthy();
  });

  it("revokes the session and returns to the console login after logout", async () => {
    const logout = vi.spyOn(consoleAuthClient, "logout").mockResolvedValue();
    consoleAuthStore.getState().acceptAuth(authenticatedResponse());
    render(<ConsoleAuthPanel />);

    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
    expect(await screen.findByRole("heading", { name: "登录控制台" })).toBeTruthy();
    expect(consoleAuthStore.getState()).toMatchObject({
      accessToken: null,
      status: "anonymous",
      user: null,
    });
  });

  it("clears the local identity when logout cannot reach the server", async () => {
    vi.spyOn(consoleAuthClient, "logout").mockRejectedValue(new Error("network unavailable"));
    consoleAuthStore.getState().acceptAuth(authenticatedResponse());
    render(<ConsoleAuthPanel />);

    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByRole("heading", { name: "登录控制台" })).toBeTruthy();
    expect(consoleAuthStore.getState()).toMatchObject({
      accessToken: null,
      status: "anonymous",
      user: null,
    });
  });
});

function authenticatedResponse() {
  return {
    access_token: "access-token",
    token_type: "bearer" as const,
    user: {
      id: 12,
      email: "owner@example.com",
      is_platform_admin: false,
      memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" as const }],
    },
  };
}
