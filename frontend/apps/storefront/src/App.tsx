import { useEffect, useState } from "react";

import { StorefrontAuthPanel } from "./auth/StorefrontAuthPanel";
import { storefrontAuthStore } from "./auth/store";
import { CatalogBrowser } from "./catalog/CatalogBrowser";
import { CatalogDetail } from "./catalog/CatalogDetail";

export function App() {
  const restoreSession = storefrontAuthStore((state) => state.restoreSession);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(() => {
    const match = window.location.pathname.match(/^\/products\/(\d+)$/);
    return match ? Number(match[1]) : null;
  });

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  function openProduct(productId: number) {
    window.history.pushState({}, "", `/products/${productId}`);
    setSelectedProductId(productId);
  }

  function closeProduct() {
    window.history.pushState({}, "", "/");
    setSelectedProductId(null);
  }

  return (
    <main className="storefront-shell">
      <section className="storefront-hero" aria-label="HomePilot 品牌介绍">
        <p className="brand-mark">HomePilot</p>
        <p className="hero-index">No. 01 / home, considered</p>
        <h1>让每一件家具，都有回家的理由。</h1>
        <p className="hero-description">
          探索来自独立家居品牌的材质、故事与生活方式。可信的商品信息，和一个随时为你解答的智能伙伴。
        </p>
        {selectedProductId === null ? (
          <CatalogBrowser onOpenProduct={openProduct} />
        ) : (
          <CatalogDetail productId={selectedProductId} onBack={closeProduct} />
        )}
      </section>
      <StorefrontAuthPanel />
    </main>
  );
}
