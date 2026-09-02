import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type AssetRecord = Record<string, unknown>;

type Props = {
  assetCode?: string | null;
};

type TwinSpec = {
  title: string;
  fidelity: string;
  evidence: string;
  dimensions: string[];
};

function clean(value: unknown, fallback = "N/A") {
  if (value === null || value === undefined) return fallback;
  const s = String(value).trim();
  return s || fallback;
}

function field(asset: AssetRecord | null, ...keys: string[]) {
  if (!asset) return "N/A";

  for (const key of keys) {
    const value = asset[key];
    if (value !== null && value !== undefined && String(value).trim()) {
      return String(value).trim();
    }
  }

  return "N/A";
}

function inferType(assetCode: string, asset: AssetRecord | null) {
  const fromAsset = field(asset, "asset_type", "type").toLowerCase();
  if (fromAsset !== "n/a") return fromAsset;

  if (assetCode.includes("_AIR_")) return "airport";
  if (assetCode.includes("_BR_")) return "bridge";
  if (assetCode.includes("_TEMPLE_")) return "temple";
  if (assetCode.includes("_BAR_")) return "barrage";
  if (assetCode.includes("_DAM_")) return "dam";

  return "infrastructure";
}

function addMesh(
  group: THREE.Group,
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  position: [number, number, number],
  rotation: [number, number, number] = [0, 0, 0],
) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(...position);
  mesh.rotation.set(...rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
}

function addWater(
  group: THREE.Group,
  width: number,
  depth: number,
  y = -1.2,
) {
  const water = new THREE.Mesh(
    new THREE.PlaneGeometry(width, depth),
    new THREE.MeshStandardMaterial({
      color: 0x0b5f83,
      roughness: 0.45,
      metalness: 0.05,
      transparent: true,
      opacity: 0.82,
      side: THREE.DoubleSide,
    }),
  );
  water.rotation.x = -Math.PI / 2;
  water.position.y = y;
  water.receiveShadow = true;
  group.add(water);
}

