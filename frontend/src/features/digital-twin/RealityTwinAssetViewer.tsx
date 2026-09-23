import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type RealityTwinAssetViewerProps = {
  asset?: any;
  twin?: any;
  data?: any;
  assetCode?: string;
  asset_code?: string;
  assetType?: string;
  asset_type?: string;
  className?: string;
  style?: React.CSSProperties;
  [key: string]: any;
};

type ViewerState =
  | "LOADING"
  | "EXACT_MODEL"
  | "PARAMETRIC"
  | "PROXY"
  | "ERROR";

function numberOrNull(...values: any[]): number | null {
  for (const value of values) {
    const n = Number(value);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

function inferType(code: string, explicit?: string): string {
  const t = String(explicit || "").toUpperCase();

  if (t) {
    if (t.includes("AIR")) return "AIRPORT";
    if (t.includes("BARRAGE")) return "BARRAGE";
    if (t.includes("BRIDGE")) return "BRIDGE";
    if (t.includes("DAM")) return "DAM";
    if (t.includes("TEMPLE")) return "TEMPLE";
  }

  const c = String(code || "").toUpperCase();

  if (c.includes("AIR")) return "AIRPORT";
  if (c.includes("BARRAGE") || c.includes("_BAR_")) return "BARRAGE";
  if (c.includes("BR_")) return "BRIDGE";
  if (c.includes("DAM")) return "DAM";
  if (c.includes("TEMPLE") || c.includes("TEMP")) return "TEMPLE";

  return "GENERIC";
}

function getStoredAssetCode(): string {
  try {
    const params = new URLSearchParams(window.location.search);

    const queryCode =
      params.get("asset") ||
      params.get("asset_code") ||
      params.get("assetCode");

    if (queryCode) return queryCode;

    const keys = [
      "selectedAssetCode",
      "selected_asset_code",
      "simras_selected_asset",
      "selectedAsset",
    ];

    for (const key of keys) {
      const raw =
        sessionStorage.getItem(key) ||
        localStorage.getItem(key);

      if (!raw) continue;

      try {
        const parsed = JSON.parse(raw);

        if (typeof parsed === "string") return parsed;

        if (parsed?.asset_code) return parsed.asset_code;
        if (parsed?.assetCode) return parsed.assetCode;
        if (parsed?.code) return parsed.code;
      } catch {
        return raw;
      }
    }
  } catch {
    // ignore storage errors
  }

  return "";
}

function material(
  color: number,
  roughness = 0.65,
  metalness = 0.08
) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness,
    metalness,
  });
}

function addBox(
  parent: THREE.Object3D,
  sx: number,
  sy: number,
  sz: number,
  x: number,
  y: number,
  z: number,
  color: number
) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(sx, sy, sz),
    material(color)
  );

  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  parent.add(mesh);

  return mesh;
}

function buildAirport(
  root: THREE.Group,
  lengthRatio: number,
  widthRatio: number
) {
  const runwayLength = Math.max(12, 24 * lengthRatio);
  const runwayWidth = Math.max(1.3, 3 * widthRatio);

  addBox(
    root,
    runwayLength,
    0.18,
    runwayWidth,
    0,
    0.1,
    0,
    0x3d454d
  );

  // Center runway line
  const markerCount = 13;

  for (let i = 0; i < markerCount; i++) {
    const x =
      -runwayLength / 2 +
      1.2 +
      (i * (runwayLength - 2.4)) / (markerCount - 1);

    addBox(
      root,
      0.7,
      0.03,
      0.08,
      x,
      0.205,
      0,
      0xf4f4f4
    );
  }

  // Taxiway
  addBox(
    root,
    runwayLength * 0.55,
    0.11,
    runwayWidth * 0.55,
    1,
    0.06,
    runwayWidth * 1.45,
    0x565f68
  );

  // Apron
  addBox(
    root,
    6,
    0.12,
    5,
    runwayLength * 0.16,
    0.07,
    runwayWidth * 3,
    0x777f87
  );

  // Terminal
  addBox(
    root,
    5,
    1.7,
    2.4,
    runwayLength * 0.18,
    0.9,
    runwayWidth * 4.4,
    0xd6dde3
  );

  addBox(
    root,
    2.2,
    0.7,
    1.7,
    runwayLength * 0.02,
    0.42,
    runwayWidth * 4.4,
    0xbac6ce
  );
}

