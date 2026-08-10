import type { Category, PublicProduct } from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/api/v1/catalog${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(detail?.detail ?? `Catalog request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function fetchCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export function fetchProducts(params: { query?: string; categoryId?: number }): Promise<PublicProduct[]> {
  const search = new URLSearchParams();
  if (params.query) search.set("q", params.query);
  if (params.categoryId) search.set("category_id", String(params.categoryId));
  const suffix = search.toString();
  return request<PublicProduct[]>(`/products${suffix ? `?${suffix}` : ""}`);
}

export function fetchProduct(productId: number): Promise<PublicProduct> {
  return request<PublicProduct>(`/products/${productId}`);
}
