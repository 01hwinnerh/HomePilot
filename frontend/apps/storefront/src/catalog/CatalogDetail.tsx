import { useEffect, useState } from "react";

import { fetchProduct } from "./api";
import type { PublicProduct } from "./types";

type CatalogDetailProps = { productId: number; onBack: () => void };

export function CatalogDetail({ productId, onBack }: CatalogDetailProps) {
  const [product, setProduct] = useState<PublicProduct | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setProduct(null);
    setError("");
    void fetchProduct(productId).then(setProduct).catch(() => setError("这件商品已经离开目录了。"));
  }, [productId]);

  if (error) {
    return <section className="catalog-detail catalog-message" role="alert"><p>{error}</p><button onClick={onBack}>返回目录</button></section>;
  }
  if (!product) return <section className="catalog-detail catalog-message">正在打开商品详情。</section>;

  return (
    <section className="catalog-detail" aria-label="商品详情">
      <button className="catalog-back" onClick={onBack}>← 返回目录</button>
      <p className="catalog-kicker">{product.category_name} / {product.store_name}</p>
      <h2>{product.name}</h2>
      <p className="catalog-detail-description">{product.description}</p>
      <p className="catalog-detail-source">{product.merchant_name} · {product.store_name}</p>
      <div className="sku-list">
        {product.skus.map((sku) => (
          <div className="sku-row" key={sku.id}>
            <div><strong>{sku.sku_name}</strong><span>{Object.entries(sku.variant_attributes).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</span></div>
            <b>¥{(sku.price_minor / 100).toFixed(2)}</b>
          </div>
        ))}
      </div>
    </section>
  );
}
