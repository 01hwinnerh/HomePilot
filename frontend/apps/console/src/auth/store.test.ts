import { describe, expect, it, vi } from "vitest";

import type { AuthResponse } from "@homepilot/auth-client";

import { createConsoleAuthStore } from "./store";

describe("console auth store", () => {
  it("restores an authenticated session from the refresh response", async () => {
    const response: AuthResponse = {
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
      },
    };
    const refresh = vi.fn().mockResolvedValue(response);
    const me = vi.fn().mockResolvedValue(response.user);
    const store = createConsoleAuthStore({ refresh, me });

    await store.getState().restoreSession();

    expect(refresh).toHaveBeenCalledOnce();
    expect(me).toHaveBeenCalledWith("access-token");
    expect(store.getState()).toMatchObject({
      accessToken: "access-token",
      status: "authenticated",
      user: response.user,
    });
  });

  it("falls back to anonymous when session restoration fails", async () => {
    const refresh = vi.fn().mockRejectedValue(new Error("network unavailable"));
    const me = vi.fn();
    const store = createConsoleAuthStore({ refresh, me });

    await store.getState().restoreSession();

    expect(store.getState()).toMatchObject({
      accessToken: null,
      status: "anonymous",
      user: null,
    });
  });

  it("shares one refresh request across concurrent session restorations", async () => {
    let resolveRefresh!: (response: AuthResponse) => void;
    const refresh = vi.fn(
      () =>
        new Promise<AuthResponse>((resolve) => {
          resolveRefresh = resolve;
        }),
    );
    const me = vi.fn().mockResolvedValue({
      id: 12,
      email: "owner@example.com",
      is_platform_admin: false,
      memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" as const }],
    });
    const store = createConsoleAuthStore({ refresh, me });

    const firstRestore = store.getState().restoreSession();
    const secondRestore = store.getState().restoreSession();

    expect(refresh).toHaveBeenCalledOnce();
    resolveRefresh({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
      },
    });
    await Promise.all([firstRestore, secondRestore]);

    expect(store.getState().status).toBe("authenticated");
  });
});