function buildPrakasamBarrage(group: THREE.Group) {
  const concrete = new THREE.MeshStandardMaterial({
    color: 0xbec7cf,
    roughness: 0.82,
  });

  const darkConcrete = new THREE.MeshStandardMaterial({
    color: 0x727e89,
    roughness: 0.88,
  });

  const gateMaterial = new THREE.MeshStandardMaterial({
    color: 0x426f8e,
    roughness: 0.55,
    metalness: 0.28,
  });

  const roadMaterial = new THREE.MeshStandardMaterial({
    color: 0x303840,
    roughness: 0.95,
  });

  const lampMaterial = new THREE.MeshStandardMaterial({
    color: 0xf2d27b,
    emissive: 0x7b5a16,
    emissiveIntensity: 0.25,
  });

  const gateCount = 70;
  const totalVisualLength = 150;
  const pierWidth = 0.72;
  const gateWidth = (totalVisualLength - pierWidth * (gateCount + 1)) / gateCount;
  const gateHeight = 5.8;

  addWater(group, 205, 72, -2.2);

  addMesh(
    group,
    new THREE.BoxGeometry(totalVisualLength + 5, 2.2, 9.2),
    concrete,
    [0, -0.9, 0],
  );

  for (let i = 0; i <= gateCount; i += 1) {
    const x =
      -totalVisualLength / 2 +
      i * (gateWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(pierWidth, gateHeight + 3.5, 7.4),
      concrete,
      [x, gateHeight / 2 + 0.4, 0],
    );

    addMesh(
      group,
      new THREE.BoxGeometry(pierWidth + 0.35, 0.45, 8.2),
      darkConcrete,
      [x, gateHeight + 2.0, 0],
    );
  }

  for (let i = 0; i < gateCount; i += 1) {
    const x =
      -totalVisualLength / 2 +
      pierWidth +
      gateWidth / 2 +
      i * (gateWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(gateWidth * 0.92, gateHeight, 0.34),
      gateMaterial,
      [x, gateHeight / 2, 1.25],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(totalVisualLength + 8, 0.62, 9.8),
    roadMaterial,
    [0, gateHeight + 3.1, 0],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(totalVisualLength + 8, 0.42, 0.38),
    concrete,
    [0, gateHeight + 3.72, 4.55],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(totalVisualLength + 8, 0.42, 0.38),
    concrete,
    [0, gateHeight + 3.72, -4.55],
  );

  for (let i = 0; i < 18; i += 1) {
    const x = -72 + i * 8.5;

    addMesh(
      group,
      new THREE.CylinderGeometry(0.10, 0.10, 2.4, 10),
      darkConcrete,
      [x, gateHeight + 4.25, 4.0],
    );

    addMesh(
      group,
      new THREE.SphereGeometry(0.22, 12, 8),
      lampMaterial,
      [x, gateHeight + 5.45, 4.0],
    );
  }

  const bankMaterial = new THREE.MeshStandardMaterial({
    color: 0x746b4e,
    roughness: 1,
  });

  addMesh(
    group,
    new THREE.BoxGeometry(24, 5, 20),
    bankMaterial,
    [-89, 0.3, 0],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(24, 5, 20),
    bankMaterial,
    [89, 0.3, 0],
  );
}

function buildDam(group: THREE.Group, name: string) {
  const concrete = new THREE.MeshStandardMaterial({
    color: 0xaeb7bf,
    roughness: 0.85,
  });

  const rock = new THREE.MeshStandardMaterial({
    color: 0x6f695e,
    roughness: 1,
  });

  const gate = new THREE.MeshStandardMaterial({
    color: 0x386f8f,
    roughness: 0.6,
    metalness: 0.22,
  });

  addWater(group, 170, 90, -2.5);

  const isPolavaram = name.toLowerCase().includes("polavaram");

  const wallLength = isPolavaram ? 125 : 105;
  const wallHeight = isPolavaram ? 20 : 17;

  addMesh(
    group,
    new THREE.BoxGeometry(wallLength, wallHeight, 9),
    concrete,
    [0, wallHeight / 2 - 2, 0],
  );

  const spillways = isPolavaram ? 12 : 8;
  const openingWidth = 4.7;
  const spacing = 6.1;

  for (let i = 0; i < spillways; i += 1) {
    const x = -(spillways - 1) * spacing / 2 + i * spacing;

    addMesh(
      group,
      new THREE.BoxGeometry(openingWidth, 8.2, 0.45),
      gate,
      [x, 5.2, 4.7],
    );

    addMesh(
      group,
      new THREE.BoxGeometry(0.75, 11.8, 8.8),
      concrete,
      [x - openingWidth / 2 - 0.5, 6.5, 0],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(20, wallHeight * 0.8, 34),
    rock,
    [-wallLength / 2 - 12, wallHeight * 0.3, 0],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(20, wallHeight * 0.8, 34),
    rock,
    [wallLength / 2 + 12, wallHeight * 0.3, 0],
  );
}

function buildArchBridge(group: THREE.Group) {
  const steel = new THREE.MeshStandardMaterial({
    color: 0x8895a3,
    metalness: 0.58,
    roughness: 0.42,
  });

  const deck = new THREE.MeshStandardMaterial({
    color: 0x303840,
    roughness: 0.92,
  });

  const pier = new THREE.MeshStandardMaterial({
    color: 0xaeb8c2,
    roughness: 0.86,
  });

  addWater(group, 180, 80, -3.0);

  const bridgeLength = 125;
  const spans = 6;
  const spanLength = bridgeLength / spans;

  addMesh(
    group,
    new THREE.BoxGeometry(bridgeLength, 1.25, 8.5),
    deck,
    [0, 8.0, 0],
  );

  for (let i = 0; i <= spans; i += 1) {
    const x = -bridgeLength / 2 + i * spanLength;

    addMesh(
      group,
      new THREE.BoxGeometry(2.0, 13.5, 7.2),
      pier,
      [x, 1.5, 0],
    );
  }

  for (let i = 0; i < spans; i += 1) {
    const x0 = -bridgeLength / 2 + i * spanLength;
    const x1 = x0 + spanLength;
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(x0 + 1.3, 8.5, 3.8),
      new THREE.Vector3((x0 + x1) / 2, 20.5, 3.8),
      new THREE.Vector3(x1 - 1.3, 8.5, 3.8),
    );

    const curve2 = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(x0 + 1.3, 8.5, -3.8),
      new THREE.Vector3((x0 + x1) / 2, 20.5, -3.8),
      new THREE.Vector3(x1 - 1.3, 8.5, -3.8),
    );

    addMesh(
      group,
      new THREE.TubeGeometry(curve, 32, 0.38, 8, false),
      steel,
      [0, 0, 0],
    );

    addMesh(
      group,
      new THREE.TubeGeometry(curve2, 32, 0.38, 8, false),
      steel,
      [0, 0, 0],
    );

    for (let h = 1; h <= 4; h += 1) {
      const t = h / 5;
      const point = curve.getPoint(t);
      const yTop = point.y;

      addMesh(
        group,
        new THREE.CylinderGeometry(0.10, 0.10, Math.max(yTop - 8.5, 0.5), 8),
        steel,
        [point.x, (yTop + 8.5) / 2, 3.8],
      );

      addMesh(
        group,
        new THREE.CylinderGeometry(0.10, 0.10, Math.max(yTop - 8.5, 0.5), 8),
        steel,
        [point.x, (yTop + 8.5) / 2, -3.8],
      );
    }
  }
}

