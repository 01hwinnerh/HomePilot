import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { storefrontAuthClient, storefrontAuthStore } from "./auth/store";

describe("Storefront App", () => {
  beforeEach(() => {
    storefrontAuthStore.getState().clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("restores the session when the application starts", async () => {
    const refresh = vi.spyOn(storefrontAuthClient, "refresh").mockResolvedValue({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 7,
        email: "customer@example.com",
        is_platform_admin: false,
        memberships: [],
      },
    });

    render(<App />);

    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(await screen.findByText("customer@example.com")).toBeTruthy();
  });
});
