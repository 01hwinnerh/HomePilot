import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthApiError } from "@homepilot/auth-client";

import { StorefrontAuthPanel } from "./StorefrontAuthPanel";
import { storefrontAuthClient, storefrontAuthStore } from "./store";

describe("StorefrontAuthPanel", () => {
  beforeEach(() => {
    storefrontAuthStore.getState().clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows login mode and can switch to registration for anonymous users", () => {
    render(<StorefrontAuthPanel />);

    expect(screen.getByRole("heading", { name: "欢迎回家" })).toBeTruthy();
    expect(screen.getByLabelText("邮箱")).toBeTruthy();
    expect(screen.getByLabelText("密码")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "注册" }));

    expect(screen.getByRole("heading", { name: "创建你的 HomePilot 账户" })).toBeTruthy();
  });

  it("registers a customer and shows the returned email", async () => {
    const register = vi.spyOn(storefrontAuthClient, "register").mockResolvedValue(
      authenticatedResponse(),
    );
    render(<StorefrontAuthPanel />);

    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "customer@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "safe-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建账户" }));

    await waitFor(() => expect(register).toHaveBeenCalledWith({
      email: "customer@example.com",
      password: "safe-password",
    }));
    expect(await screen.findByText("customer@example.com")).toBeTruthy();
  });

  it("shows a safe authentication error when login fails", async () => {
    const login = vi
      .spyOn(storefrontAuthClient, "login")
      .mockRejectedValue(new AuthApiError(401, "Invalid credentials"));
    render(<StorefrontAuthPanel />);

    fireEvent.change(screen.getByLabelText("邮箱"), {
      target: { value: "customer@example.com" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "登录 HomePilot" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Invalid credentials");
    expect(login).toHaveBeenCalledOnce();
    expect(document.body.textContent).not.toContain("access-token");
  });

  it("revokes the browser session and returns to login after logout", async () => {
    const logout = vi.spyOn(storefrontAuthClient, "logout").mockResolvedValue();
    storefrontAuthStore.getState().acceptAuth(authenticatedResponse());
    render(<StorefrontAuthPanel />);

    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
    expect(await screen.findByRole("heading", { name: "欢迎回家" })).toBeTruthy();
    expect(storefrontAuthStore.getState()).toMatchObject({
      accessToken: null,
      status: "anonymous",
      user: null,
    });
  });

  it("clears local authentication even when logout cannot reach the server", async () => {
    vi.spyOn(storefrontAuthClient, "logout").mockRejectedValue(new Error("network unavailable"));
    storefrontAuthStore.getState().acceptAuth(authenticatedResponse());
    render(<StorefrontAuthPanel />);

    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByRole("heading", { name: "欢迎回家" })).toBeTruthy();
    expect(storefrontAuthStore.getState()).toMatchObject({
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
      id: 7,
      email: "customer@example.com",
      is_platform_admin: false,
      memberships: [],
    },
  };
}
