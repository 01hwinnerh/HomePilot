import { useEffect } from "react";

import { App as AntdApp, ConfigProvider } from "antd";

import { ConsoleAuthPanel } from "./auth/ConsoleAuthPanel";
import { consoleAuthStore } from "./auth/store";

import "./styles.css";

export function App() {
  const restoreSession = consoleAuthStore((state) => state.restoreSession);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  return (
    <ConfigProvider theme={{ token: { colorPrimary: "#9a5b24", borderRadius: 10 } }}>
      <AntdApp>
        <ConsoleAuthPanel />
      </AntdApp>
    </ConfigProvider>
  );
}
