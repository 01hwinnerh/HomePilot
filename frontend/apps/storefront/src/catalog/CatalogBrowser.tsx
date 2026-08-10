import { useEffect, useState, type CSSProperties, type FormEvent } from "react";

import { fetchCategories, fetchProducts } from "./api";
import type { Category, PublicProduct } from "./types";

type CatalogBrowserProps = { onOpenProduct: (productId: number) => void };

export function CatalogBrowser({ onOpenProduct }: CatalogBrowserProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<PublicProduct[]>([]);
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([fetchCategories(), fetchProducts({})])
      .then(([nextCategories, nextProducts]) => {
        setCategories(nextCategories);
        setProducts(nextProducts);
        setStatus("ready");
      })
      .catch(() => {
        setStatus("error");
        setError("暂时无法打开商品目录，请稍后重试。");
      });
  }, []);

  async function runSearch(nextQuery = activeQuery, nextCategoryId = categoryId) {
    setStatus("loading");
    try {
      setProducts(await fetchProducts({ query: nextQuery || undefined, categoryId: nextCategoryId }));
      setStatus("ready");
    } catch (requestError) {
      setStatus("error");
      setError(requestError instanceof Error && requestError.message === "SEARCH_UNAVAILABLE"
        ? "搜索服务正在休息，请稍后再试。"
        : "商品目录暂时不可用，请稍后重试。");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveQuery(query.trim());
    void runSearch(query.trim(), categoryId);
  }

  function selectCategory(value: string) {
    const next = value ? Number(value) : undefined;
    setCategoryId(next);
    void runSearch(activeQuery, next);
  }

  return (
    <section className="catalog-browser" aria-label="商品发现">
      <div className="catalog-heading">
        <div>
          <p className="catalog-kicker">The considered home edit</p>
          <h2>为日常，挑一件好东西。</h2>
        </div>
        <span className="catalog-count">{status === "ready" ? `${products.length} 件精选` : "正在整理"}</span>
      </div>
      <form className="catalog-search" onSubmit={submit}>
        <label htmlFor="catalog-query">搜索材质、风格或商品</label>
        <div className="catalog-search-row">
          <input
            id="catalog-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：胡桃木、沙发、安静的卧室"
          />
          <button type="submit">发现</button>
        </div>
      </form>
      <div className="catalog-filters">
        <button className={!categoryId ? "is-active" : ""} onClick={() => selectCategory("")}>全部</button>
        {categories.map((category) => (
          <button
            className={categoryId === category.id ? "is-active" : ""}
            key={category.id}
            onClick={() => selectCategory(String(category.id))}
          >
            {category.name}
          </button>
        ))}
      </div>
      {status === "loading" && <p className="catalog-message">正在为你翻找合适的家居。</p>}
      {status === "error" && <p className="catalog-message catalog-error" role="alert">{error}</p>}
      {status === "ready" && products.length === 0 && (
        <p className="catalog-message">没有找到这件东西。换个关键词试试？</p>
      )}
      {status === "ready" && products.length > 0 && (
        <div className="catalog-grid">
          {products.map((product, index) => (
            <article className="product-card" key={product.id} style={{ "--card-delay": `${index * 70}ms` } as CSSProperties}>
              <button className="product-card-button" onClick={() => onOpenProduct(product.id)}>
                <span className="product-card-number">0{index + 1}</span>
                <span className="product-card-swatch" aria-hidden="true" />
                <span className="product-card-category">{product.category_name}</span>
                <strong>{product.name}</strong>
                <span className="product-card-source">来自 {product.store_name} · {product.merchant_name}</span>
                <span className="product-card-price">¥{(Math.min(...product.skus.map((sku) => sku.price_minor)) / 100).toFixed(2)} 起</span>
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
