import fs from "node:fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteStaticCopy } from "vite-plugin-static-copy";

const targets: {
  src: string;
  dest: string;
}[] = [];

function addCesiumDirectory(
  candidates: string[],
) {
  const src = candidates.find(
    (candidate) => fs.existsSync(candidate),
  );

  if (src) {
    targets.push({
      src,
      dest: "cesium",
    });

    console.log(
      `[Cesium] static resource: ${src}`,
    );
  }
}

addCesiumDirectory([
  "node_modules/@cesium/engine/Build/Workers",
  "node_modules/cesium/Build/CesiumUnminified/Workers",
  "node_modules/cesium/Build/Cesium/Workers",
]);

addCesiumDirectory([
  "node_modules/@cesium/engine/Build/ThirdParty",
  "node_modules/cesium/Build/CesiumUnminified/ThirdParty",
  "node_modules/cesium/Build/Cesium/ThirdParty",
]);

addCesiumDirectory([
  "node_modules/@cesium/engine/Source/Assets",
  "node_modules/cesium/Build/CesiumUnminified/Assets",
  "node_modules/cesium/Build/Cesium/Assets",
]);

addCesiumDirectory([
  "node_modules/cesium/Build/Cesium/Widgets",
  "node_modules/cesium/Build/CesiumUnminified/Widgets",
  "node_modules/@cesium/widgets/Source/Widgets",
]);

export default defineConfig({
  define: {
    CESIUM_BASE_URL:
      JSON.stringify("/cesium"),
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
