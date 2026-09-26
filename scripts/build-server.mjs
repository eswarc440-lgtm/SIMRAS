import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import path from "node:path";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

await build({
  absWorkingDir: projectRoot,
  entryPoints: ["./server.ts"],
  bundle: true,
  platform: "node",
  format: "cjs",
  packages: "external",
  sourcemap: true,
  outfile: path.join(projectRoot, "dist", "server.cjs"),
});
