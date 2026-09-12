import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";

const cesiumSource = "node_modules/cesium/Build/Cesium";

export default defineConfig({
  define: {
    CESIUM_BASE_URL: JSON.stringify("/cesium"),
  },
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        { src: "node_modules/@cesium/engine/Build/Workers", dest: "cesium" },
        { src: "node_modules/@cesium/engine/Build/ThirdParty", dest: "cesium" },
        { src: "node_modules/@cesium/engine/Source/Assets", dest: "cesium" },
      ],
    }),
  ],
  server: { port: 5173 },
});



