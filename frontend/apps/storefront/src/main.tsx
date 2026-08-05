import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./styles.css";

function App() {
  return (
    <main className="min-h-screen bg-stone-50 px-6 py-20 text-stone-900">
      <section className="mx-auto max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-amber-700">HomePilot</p>
        <h1 className="mt-4 text-5xl font-semibold tracking-tight">AI-powered home marketplace</h1>
        <p className="mt-6 max-w-xl text-lg leading-8 text-stone-600">
          用户商城骨架已就绪。后续将逐步接入商品浏览、跨店购物车与可信 Agent 客服。
        </p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
