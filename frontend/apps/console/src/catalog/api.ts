export type Store = { id: number; merchant_id: number; name: string; slug: string; is_active: boolean };
export type Product = { id: number; merchant_id: number; store_id: number; category_id: number; name: string; description: string; status: string };
export type Sku = { id: number; merchant_id: number; product_id: number; sku_code: string; sku_name: string; variant_attributes: Record<string, string | number | boolean | null>; price_minor: number; currency: string; is_active: boolean };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init?.headers },
  });
  if (!response.ok) throw new Error(`Console catalog request failed (${response.status})`);
  return (await response.json()) as T;
}

export function fetchStores(token: string, merchantId: number): Promise<Store[]> {
  return request(token, `/api/v1/merchants/${merchantId}/stores`);
}

export function fetchProducts(token: string, merchantId: number, status?: string): Promise<Product[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(token, `/api/v1/merchants/${merchantId}/products${suffix}`);
}

export function fetchSkus(token: string, merchantId: number, productId: number): Promise<Sku[]> {
  return request(token, `/api/v1/merchants/${merchantId}/products/${productId}/skus`);
}

export function createProduct(token: string, merchantId: number, storeId: number, input: { name: string; description: string; category_id: number }): Promise<Product> {
  return request(token, `/api/v1/merchants/${merchantId}/stores/${storeId}/products`, { method: "POST", body: JSON.stringify({ ...input, store_id: storeId }) });
}

export function transitionProduct(token: string, merchantId: number, productId: number, transition: "publish" | "archive"): Promise<Product> {
  return request(token, `/api/v1/merchants/${merchantId}/products/${productId}/${transition}`, { method: "POST" });
}

export function createSku(token: string, merchantId: number, productId: number, input: { sku_code: string; sku_name: string; price_minor: number }): Promise<Sku> {
  return request(token, `/api/v1/merchants/${merchantId}/products/${productId}/skus`, { method: "POST", body: JSON.stringify({ ...input, product_id: productId, variant_attributes: {}, currency: "CNY" }) });
}
