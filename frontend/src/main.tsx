import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./design-system.css";
import "./styles.css";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import { AssetProvider } from "./contexts/AssetContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <NotificationProvider>
        <AssetProvider>
          <App />
        </AssetProvider>
      </NotificationProvider>
    </AuthProvider>
  </StrictMode>,
);
