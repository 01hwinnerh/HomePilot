export type Category = {
  id: number;
  parent_id: number | null;
  slug: string;
  name: string;
  sort_order: number;
};

export type PublicSku = {
  id: number;
  sku_code: string;
  sku_name: string;
  variant_attributes: Record<string, string | number | boolean | null>;
  price_minor: number;
  currency: string;
};

export type PublicProduct = {
  id: number;
  merchant_id: number;
  merchant_name: string;
  store_id: number;
  store_name: string;
  store_slug: string;
  category_id: number;
  category_name: string;
  name: string;
  description: string;
  skus: PublicSku[];
};