function buildBridge(
  root: THREE.Group,
  lengthRatio: number,
  widthRatio: number
) {
  const length = Math.max(12, 22 * lengthRatio);
  const width = Math.max(2, 4 * widthRatio);

  // water
  addBox(root, length + 8, 0.08, 15, 0, -1.9, 0, 0x357ca5);

  // deck
  addBox(root, length, 0.65, width, 0, 2, 0, 0x8b9298);

  const pillars = 7;

  for (let i = 0; i < pillars; i++) {
    const x =
      -length / 2 +
      2 +
      (i * (length - 4)) / Math.max(1, pillars - 1);

    addBox(root, 0.75, 4.3, 1.1, x, -0.1, 0, 0xb3b8bc);
  }

  // side barriers
  addBox(root, length, 0.35, 0.18, 0, 2.55, width / 2, 0xd4d7da);
  addBox(root, length, 0.35, 0.18, 0, 2.55, -width / 2, 0xd4d7da);
}

function buildDam(
  root: THREE.Group,
  lengthRatio: number,
  heightRatio: number
) {
  const length = Math.max(14, 22 * lengthRatio);
  const height = Math.max(4, 7 * heightRatio);

  // reservoir
  addBox(root, length + 10, 0.12, 12, 0, 0.1, -5, 0x2c86b7);

  // dam wall
  const wall = new THREE.Mesh(
    new THREE.BoxGeometry(length, height, 2.2),
    material(0x9da5aa)
  );

  wall.position.y = height / 2;

  wall.rotation.x = -0.06;

  wall.castShadow = true;
  wall.receiveShadow = true;

  root.add(wall);

  // spillway
  addBox(root, 5, height * 0.75, 2.5, 0, height * 0.38, 0.2, 0x7f878c);
}

function buildBarrage(
  root: THREE.Group,
  lengthRatio: number
) {
  const length = Math.max(15, 24 * lengthRatio);

  addBox(root, length + 8, 0.1, 16, 0, -1.3, 0, 0x347fa7);

  addBox(root, length, 0.7, 3.8, 0, 3, 0, 0x9ba1a6);

  const gateCount = 12;

  for (let i = 0; i < gateCount; i++) {
    const x =
      -length / 2 +
      1 +
      (i * (length - 2)) / (gateCount - 1);

    addBox(root, 0.35, 5, 0.8, x, 0.2, 0, 0xb8bdc0);

    if (i < gateCount - 1) {
      addBox(
        root,
        length / gateCount - 0.2,
        2.1,
        0.18,
        x + length / gateCount / 2,
        0,
        0,
        0x586975
      );
    }
  }
}

function buildTemple(
  root: THREE.Group,
  widthRatio: number,
  heightRatio: number
) {
  const base = Math.max(5, 7 * widthRatio);

  addBox(root, base, 0.7, base, 0, 0.35, 0, 0xc9a35c);

  addBox(root, base * 0.75, 1.4, base * 0.68, 0, 1.35, 0, 0xd5ad63);

  let y = 2.3;

  const levels = 7;

  for (let i = 0; i < levels; i++) {
    const scale = 1 - i * 0.105;

    const w = base * 0.58 * scale;
    const d = base * 0.47 * scale;
    const h = 0.7 * Math.max(0.7, heightRatio);

    addBox(
      root,
      w,
      h,
      d,
      0,
      y,
      0,
      i % 2 === 0 ? 0xd39545 : 0xe0b45c
    );

    y += h;
  }

  // finial
  const cone = new THREE.Mesh(
    new THREE.ConeGeometry(0.4, 1.3, 12),
    material(0xc68b31)
  );

  cone.position.y = y + 0.5;

  root.add(cone);
}

function buildGeneric(root: THREE.Group) {
  addBox(root, 8, 2.5, 5, 0, 1.25, 0, 0x5d7f91);

  addBox(root, 4, 3.5, 3, 0, 4.2, 0, 0x7997a7);
}

