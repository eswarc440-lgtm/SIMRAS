import path from "node:path";
import fs from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";

const cesiumBaseUrl = "cesium";

const possibleTargets = [
  {
    src: "node_modules/@cesium/engine/Build/Workers",
    dest: cesiumBaseUrl,
  },
  {
    src: "node_modules/@cesium/engine/Build/ThirdParty",
    dest: cesiumBaseUrl,
  },
  {
    src: "node_modules/@cesium/engine/Source/Assets",
    dest: cesiumBaseUrl,
  },
  {
    src: "node_modules/cesium/Build/Cesium/Widgets",
    dest: cesiumBaseUrl,
  },
];

const targets = possibleTargets.filter((target) => {
  const exists = fs.existsSync(target.src);

  if (!exists) {
    console.warn(
      `[Cesium] Static directory not found: ${target.src}`,
    );
  }

  return exists;
});

export default defineConfig({
  define: {
    CESIUM_BASE_URL: JSON.stringify(
      `/${cesiumBaseUrl}`,
    ),
  },

  plugins: [
    react(),

    viteStaticCopy({
      targets,
    }),
  ],

  server: {
    port: 5173,
  },
});
