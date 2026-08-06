import { describe, expect, it, vi } from "vitest";

import type { AuthResponse } from "@homepilot/auth-client";

import { createAuthStore } from "./store";

describe("storefront auth store", () => {
  it("restores an authenticated session from the refresh response", async () => {
    const response: AuthResponse = {
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 7,
        email: "customer@example.com",
        is_platform_admin: false,
        memberships: [],
      },
    };
    const refresh = vi.fn().mockResolvedValue(response);
    const store = createAuthStore({ refresh });

    await store.getState().restoreSession();

    expect(refresh).toHaveBeenCalledOnce();
    expect(store.getState()).toMatchObject({
      accessToken: "access-token",
      status: "authenticated",
      user: response.user,
    });
  });

  it("falls back to anonymous when session restoration fails", async () => {
    const refresh = vi.fn().mockRejectedValue(new Error("network unavailable"));
    const store = createAuthStore({ refresh });

    await store.getState().restoreSession();

    expect(store.getState()).toMatchObject({
      accessToken: null,
      status: "anonymous",
      user: null,
    });
  });

  it("clears the in-memory authentication state", () => {
    const store = createAuthStore({ refresh: vi.fn() });
    const response = authenticatedResponse();

    store.getState().acceptAuth(response);
    store.getState().clear();

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
    const store = createAuthStore({ refresh });

    const firstRestore = store.getState().restoreSession();
    const secondRestore = store.getState().restoreSession();

    expect(refresh).toHaveBeenCalledOnce();

    resolveRefresh(authenticatedResponse());
    await Promise.all([firstRestore, secondRestore]);

    expect(store.getState().status).toBe("authenticated");
  });
});

function authenticatedResponse(): AuthResponse {
  return {
    access_token: "access-token",
    token_type: "bearer",
    user: {
      id: 7,
      email: "customer@example.com",
      is_platform_admin: false,
      memberships: [],
    },
  };
}
