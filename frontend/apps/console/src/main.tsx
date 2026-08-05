import { App as AntdApp, ConfigProvider, Layout, Typography } from "antd";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "antd/dist/reset.css";

function ConsoleHome() {
  return (
    <ConfigProvider theme={{ token: { colorPrimary: "#9a5b24", borderRadius: 10 } }}>
      <AntdApp>
        <Layout style={{ minHeight: "100vh", padding: "72px max(24px, 8vw)", background: "#faf9f6" }}>
          <Typography.Text type="secondary">HOMEPILOT CONSOLE</Typography.Text>
          <Typography.Title level={1}>商家与平台控制台</Typography.Title>
          <Typography.Paragraph style={{ fontSize: 17, maxWidth: 640 }}>
            控制台骨架已就绪。商品管理、知识审核、售后审核与人工接管将在后续模块逐步接入。
          </Typography.Paragraph>
        </Layout>
      </AntdApp>
    </ConfigProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConsoleHome />
  </StrictMode>,
);
