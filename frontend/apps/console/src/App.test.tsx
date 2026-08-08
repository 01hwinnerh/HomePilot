import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { consoleAuthClient, consoleAuthStore } from "./auth/store";

describe("Console App", () => {
  beforeEach(() => {
    consoleAuthStore.getState().clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("restores the console session when the application starts", async () => {
    const refresh = vi.spyOn(consoleAuthClient, "refresh").mockResolvedValue({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        id: 12,
        email: "owner@example.com",
        is_platform_admin: false,
        memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
      },
    });
    const me = vi.spyOn(consoleAuthClient, "me").mockResolvedValue({
      id: 12,
      email: "owner@example.com",
      is_platform_admin: false,
      memberships: [{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }],
    });

    render(<App />);

    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(me).toHaveBeenCalledWith("access-token");
    expect(await screen.findByText("榫卯之家")).toBeTruthy();
  });
});
