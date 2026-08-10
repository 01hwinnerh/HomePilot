import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogWorkspace } from "./CatalogWorkspace";

describe("CatalogWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads the selected merchant catalog and exposes SKU management", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/stores")) return new Response(JSON.stringify([{ id: 3, merchant_id: 4, name: "榫卯店", slug: "joinery", is_active: true }]), { status: 200 });
      return new Response(JSON.stringify([{ id: 8, merchant_id: 4, store_id: 3, category_id: 1, name: "胡桃木边几", description: "", status: "DRAFT" }]), { status: 200 });
    });

    render(<CatalogWorkspace token="memory-token" memberships={[{ merchant_id: 4, merchant_name: "榫卯之家", role: "OWNER" }]} />);

    expect(await screen.findByText("胡桃木边几")).toBeTruthy();
    expect(screen.getByRole("button", { name: "管理 SKU" })).toBeTruthy();
    expect(document.body.textContent).not.toContain("memory-token");
  });
});
