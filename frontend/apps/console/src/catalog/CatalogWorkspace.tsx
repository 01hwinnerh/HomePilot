import { useEffect, useState } from "react";

import { Alert, Button, Card, Empty, Input, Select, Space, Tag, Typography } from "antd";

import type { MerchantMembership } from "@homepilot/auth-client";

import { createProduct, createSku, fetchProducts, fetchSkus, fetchStores, transitionProduct, type Product, type Sku, type Store } from "./api";

type CatalogWorkspaceProps = { token: string; memberships: MerchantMembership[] };

export function CatalogWorkspace({ token, memberships }: CatalogWorkspaceProps) {
  const [merchantId, setMerchantId] = useState(memberships[0]?.merchant_id);
  const [stores, setStores] = useState<Store[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [skus, setSkus] = useState<Sku[]>([]);
  const [productName, setProductName] = useState("");
  const [skuName, setSkuName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function reload(nextMerchantId = merchantId) {
    if (!nextMerchantId) return;
    try {
      const [nextStores, nextProducts] = await Promise.all([
        fetchStores(token, nextMerchantId),
        fetchProducts(token, nextMerchantId),
      ]);
      setStores(nextStores);
      setProducts(nextProducts);
      setSelectedProduct(null);
      setSkus([]);
    } catch {
      setError("目录加载失败，请检查当前商家权限。");
    }
  }

  useEffect(() => { void reload(); }, [merchantId, token]);

  async function openProduct(product: Product) {
    if (!merchantId) return;
    setSelectedProduct(product);
    try { setSkus(await fetchSkus(token, merchantId, product.id)); } catch { setError("SKU 加载失败。"); }
  }

  async function addProduct() {
    if (!merchantId || !stores[0] || !productName.trim()) return;
    try {
      await createProduct(token, merchantId, stores[0].id, { name: productName.trim(), description: "", category_id: 1 });
      setProductName("");
      await reload();
    } catch { setError("商品创建失败，请确认类目和店铺状态。"); }
  }

  async function addSku() {
    if (!merchantId || !selectedProduct || !skuName.trim()) return;
    try {
      const sku = await createSku(token, merchantId, selectedProduct.id, { sku_code: `${selectedProduct.id}-${Date.now()}`, sku_name: skuName.trim(), price_minor: 0 });
      setSkus((current) => [...current, sku]);
      setSkuName("");
    } catch { setError("SKU 创建失败。"); }
  }

  async function transition(product: Product, action: "publish" | "archive") {
    if (!merchantId) return;
    try { await transitionProduct(token, merchantId, product.id, action); await reload(); } catch { setError("状态变更失败，请检查商品是否满足发布条件。"); }
  }

  if (!merchantId) return <Empty description="没有可管理的商家" />;
  return (
    <section className="console-catalog-workspace" aria-label="商品目录工作台">
      {error && <Alert closable message={error} onClose={() => setError(null)} type="error" />}
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Space wrap>
          <Typography.Text strong>当前商家</Typography.Text>
          <Select value={merchantId} onChange={(value) => setMerchantId(value)} options={memberships.map((item) => ({ value: item.merchant_id, label: `${item.merchant_name} · ${item.role}` }))} />
          <Tag color="gold">{stores.length} 家店铺</Tag>
        </Space>
        <Card title="商品目录" extra={<Space><Input value={productName} onChange={(event) => setProductName(event.target.value)} placeholder="新商品名称" /><Button type="primary" onClick={() => void addProduct()}>创建商品</Button></Space>}>
          {products.length === 0 ? <Empty description="还没有商品" /> : products.map((product) => (
            <div className="console-product-row" key={product.id}>
              <div><Typography.Text strong>{product.name}</Typography.Text><Typography.Paragraph type="secondary">店铺 #{product.store_id} · 类目 #{product.category_id}</Typography.Paragraph></div>
              <Space><Tag>{product.status}</Tag><Button type="link" onClick={() => void openProduct(product)}>管理 SKU</Button>{product.status === "DRAFT" ? <Button type="link" onClick={() => void transition(product, "publish")}>发布</Button> : <Button type="link" danger onClick={() => void transition(product, "archive")}>归档</Button>}</Space>
            </div>
          ))}
        </Card>
        {selectedProduct && <Card title={`${selectedProduct.name} / SKU`} extra={<Space><Input value={skuName} onChange={(event) => setSkuName(event.target.value)} placeholder="规格名称" /><Button onClick={() => void addSku()}>新增 SKU</Button></Space>}>
          {skus.map((sku) => <div className="console-sku-row" key={sku.id}><span>{sku.sku_name}</span><strong>¥{(sku.price_minor / 100).toFixed(2)}</strong></div>)}
        </Card>}
      </Space>
    </section>
  );
}