function buildFlyover(group: THREE.Group) {
  const concrete = new THREE.MeshStandardMaterial({
    color: 0xaeb8c2,
    roughness: 0.88,
  });

  const deck = new THREE.MeshStandardMaterial({
    color: 0x303840,
    roughness: 0.94,
  });

  const points = [
    new THREE.Vector3(-65, 8, -18),
    new THREE.Vector3(-20, 10, -5),
    new THREE.Vector3(25, 10, 8),
    new THREE.Vector3(65, 9, 22),
  ];

  const curve = new THREE.CatmullRomCurve3(points);
  const road = new THREE.TubeGeometry(curve, 90, 4.2, 12, false);

  addMesh(group, road, deck, [0, 0, 0]);

  for (let i = 1; i < 11; i += 1) {
    const p = curve.getPoint(i / 11);

    addMesh(
      group,
      new THREE.BoxGeometry(2.6, p.y, 2.6),
      concrete,
      [p.x, p.y / 2, p.z],
    );
  }
}

function buildAirport(group: THREE.Group) {
  const runway = new THREE.MeshStandardMaterial({
    color: 0x272d32,
    roughness: 0.95,
  });

  const marking = new THREE.MeshStandardMaterial({
    color: 0xf2f2ea,
    roughness: 0.8,
  });

  const terminal = new THREE.MeshStandardMaterial({
    color: 0x9daab5,
    roughness: 0.62,
    metalness: 0.10,
  });

  const glass = new THREE.MeshStandardMaterial({
    color: 0x5f8fa8,
    roughness: 0.25,
    metalness: 0.15,
  });

  const apron = new THREE.MeshStandardMaterial({
    color: 0x6d747a,
    roughness: 0.95,
  });

  addMesh(
    group,
    new THREE.BoxGeometry(165, 0.35, 16),
    runway,
    [0, 0.2, -18],
  );

  for (let i = -7; i <= 7; i += 1) {
    addMesh(
      group,
      new THREE.BoxGeometry(5.5, 0.05, 0.45),
      marking,
      [i * 10.0, 0.4, -18],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(78, 0.28, 42),
    apron,
    [26, 0.18, 22],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(58, 8.5, 17),
    terminal,
    [32, 4.5, 39],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(49, 3.2, 0.5),
    glass,
    [32, 4.5, 30.25],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(26, 4.0, 12),
    terminal,
    [-12, 2.1, 36],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(6, 10, 6),
    terminal,
    [62, 5.2, 42],
  );

  addMesh(
    group,
    new THREE.CylinderGeometry(1.0, 1.0, 9.5, 16),
    terminal,
    [62, 11.8, 42],
  );
}

function buildTemple(group: THREE.Group) {
  const stone = new THREE.MeshStandardMaterial({
    color: 0xc59b55,
    roughness: 0.88,
  });

  const paleStone = new THREE.MeshStandardMaterial({
    color: 0xd9b66d,
    roughness: 0.86,
  });

  const darkStone = new THREE.MeshStandardMaterial({
    color: 0x8b6a38,
    roughness: 0.94,
  });

  addMesh(
    group,
    new THREE.BoxGeometry(56, 2.0, 45),
    darkStone,
    [0, 1, 0],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(32, 5.0, 28),
    stone,
    [0, 4.4, 3],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(18, 8.0, 16),
    paleStone,
    [0, 10.2, 3],
  );

  const levels = [
    [22, 6.0],
    [18.5, 5.2],
    [15.0, 4.8],
    [12.0, 4.3],
    [9.0, 3.8],
    [6.5, 3.2],
  ];

  let y = 4.0;

  levels.forEach(([size, height], index) => {
    addMesh(
      group,
      new THREE.BoxGeometry(size, height, size * 0.72),
      index % 2 === 0 ? stone : paleStone,
      [0, y + height / 2, -17],
    );

    y += height;
  });

  addMesh(
    group,
    new THREE.SphereGeometry(2.3, 20, 12),
    paleStone,
    [0, y + 1.7, -17],
  );

  for (let x = -18; x <= 18; x += 12) {
    addMesh(
      group,
      new THREE.CylinderGeometry(0.8, 0.8, 5.2, 12),
      darkStone,
      [x, 5.1, 15],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(44, 1.0, 7),
    stone,
    [0, 7.3, 15],
  );
}

function buildGenericInfrastructure(group: THREE.Group) {
  const material = new THREE.MeshStandardMaterial({
    color: 0x8796a5,
    roughness: 0.85,
  });

  addMesh(
    group,
    new THREE.BoxGeometry(54, 12, 24),
    material,
    [0, 6, 0],
  );
}

function buildTwin(
  group: THREE.Group,
  assetCode: string,
  type: string,
  name: string,
): TwinSpec {
  if (assetCode === "AP_DAM_00001") {
    buildPrakasamBarrage(group);

    return {
      title: "Source-linked barrage model",
      fidelity: "L2 SOURCE-BACKED PARAMETRIC TWIN",
      evidence:
        "Geometry uses the source-linked SIMRAS Prakasam dimensions. Visual detailing is parametric rather than survey/BIM reconstruction.",
      dimensions: [
        "Total length: 1,232.92 m",
        "70 gates",
        "Gate width: 12.19 m",
        "Gate height: 3.66 m",
      ],
    };
  }

  if (type === "bridge") {
    if (
      name.toLowerCase().includes("arch") ||
      assetCode === "AP_BR_00001"
    ) {
      buildArchBridge(group);

      return {
        title: "Asset-specific arch bridge twin",
        fidelity: "L1/L2 SOURCE-AWARE VISUAL TWIN",
        evidence:
          "Bridge form is asset-specific. Exact member dimensions require verified engineering drawings/BIM.",
        dimensions: [
          "Arch bridge configuration",
          "Deck + piers + repeated arch spans",
        ],
      };
    }

    buildFlyover(group);

    return {
      title: "Asset-specific flyover twin",
      fidelity: "L1/L2 SOURCE-AWARE VISUAL TWIN",
      evidence:
        "Flyover form is asset-specific. Exact alignment/member dimensions require verified engineering drawings/BIM.",
      dimensions: [
        "Elevated deck",
        "Repeated pier supports",
      ],
    };
  }

  if (type === "airport") {
    buildAirport(group);

    return {
      title: "Airport infrastructure twin",
      fidelity: "L1/L2 SOURCE-AWARE VISUAL TWIN",
      evidence:
        "Airport type and site identity are real; exact terminal/runway geometry requires authoritative airport drawings or survey data.",
      dimensions: [
        "Runway",
        "Taxiway/apron",
        "Terminal complex",
        "Control/service block",
      ],
    };
  }

  if (type === "temple") {
    buildTemple(group);

    return {
      title: "Temple complex visual twin",
      fidelity: "L1 ASSET-SPECIFIC VISUAL TWIN",
      evidence:
        "Temple identity is real. Gopuram/mandapa geometry is an asset-type visual representation until verified architectural survey/photogrammetry is available.",
      dimensions: [
        "Gopuram tower",
        "Mandapa",
        "Sanctum complex",
        "Raised plinth",
      ],
    };
  }

  if (type === "barrage") {
    buildPrakasamBarrage(group);

    return {
      title: "Barrage engineering visual twin",
      fidelity: "L1/L2 SOURCE-AWARE PARAMETRIC TWIN",
      evidence:
        "Barrage form is source-aware. Only Prakasam currently uses the linked gate/length values in this renderer.",
      dimensions: [
        "Repeated gate bays",
        "Piers",
        "Road deck",
        "River channel",
      ],
    };
  }

  if (type === "dam") {
    buildDam(group, name);

    return {
      title: "Dam engineering visual twin",
      fidelity: "L1/L2 SOURCE-AWARE PARAMETRIC TWIN",
      evidence:
        "Dam form is asset-specific by type/name. Exact dimensions require linked official dam records, drawings or survey data.",
      dimensions: [
        "Dam wall",
        "Spillway gates",
        "Abutments",
        "Reservoir/water side",
      ],
    };
  }

  buildGenericInfrastructure(group);

  return {
    title: "Infrastructure visual twin",
    fidelity: "L1 VISUAL TWIN",
    evidence:
      "A generic infrastructure form is used because no verified type-specific engineering geometry is available.",
    dimensions: ["Verified geometry not available"],
  };
}

/*
 * SIMRAS_V22_ENGINEERING_TWIN
 *
 * One clean Three.js twin.
 * Zero map/tile dependencies.
 * Zero OSM2World GLB dependency.
 * Zero duplicate viewer.
 */
export default function RealityTwinAssetViewer({
  assetCode,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [sceneReady, setSceneReady] = useState(false);
  const [spec, setSpec] = useState<TwinSpec | null>(null);

  useEffect(() => {
    let mounted = true;

    fetch("/reality-twin/assets.json", {
      cache: "no-store",
    })
      .then((response) => (response.ok ? response.json() : []))
      .then((rows) => {
        if (!mounted) return;
        setAssets(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!mounted) return;
        setAssets([]);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const selectedAsset = useMemo(
    () =>
      assets.find(
        (asset) => clean(asset.asset_code, "") === assetCode,
      ) ?? null,
    [assets, assetCode],
  );

  const name = field(
    selectedAsset,
    "name",
    "asset_name",
  );

  const district = field(
    selectedAsset,
    "district",
  );

  const type = inferType(
    assetCode ?? "",
    selectedAsset,
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !assetCode) return;

    setSceneReady(false);
    setSpec(null);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07111f);
    scene.fog = new THREE.Fog(0x07111f, 210, 430);

    const camera = new THREE.PerspectiveCamera(
      42,
      1,
      0.05,
      1500,
    );

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
    });

    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio || 1, 2),
    );

    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    host.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(
      camera,
      renderer.domElement,
    );

    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.screenSpacePanning = true;
    controls.maxPolarAngle = Math.PI * 0.49;

    scene.add(
      new THREE.HemisphereLight(
        0xd8efff,
        0x283743,
        2.0,
      ),
    );

    const sun = new THREE.DirectionalLight(
      0xffffff,
      4.2,
    );
    sun.position.set(120, 170, 95);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    scene.add(sun);

    const fill = new THREE.DirectionalLight(
      0x8dc8ff,
      1.1,
    );
    fill.position.set(-110, 70, -80);
    scene.add(fill);

    const group = new THREE.Group();
    scene.add(group);

    const groundMaterial = new THREE.MeshStandardMaterial({
      color: 0x142331,
      roughness: 0.98,
    });

    addMesh(
      group,
      new THREE.BoxGeometry(230, 1.2, 120),
      groundMaterial,
      [0, -3.3, 0],
    );

    const builtSpec = buildTwin(
      group,
      assetCode,
      type,
      name,
    );

    setSpec(builtSpec);

    const bounds = new THREE.Box3().setFromObject(group);
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());

    group.position.sub(center);

    const maxDimension = Math.max(
      size.x,
      size.y,
      size.z,
      1,
    );

    const distance = maxDimension * 0.95;

    camera.near = Math.max(maxDimension / 2000, 0.05);
    camera.far = Math.max(maxDimension * 18, 1000);

    camera.position.set(
      distance,
      distance * 0.62,
      distance * 0.78,
    );

    camera.updateProjectionMatrix();

    controls.target.set(0, 0, 0);
    controls.minDistance = maxDimension * 0.18;
    controls.maxDistance = maxDimension * 5.5;
    controls.update();

    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);

      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    let frame = 0;
    let disposed = false;

    const animate = () => {
      if (disposed) return;

      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };

    animate();
    setSceneReady(true);

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();

      group.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return;

        child.geometry?.dispose();

        const materials = Array.isArray(child.material)
          ? child.material
          : [child.material];

        materials.forEach((material) => material?.dispose());
      });

      renderer.dispose();
      host.replaceChildren();
    };
  }, [assetCode, type, name]);

  return (
    <div
      data-simras-reality-view="V22_ENGINEERING_TWIN"
      style={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div
        style={{
          position: "relative",
          width: "100%",
          height: "72vh",
          minHeight: 620,
          maxHeight: 820,
          overflow: "hidden",
          border: "1px solid rgba(148,163,184,.18)",
          borderRadius: 12,
          background: "#07111f",
        }}
      >
        <div
          ref={hostRef}
          style={{
            position: "absolute",
            inset: 0,
          }}
        />

        {!sceneReady && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "grid",
              placeItems: "center",
              color: "#cbd5e1",
              background: "#07111f",
              zIndex: 2,
            }}
          >
            Building engineering twin...
          </div>
        )}

        <div
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            zIndex: 5,
            width: "min(470px, calc(100% - 28px))",
            padding: "12px 14px",
            border: "1px solid rgba(255,255,255,.12)",
            borderRadius: 10,
            background: "rgba(3,12,23,.88)",
            color: "#ffffff",
            backdropFilter: "blur(8px)",
            boxShadow: "0 12px 28px rgba(0,0,0,.28)",
          }}
        >
          <div
            style={{
              color: "#67e8f9",
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: ".14em",
            }}
          >
            SIMRAS / ENGINEERING DIGITAL TWIN
          </div>

          <div
            style={{
              marginTop: 7,
              fontSize: 17,
              fontWeight: 750,
            }}
          >
            {name}
          </div>

          <div
            style={{
              marginTop: 3,
              color: "#cbd5e1",
              fontSize: 11,
            }}
          >
            {clean(assetCode)} / {type} / {district}
          </div>

          {spec && (
            <>
              <div
                style={{
                  marginTop: 9,
                  color: "#86efac",
                  fontSize: 10,
                  fontWeight: 700,
                }}
              >
                {spec.title}
              </div>

              <div
                style={{
                  marginTop: 4,
                  color: "#fde68a",
                  fontSize: 10,
                  lineHeight: 1.45,
                }}
              >
                {spec.fidelity}
              </div>
            </>
          )}
        </div>

        {spec && spec.dimensions.length > 0 && (
          <div
            style={{
              position: "absolute",
              right: 14,
              top: 14,
              zIndex: 5,
              width: "min(300px, calc(100% - 28px))",
              padding: "11px 13px",
              border: "1px solid rgba(255,255,255,.12)",
              borderRadius: 10,
              background: "rgba(3,12,23,.84)",
              color: "#dbeafe",
              backdropFilter: "blur(8px)",
            }}
          >
            <div
              style={{
                color: "#93c5fd",
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: ".10em",
              }}
            >
              SOURCE-LINKED DETAILS
            </div>

            <div
              style={{
                marginTop: 7,
                display: "grid",
                gap: 5,
              }}
            >
              {spec.dimensions.map((item) => (
                <div
                  key={item}
                  style={{
                    fontSize: 11,
                    color: "#e2e8f0",
                  }}
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {spec && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(160px, 1fr) minmax(220px, 2fr)",
            gap: 12,
            padding: 13,
            border: "1px solid rgba(148,163,184,.18)",
            borderRadius: 10,
            background: "rgba(2,10,19,.46)",
          }}
        >
          <div>
            <div
              style={{
                color: "#94a3b8",
                fontSize: 10,
              }}
            >
              Fidelity
            </div>

            <div
              style={{
                marginTop: 4,
                fontSize: 12,
                fontWeight: 650,
              }}
            >
              {spec.fidelity}
            </div>
          </div>

          <div>
            <div
              style={{
                color: "#94a3b8",
                fontSize: 10,
              }}
            >
              Evidence note
            </div>

            <div
              style={{
                marginTop: 4,
                fontSize: 11,
                lineHeight: 1.5,
                color: "#cbd5e1",
              }}
            >
              {spec.evidence}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}