import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogBrowser } from "./CatalogBrowser";
import { CatalogDetail } from "./CatalogDetail";

describe("CatalogBrowser", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads categories and shows products from their source merchants", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/categories")) {
        return new Response(JSON.stringify([{ id: 1, parent_id: null, slug: "living", name: "客厅", sort_order: 1 }]), { status: 200 });
      }
      return new Response(JSON.stringify([{
        id: 8,
        merchant_id: 2,
        merchant_name: "木作商社",
        store_id: 3,
        store_name: "木作客厅",
        store_slug: "wood-living",
        category_id: 1,
        category_name: "客厅",
        name: "胡桃木边几",
        description: "一张安静的边几",
        skus: [{ id: 9, sku_code: "TABLE-1", sku_name: "标准款", variant_attributes: { color: "胡桃木" }, price_minor: 19900, currency: "CNY" }],
      }]), { status: 200 });
    });

    render(<CatalogBrowser onOpenProduct={vi.fn()} />);

    expect(await screen.findByText("胡桃木边几")).toBeTruthy();
    expect(screen.getByText("来自 木作客厅 · 木作商社")).toBeTruthy();
    expect(screen.getByRole("button", { name: "客厅" })).toBeTruthy();
  });

  it("shows a retryable error when search is unavailable", async () => {
    let productRequests = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/categories")) return new Response("[]", { status: 200 });
      productRequests += 1;
      if (productRequests === 1) return new Response("[]", { status: 200 });
      return new Response(JSON.stringify({ detail: "SEARCH_UNAVAILABLE" }), { status: 503 });
    });

    render(<CatalogBrowser onOpenProduct={vi.fn()} />);
    await screen.findByText("没有找到这件东西。换个关键词试试？");
    fireEvent.change(screen.getByLabelText("搜索材质、风格或商品"), { target: { value: "沙发" } });
    fireEvent.click(screen.getByRole("button", { name: "发现" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(screen.getByRole("alert").textContent).toContain("搜索服务正在休息");
  });

  it("shows a public product detail and active SKU prices", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      id: 8,
      merchant_id: 2,
      merchant_name: "木作商社",
      store_id: 3,
      store_name: "木作客厅",
      store_slug: "wood-living",
      category_id: 1,
      category_name: "客厅",
      name: "胡桃木边几",
      description: "一张安静的边几",
      skus: [{ id: 9, sku_code: "TABLE-1", sku_name: "标准款", variant_attributes: { color: "胡桃木" }, price_minor: 19900, currency: "CNY" }],
    }), { status: 200 }));

    render(<CatalogDetail productId={8} onBack={vi.fn()} />);

    expect(await screen.findByText("胡桃木边几")).toBeTruthy();
    expect(screen.getByText("¥199.00")).toBeTruthy();
  });
});
