import { useEffect } from "react";

import { StorefrontAuthPanel } from "./auth/StorefrontAuthPanel";
import { storefrontAuthStore } from "./auth/store";

export function App() {
  const restoreSession = storefrontAuthStore((state) => state.restoreSession);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  return (
    <main className="storefront-shell">
      <section className="storefront-hero" aria-label="HomePilot 品牌介绍">
        <p className="brand-mark">HomePilot</p>
        <p className="hero-index">No. 01 / home, considered</p>
        <h1>让每一件家具，都有回家的理由。</h1>
        <p>
          探索来自独立家居品牌的材质、故事与生活方式。可信的商品信息，和一个随时为你解答的智能伙伴。
        </p>
      </section>
      <StorefrontAuthPanel />
    </main>
  );
}