function disposeObject(object: THREE.Object3D) {
  object.traverse((child: any) => {
    if (child.geometry) {
      child.geometry.dispose?.();
    }

    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach((m: any) => m.dispose?.());
      } else {
        child.material.dispose?.();
      }
    }
  });
}

export function RealityTwinAssetViewer(
  props: RealityTwinAssetViewerProps
) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  const [viewerState, setViewerState] =
    useState<ViewerState>("LOADING");

  const [error, setError] = useState<string>("");

  const [resolvedTwin, setResolvedTwin] = useState<any>(
    props.twin || props.data || null
  );

  const asset = props.asset || props.data?.asset || {};

  const assetCode = useMemo(() => {
    return (
      props.assetCode ||
      props.asset_code ||
      asset.asset_code ||
      asset.assetCode ||
      asset.code ||
      resolvedTwin?.asset_code ||
      getStoredAssetCode() ||
      "SIMRAS_ASSET"
    );
  }, [
    props.assetCode,
    props.asset_code,
    asset,
    resolvedTwin,
  ]);

  const explicitType =
    props.assetType ||
    props.asset_type ||
    asset.asset_type ||
    asset.assetType ||
    asset.category ||
    resolvedTwin?.asset_type ||
    resolvedTwin?.category;

  const assetType = inferType(assetCode, explicitType);

  // Try backend twin API, but NEVER block fallback geometry.
  useEffect(() => {
    let cancelled = false;

    async function loadTwin() {
      if (
        props.twin ||
        (props.data && props.data.asset_code)
      ) {
        setResolvedTwin(props.twin || props.data);
        return;
      }

      if (!assetCode || assetCode === "SIMRAS_ASSET") return;

      try {
        const raw =
          (import.meta as any).env?.VITE_API_BASE_URL ||
          "http://localhost:8000/api/v1";

        const base = String(raw).replace(/\/+$/, "");

        const url =
          `${base}/assets/${encodeURIComponent(assetCode)}/twin`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Twin API HTTP ${response.status}`);
        }

        const json = await response.json();

        if (!cancelled) {
          setResolvedTwin(json);
        }
      } catch (e: any) {
        // API failure should NOT produce blank viewer.
        console.warn(
          "[SIMRAS Digital Twin] Twin API unavailable, using proxy geometry:",
          e
        );
      }
    }

    loadTwin();

    return () => {
      cancelled = true;
    };
  }, [assetCode, props.twin, props.data]);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) return;

    setViewerState("LOADING");
    setError("");

    while (mount.firstChild) {
      mount.removeChild(mount.firstChild);
    }

    let renderer: THREE.WebGLRenderer | null = null;
    let controls: OrbitControls | null = null;
    let animationFrame = 0;
    let resizeObserver: ResizeObserver | null = null;

    const scene = new THREE.Scene();

    scene.background = new THREE.Color(0xcbd4da);

    scene.fog = new THREE.Fog(
      0xcbd4da,
      40,
      130
    );

    const camera = new THREE.PerspectiveCamera(
      42,
      1,
      0.05,
      500
    );

    camera.position.set(20, 14, 22);

    const root = new THREE.Group();

    scene.add(root);

    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      });

      renderer.setPixelRatio(
        Math.min(window.devicePixelRatio || 1, 2)
      );

      renderer.shadowMap.enabled = true;

      renderer.shadowMap.type =
        THREE.PCFSoftShadowMap;

      renderer.outputColorSpace =
        THREE.SRGBColorSpace;

      mount.appendChild(renderer.domElement);

      // Lighting
      scene.add(
        new THREE.HemisphereLight(
          0xffffff,
          0x62717c,
          2.1
        )
      );

      const sun = new THREE.DirectionalLight(
        0xffffff,
        3.2
      );

      sun.position.set(20, 30, 18);

      sun.castShadow = true;

      scene.add(sun);

      const fill = new THREE.DirectionalLight(
        0xbad8ff,
        1.1
      );

      fill.position.set(-15, 12, -12);

      scene.add(fill);

      // Ground
      const ground = new THREE.Mesh(
        new THREE.PlaneGeometry(100, 100),
        new THREE.MeshStandardMaterial({
          color: 0xaeb9bf,
          roughness: 1,
        })
      );

      ground.rotation.x = -Math.PI / 2;

      ground.position.y = -2;

      ground.receiveShadow = true;

      scene.add(ground);

      const grid = new THREE.GridHelper(
        70,
        35,
        0x71818c,
        0x94a2aa
      );

      grid.position.y = -1.95;

      scene.add(grid);

      const dims =
        resolvedTwin?.dimensions ||
        asset?.dimensions ||
        {};

      const length =
        numberOrNull(
          dims.length_m,
          dims.length,
          asset?.length_m,
          asset?.length
        ) || 100;

      const width =
        numberOrNull(
          dims.width_m,
          dims.width,
          dims.breadth_m,
          asset?.width_m,
          asset?.width
        ) || 20;

      const height =
        numberOrNull(
          dims.height_m,
          dims.height,
          asset?.height_m,
          asset?.height
        ) || 20;

      // Normalize engineering dimensions to safe scene scale.
      const maxDim = Math.max(length, width, height, 1);

      const lengthRatio = THREE.MathUtils.clamp(
        length / maxDim,
        0.3,
        1
      );

      const widthRatio = THREE.MathUtils.clamp(
        width / maxDim,
        0.18,
        1
      );

      const heightRatio = THREE.MathUtils.clamp(
        height / maxDim,
        0.25,
        1
      );

      switch (assetType) {
        case "AIRPORT":
          buildAirport(
            root,
            Math.max(0.7, lengthRatio),
            Math.max(0.3, widthRatio)
          );
          break;

        case "BRIDGE":
          buildBridge(
            root,
            Math.max(0.7, lengthRatio),
            Math.max(0.3, widthRatio)
          );
          break;

        case "DAM":
          buildDam(
            root,
            Math.max(0.7, lengthRatio),
            Math.max(0.4, heightRatio)
          );
          break;

        case "BARRAGE":
          buildBarrage(
            root,
            Math.max(0.7, lengthRatio)
          );
          break;

        case "TEMPLE":
          buildTemple(
            root,
            Math.max(0.45, widthRatio),
            Math.max(0.45, heightRatio)
          );
          break;

        default:
          buildGeneric(root);
          break;
      }

      // Automatic model centering
      const box = new THREE.Box3().setFromObject(root);

      if (!box.isEmpty()) {
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        root.position.sub(center);

        // Preserve ground relationship after centering.
        const correctedBox = new THREE.Box3().setFromObject(root);

        root.position.y +=
          -1.85 - correctedBox.min.y;

        const maxSize = Math.max(
          size.x,
          size.y,
          size.z,
          5
        );

        const distance = maxSize * 1.35 + 8;

        camera.position.set(
          distance,
          distance * 0.58,
          distance
        );

        camera.near = Math.max(
          0.05,
          distance / 1000
        );

        camera.far = Math.max(
          500,
          distance * 20
        );

        camera.updateProjectionMatrix();
      }

      controls = new OrbitControls(
        camera,
        renderer.domElement
      );

      controls.enableDamping = true;

      controls.dampingFactor = 0.06;

      controls.enablePan = true;

      controls.minDistance = 4;

      controls.maxDistance = 150;

      controls.target.set(0, 1.5, 0);

      controls.update();

      function resize() {
        if (!renderer || !mount) return;

        const width =
          Math.max(mount.clientWidth, 320);

        const height =
          Math.max(mount.clientHeight, 420);

        renderer.setSize(
          width,
          height,
          false
        );

        camera.aspect =
          width / height;

        camera.updateProjectionMatrix();
      }

      resize();

      resizeObserver =
        new ResizeObserver(resize);

      resizeObserver.observe(mount);

      function animate() {
        animationFrame =
          requestAnimationFrame(animate);

        controls?.update();

        renderer?.render(
          scene,
          camera
        );
      }

      animate();

      setViewerState(
        resolvedTwin?.model_url
          ? "PARAMETRIC"
          : "PROXY"
      );
    } catch (e: any) {
      console.error(
        "[SIMRAS Digital Twin] Viewer error:",
        e
      );

      setViewerState("ERROR");

      setError(
        e?.message ||
          "Unable to initialize 3D viewer."
      );
    }

    return () => {
      cancelAnimationFrame(animationFrame);

      resizeObserver?.disconnect();

      controls?.dispose();

      disposeObject(root);

      renderer?.dispose();

      if (
        renderer?.domElement &&
        renderer.domElement.parentNode === mount
      ) {
        mount.removeChild(
          renderer.domElement
        );
      }
    };
  }, [
    assetCode,
    assetType,
    resolvedTwin,
    asset,
  ]);

  const dimensions =
    resolvedTwin?.dimensions ||
    asset?.dimensions ||
    {};

  const geometryLabel =
    viewerState === "ERROR"
      ? "ERROR"
      : resolvedTwin?.geometry_mode ||
        viewerState;

  return (
    <div
      className={props.className}
      style={{
        position: "relative",
        width: "100%",
        minHeight: 520,
        overflow: "hidden",
        borderRadius: 12,
        background: "#cbd4da",
        ...props.style,
      }}
    >
      <div
        ref={mountRef}
        style={{
          width: "100%",
          height: "clamp(520px, 68vh, 820px)",
          minHeight: 520,
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 16,
          top: 16,
          zIndex: 20,
          background: "rgba(4, 19, 29, 0.90)",
          color: "#fff",
          padding: "12px 15px",
          borderRadius: 8,
          fontSize: 13,
          lineHeight: 1.55,
          boxShadow:
            "0 6px 20px rgba(0,0,0,.18)",
        }}
      >
        <div
          style={{
            fontWeight: 800,
            letterSpacing: ".08em",
            color: "#67d8f3",
          }}
        >
          {assetCode}
        </div>

        <div>
          {assetType}
        </div>

        <div>
          Geometry: {geometryLabel}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          right: 16,
          top: 16,
          zIndex: 20,
          minWidth: 185,
          background: "rgba(255,255,255,.92)",
          color: "#0b2232",
          padding: "12px 15px",
          borderRadius: 8,
          fontSize: 12,
          lineHeight: 1.6,
          boxShadow:
            "0 6px 20px rgba(0,0,0,.15)",
        }}
      >
        <strong>
          Engineering dimensions
        </strong>

        <div>
          Length:{" "}
          {dimensions.length_m ??
            dimensions.length ??
            asset?.length_m ??
            "Not verified"}
        </div>

        <div>
          Width:{" "}
          {dimensions.width_m ??
            dimensions.width ??
            dimensions.breadth_m ??
            asset?.width_m ??
            "Not verified"}
        </div>

        <div>
          Height:{" "}
          {dimensions.height_m ??
            dimensions.height ??
            asset?.height_m ??
            "Not verified"}
        </div>
      </div>

      {viewerState === "LOADING" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            background:
              "rgba(203,212,218,.72)",
            color: "#082436",
            fontWeight: 700,
            zIndex: 30,
          }}
        >
          Loading SIMRAS Digital Twin...
        </div>
      )}

      {viewerState === "ERROR" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            background:
              "rgba(35,20,20,.88)",
            color: "#fff",
            padding: 30,
            zIndex: 40,
            textAlign: "center",
          }}
        >
          <div>
            <h3>
              Digital Twin Load Error
            </h3>

            <p>
              {error}
            </p>

            <button
              type="button"
              onClick={() =>
                window.location.reload()
              }
            >
              Retry
            </button>
          </div>
        </div>
      )}

      <div
        style={{
          position: "absolute",
          left: 16,
          bottom: 16,
          zIndex: 20,
          background: "rgba(4,19,29,.88)",
          color: "#dce9ef",
          padding: "8px 12px",
          borderRadius: 7,
          fontSize: 12,
        }}
      >
        Drag to rotate · Scroll to zoom · Right-drag to pan
      </div>
    </div>
  );
}

export default RealityTwinAssetViewer;
