import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import * as THREE from "three";

import { OrbitControls } from
  "three/examples/jsm/controls/OrbitControls.js";


type JsonRecord = Record<string, unknown>;

interface BridgePayload {
  asset?: JsonRecord;
  profile?: unknown;
  engineering?: unknown;
  report?: unknown;
}

interface Props {
  assetCode?: string;
}


function parseRecord(value: unknown): JsonRecord {
  if (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  ) {
    return value as JsonRecord;
  }

  if (typeof value === "string") {
    try {
      const parsed: unknown = JSON.parse(value);

      if (
        typeof parsed === "object" &&
        parsed !== null &&
        !Array.isArray(parsed)
      ) {
        return parsed as JsonRecord;
      }
    } catch {
      return {};
    }
  }

  return {};
}


function findDeep(
  value: unknown,
  names: string[],
): unknown {
  const keys = new Set(
    names.map((name) => name.toLowerCase()),
  );

  const visit = (item: unknown): unknown => {
    if (
      item === null ||
      item === undefined
    ) {
      return undefined;
    }

    if (typeof item === "string") {
      const trimmed = item.trim();

      if (
        trimmed.startsWith("{") ||
        trimmed.startsWith("[")
      ) {
        try {
          return visit(JSON.parse(trimmed));
        } catch {
          return undefined;
        }
      }

      return undefined;
    }

    if (Array.isArray(item)) {
      for (const child of item) {
        const result = visit(child);

        if (result !== undefined) {
          return result;
        }
      }

      return undefined;
    }

    if (typeof item === "object") {
      const object = item as JsonRecord;

      for (const [key, child] of Object.entries(object)) {
        if (keys.has(key.toLowerCase())) {
          return child;
        }
      }

      for (const child of Object.values(object)) {
        const result = visit(child);

        if (result !== undefined) {
          return result;
        }
      }
    }

    return undefined;
  };

  return visit(value);
}


function getNumber(
  value: unknown,
  names: string[],
): number | undefined {
  const raw = findDeep(value, names);

  if (
    raw === null ||
    raw === undefined
  ) {
    return undefined;
  }

  const number = Number(raw);

  return Number.isFinite(number)
    ? number
    : undefined;
}


function getText(
  value: unknown,
  names: string[],
): string | undefined {
  const raw = findDeep(value, names);

  if (
    raw === null ||
    raw === undefined
  ) {
    return undefined;
  }

  const text = String(raw).trim();

  return text.length > 0
    ? text
    : undefined;
}


function extractAlignment(
  value: unknown,
): number[][] | undefined {
  let geometry = findDeep(
    value,
    [
      "actual_geometry",
      "alignment_geometry",
      "osm_geometry",
      "geometry_geojson",
    ],
  );

  if (typeof geometry === "string") {
    try {
      geometry = JSON.parse(geometry);
    } catch {
      return undefined;
    }
  }

  if (
    typeof geometry !== "object" ||
    geometry === null
  ) {
    return undefined;
  }

  const object = geometry as JsonRecord;

  if (object.type === "Feature") {
    return extractAlignment(object.geometry);
  }

  if (
    object.type === "LineString" &&
    Array.isArray(object.coordinates)
  ) {
    const output: number[][] = [];

    for (const coordinate of object.coordinates) {
      if (
        Array.isArray(coordinate) &&
        coordinate.length >= 2
      ) {
        const x = Number(coordinate[0]);
        const y = Number(coordinate[1]);

        if (
          Number.isFinite(x) &&
          Number.isFinite(y)
        ) {
          output.push([x, y]);
        }
      }
    }

    return output.length >= 2
      ? output
      : undefined;
  }

  if (
    object.type === "MultiLineString" &&
    Array.isArray(object.coordinates)
  ) {
    let best: number[][] = [];

    for (const rawLine of object.coordinates) {
      if (!Array.isArray(rawLine)) {
        continue;
      }

      const line: number[][] = [];

      for (const coordinate of rawLine) {
        if (
          Array.isArray(coordinate) &&
          coordinate.length >= 2
        ) {
          const x = Number(coordinate[0]);
          const y = Number(coordinate[1]);

          if (
            Number.isFinite(x) &&
            Number.isFinite(y)
          ) {
            line.push([x, y]);
          }
        }
      }

      if (line.length > best.length) {
        best = line;
      }
    }

    return best.length >= 2
      ? best
      : undefined;
  }

  return undefined;
}


function pathLengths(
  points: THREE.Vector3[],
): number[] {
  const output = [0];

  for (let i = 1; i < points.length; i += 1) {
    output.push(
      output[i - 1] +
      points[i].distanceTo(points[i - 1]),
    );
  }

  return output;
}


function pointAt(
  points: THREE.Vector3[],
  fraction: number,
): THREE.Vector3 {
  if (points.length === 1) {
    return points[0].clone();
  }

  const lengths = pathLengths(points);
  const total = lengths[lengths.length - 1];

  const target =
    THREE.MathUtils.clamp(fraction, 0, 1) *
    total;

  for (let i = 1; i < lengths.length; i += 1) {
    if (lengths[i] < target) {
      continue;
    }

    const startLength = lengths[i - 1];
    const segmentLength =
      lengths[i] - startLength;

    const local =
      segmentLength > 0
        ? (target - startLength) /
          segmentLength
        : 0;

    return new THREE.Vector3().lerpVectors(
      points[i - 1],
      points[i],
      local,
    );
  }

  return points[points.length - 1].clone();
}


function tangentAt(
  points: THREE.Vector3[],
  fraction: number,
): THREE.Vector3 {
  const before = pointAt(
    points,
    Math.max(0, fraction - 0.015),
  );

  const after = pointAt(
    points,
    Math.min(1, fraction + 0.015),
  );

  return after.sub(before).normalize();
}


function createDisplayPath(
  coordinates?: number[][],
): THREE.Vector3[] {
  if (
    !coordinates ||
    coordinates.length < 2
  ) {
    return [
      new THREE.Vector3(-58, 0, 0),
      new THREE.Vector3(58, 0, 0),
    ];
  }

  const sampled: number[][] = [];

  const sampleCount = Math.min(
    100,
    coordinates.length,
  );

  for (let i = 0; i < sampleCount; i += 1) {
    const index = Math.round(
      i *
      (coordinates.length - 1) /
      Math.max(1, sampleCount - 1),
    );

    sampled.push(coordinates[index]);
  }

  const first = sampled[0];

  const geographic = sampled.every(
    ([x, y]) =>
      Math.abs(x) <= 180 &&
      Math.abs(y) <= 90,
  );

  const raw: THREE.Vector3[] = [];

  if (geographic) {
    const lon0 = first[0];
    const lat0 = first[1];

    const cosLat = Math.cos(
      THREE.MathUtils.degToRad(lat0),
    );

    for (const [lon, lat] of sampled) {
      raw.push(
        new THREE.Vector3(
          (lon - lon0) *
            111320 *
            cosLat,
          0,
          -(lat - lat0) * 110540,
        ),
      );
    }
  } else {
    for (const [x, y] of sampled) {
      raw.push(
        new THREE.Vector3(
          x - first[0],
          0,
          -(y - first[1]),
        ),
      );
    }
  }

  const lengths = pathLengths(raw);
  const total = lengths[lengths.length - 1];

  if (total <= 0.001) {
    return [
      new THREE.Vector3(-58, 0, 0),
      new THREE.Vector3(58, 0, 0),
    ];
  }

  const displayScale = 116 / total;

  const result = raw.map(
    (point) =>
      point.clone().multiplyScalar(displayScale),
  );

  const bounds = new THREE.Box3()
    .setFromPoints(result);

  const center = bounds.getCenter(
    new THREE.Vector3(),
  );

  for (const point of result) {
    point.sub(center);
  }

  return result;
}


function addBoxBetween(
  group: THREE.Group,
  start: THREE.Vector3,
  end: THREE.Vector3,
  width: number,
  height: number,
  y: number,
  material: THREE.Material,
): void {
  const dx = end.x - start.x;
  const dz = end.z - start.z;

  const length = Math.sqrt(
    dx * dx + dz * dz,
  );

  if (length <= 0.001) {
    return;
  }

  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(
      length,
      height,
      width,
    ),
    material,
  );

  mesh.position.set(
    (start.x + end.x) / 2,
    y,
    (start.z + end.z) / 2,
  );

  mesh.rotation.y = -Math.atan2(
    dz,
    dx,
  );

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);
}


function offsetPoints(
  points: THREE.Vector3[],
  distance: number,
  y: number,
): THREE.Vector3[] {
  return points.map((point, index) => {
    const fraction =
      points.length === 1
        ? 0
        : index / (points.length - 1);

    const tangent = tangentAt(
      points,
      fraction,
    );

    const perpendicular =
      new THREE.Vector3(
        -tangent.z,
        0,
        tangent.x,
      ).normalize();

    return point
      .clone()
      .addScaledVector(
        perpendicular,
        distance,
      )
      .setY(y);
  });
}


function addTube(
  group: THREE.Group,
  points: THREE.Vector3[],
  radius: number,
  material: THREE.Material,
): void {
  if (points.length < 2) {
    return;
  }

  const curve = new THREE.CatmullRomCurve3(
    points,
  );

  const geometry = new THREE.TubeGeometry(
    curve,
    Math.max(24, points.length * 2),
    radius,
    8,
    false,
  );

  const mesh = new THREE.Mesh(
    geometry,
    material,
  );

  mesh.castShadow = true;

  group.add(mesh);
}


function positionHtmlLabel(
  element: HTMLDivElement | null,
  point: THREE.Vector3,
  camera: THREE.Camera,
  width: number,
  height: number,
): void {
  if (!element) {
    return;
  }

  const projected = point.clone().project(camera);

  const x =
    (projected.x * 0.5 + 0.5) *
    width;

  const y =
    (-projected.y * 0.5 + 0.5) *
    height;

  element.style.transform =
    `translate(-50%, -50%) translate(${x}px, ${y}px)`;

  element.style.opacity =
    projected.z >= -1 &&
    projected.z <= 1
      ? "1"
      : "0";
}


export default function BridgeEngineeringViewer({
  assetCode,
}: Props) {
  const canvasHostRef =
    useRef<HTMLDivElement>(null);

  const lengthLabelRef =
    useRef<HTMLDivElement>(null);

  const widthLabelRef =
    useRef<HTMLDivElement>(null);

  const pierLabelRef =
    useRef<HTMLDivElement>(null);

  const spanLabelRef =
    useRef<HTMLDivElement>(null);

  const [payload, setPayload] =
    useState<BridgePayload>();

  const [error, setError] =
    useState<string>();

  const [showDimensions, setShowDimensions] =
    useState(true);


  useEffect(() => {
    if (!assetCode) {
      return;
    }

    let cancelled = false;

    setPayload(undefined);
    setError(undefined);

    const base = String(
      import.meta.env.VITE_API_BASE_URL ?? "",
    ).replace(/\/$/, "");

    fetch(
      `${base}/assets/${encodeURIComponent(
        assetCode,
      )}/bridge-profile`,
      {
        cache: "no-store",
      },
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `${response.status} ${await response.text()}`,
          );
        }

        return response.json() as Promise<BridgePayload>;
      })
      .then((data) => {
        if (!cancelled) {
          setPayload(data);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof Error
              ? cause.message
              : String(cause),
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [assetCode]);


  const data = useMemo(
    () => ({
      profile: parseRecord(payload?.profile),
      engineering: parseRecord(
        payload?.engineering,
      ),
      report: parseRecord(payload?.report),
    }),
    [payload],
  );


  const isGodavari =
    assetCode === "AP_BR_00001";

  const isKanaka =
    assetCode === "AP_BR_00002";


  const lengthM =
    getNumber(
      data,
      [
        "length_m",
        "verified_length_m",
        "total_length_m",
        "bridge_length_m",
      ],
    ) ??
    (
      isGodavari
        ? 2745
        : isKanaka
          ? 2600
          : undefined
    );


  const widthM =
    getNumber(
      data,
      [
        "width_m",
        "verified_width_m",
        "deck_width_m",
      ],
    ) ??
    (
      isKanaka
        ? 23.7744
        : undefined
    );


  const pierCount =
    getNumber(
      data,
      [
        "pier_count",
        "number_of_piers",
        "piers",
      ],
    ) ??
    (
      isGodavari
        ? 28
        : isKanaka
          ? 45
          : undefined
    );


  const spanCount =
    getNumber(
      data,
      [
        "span_count",
        "number_of_spans",
        "spans",
      ],
    ) ??
    (
      isGodavari
        ? 28
        : undefined
    );


  const geometrySource =
    getText(
      data,
      [
        "geometry_source",
      ],
    );


  const rawAlignment =
    extractAlignment(data.profile);


  useEffect(() => {
    const host = canvasHostRef.current;

    if (
      !host ||
      !assetCode ||
      !payload
    ) {
      return;
    }

    host.innerHTML = "";

    const scene = new THREE.Scene();

    scene.background =
      new THREE.Color(0x06121e);

    scene.fog = new THREE.Fog(
      0x06121e,
      160,
      300,
    );


    const camera =
      new THREE.PerspectiveCamera(
        45,
        1,
        0.1,
        1000,
      );


    const renderer =
      new THREE.WebGLRenderer({
        antialias: true,
      });

    renderer.setPixelRatio(
      Math.min(
        window.devicePixelRatio,
        2,
      ),
    );

    renderer.shadowMap.enabled = true;

    host.appendChild(
      renderer.domElement,
    );


    const controls =
      new OrbitControls(
        camera,
        renderer.domElement,
      );

    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 30;
    controls.maxDistance = 260;


    scene.add(
      new THREE.HemisphereLight(
        0xc9f0ff,
        0x172531,
        2.7,
      ),
    );


    const sun =
      new THREE.DirectionalLight(
        0xffffff,
        4.8,
      );

    sun.position.set(
      45,
      75,
      35,
    );

    sun.castShadow = true;

    scene.add(sun);


    const fill =
      new THREE.DirectionalLight(
        0x49c9ff,
        1.7,
      );

    fill.position.set(
      -50,
      25,
      -35,
    );

    scene.add(fill);


    const grid =
      new THREE.GridHelper(
        240,
        48,
        0x1a7495,
        0x10384d,
      );

    grid.position.y = -9.2;

    scene.add(grid);


    const water =
      new THREE.Mesh(
        new THREE.PlaneGeometry(
          230,
          82,
        ),
        new THREE.MeshStandardMaterial({
          color: 0x0b4057,
          roughness: 0.3,
          metalness: 0.2,
          transparent: true,
          opacity: 0.7,
        }),
      );

    water.rotation.x = -Math.PI / 2;
    water.position.y = -9;

    scene.add(water);


    const path = createDisplayPath(
      rawAlignment,
    );


    const bridge =
      new THREE.Group();

    scene.add(bridge);


    const actualWidth =
      widthM ?? 20;

    const deckWidth =
      THREE.MathUtils.clamp(
        actualWidth / 4,
        4.6,
        7.5,
      );


    const concrete =
      new THREE.MeshStandardMaterial({
        color: 0xc4ccd2,
        roughness: 0.72,
        metalness: 0.05,
      });


    const deckTop =
      new THREE.MeshStandardMaterial({
        color: isGodavari
          ? 0x4c5358
          : 0x303b43,
        roughness: 0.88,
      });


    const steel =
      new THREE.MeshStandardMaterial({
        color: 0x63dbef,
        roughness: 0.3,
        metalness: 0.55,
      });


    for (
      let index = 1;
      index < path.length;
      index += 1
    ) {
      addBoxBetween(
        bridge,
        path[index - 1],
        path[index],
        deckWidth,
        1.35,
        0,
        concrete,
      );

      addBoxBetween(
        bridge,
        path[index - 1],
        path[index],
        deckWidth * 0.88,
        0.16,
        0.76,
        deckTop,
      );
    }


    const leftBarrier = offsetPoints(
      path,
      deckWidth * 0.47,
      1.35,
    );

    const rightBarrier = offsetPoints(
      path,
      -deckWidth * 0.47,
      1.35,
    );

    addTube(
      bridge,
      leftBarrier,
      0.13,
      steel,
    );

    addTube(
      bridge,
      rightBarrier,
      0.13,
      steel,
    );


    if (isGodavari) {
      const railLeft = offsetPoints(
        path,
        0.8,
        1.0,
      );

      const railRight = offsetPoints(
        path,
        -0.8,
        1.0,
      );

      addTube(
        bridge,
        railLeft,
        0.09,
        steel,
      );

      addTube(
        bridge,
        railRight,
        0.09,
        steel,
      );
    }


    const verifiedPiers =
      pierCount !== undefined;

    const visualPierCount =
      verifiedPiers
        ? THREE.MathUtils.clamp(
            Math.round(pierCount),
            2,
            60,
          )
        : 10;


    for (
      let index = 1;
      index <= visualPierCount;
      index += 1
    ) {
      const fraction =
        index /
        (visualPierCount + 1);

      const position = pointAt(
        path,
        fraction,
      );

      const pier =
        new THREE.Mesh(
          new THREE.BoxGeometry(
            1.15,
            8.0,
            Math.max(
              1.5,
              deckWidth * 0.38,
            ),
          ),
          concrete,
        );

      pier.position.set(
        position.x,
        -4.7,
        position.z,
      );

      pier.castShadow = true;
      pier.receiveShadow = true;

      bridge.add(pier);


      const cap =
        new THREE.Mesh(
          new THREE.BoxGeometry(
            2.8,
            0.55,
            deckWidth * 0.92,
          ),
          concrete,
        );

      cap.position.set(
        position.x,
        -1.0,
        position.z,
      );

      bridge.add(cap);
    }


    if (isGodavari) {
      const arches =
        Math.max(
          1,
          Math.min(
            28,
            Math.round(
              spanCount ?? 28,
            ),
          ),
        );

      for (
        let index = 0;
        index < arches;
        index += 1
      ) {
        const startFraction =
          index / arches;

        const endFraction =
          (index + 1) / arches;

        const middleFraction =
          (startFraction +
            endFraction) /
          2;

        const start = pointAt(
          path,
          startFraction,
        );

        const middle = pointAt(
          path,
          middleFraction,
        );

        const end = pointAt(
          path,
          endFraction,
        );

        const tangent = tangentAt(
          path,
          middleFraction,
        );

        const sideVector =
          new THREE.Vector3(
            -tangent.z,
            0,
            tangent.x,
          ).normalize();

        for (const side of [-1, 1]) {
          const offset =
            side *
            deckWidth *
            0.42;

          const a = start
            .clone()
            .addScaledVector(
              sideVector,
              offset,
            );

          a.y = 1.1;

          const b = middle
            .clone()
            .addScaledVector(
              sideVector,
              offset,
            );

          b.y = 6.2;

          const c = end
            .clone()
            .addScaledVector(
              sideVector,
              offset,
            );

          c.y = 1.1;

          const curve =
            new THREE.QuadraticBezierCurve3(
              a,
              b,
              c,
            );

          const arch =
            new THREE.Mesh(
              new THREE.TubeGeometry(
                curve,
                12,
                0.23,
                7,
                false,
              ),
              steel,
            );

          arch.castShadow = true;

          bridge.add(arch);
        }
      }
    }


    if (isKanaka) {
      const girderLeft =
        offsetPoints(
          path,
          deckWidth * 0.28,
          -1.0,
        );

      const girderRight =
        offsetPoints(
          path,
          -deckWidth * 0.28,
          -1.0,
        );

      addTube(
        bridge,
        girderLeft,
        0.3,
        concrete,
      );

      addTube(
        bridge,
        girderRight,
        0.3,
        concrete,
      );
    }


    const dimensions =
      new THREE.Group();

    dimensions.visible =
      showDimensions;

    scene.add(dimensions);


    const dimensionMaterial =
      new THREE.LineBasicMaterial({
        color: 0x67e8f9,
      });


    const dimensionPath =
      path.map((point) => {
        const copy = point.clone();
        copy.y = 8.0;
        return copy;
      });


    dimensions.add(
      new THREE.Line(
        new THREE.BufferGeometry()
          .setFromPoints(
            dimensionPath,
          ),
        dimensionMaterial,
      ),
    );


    const midpoint = pointAt(
      path,
      0.5,
    );

    const tangent = tangentAt(
      path,
      0.5,
    );

    const perpendicular =
      new THREE.Vector3(
        -tangent.z,
        0,
        tangent.x,
      ).normalize();


    const widthStart =
      midpoint
        .clone()
        .addScaledVector(
          perpendicular,
          -deckWidth / 2,
        );

    widthStart.y = 3;


    const widthEnd =
      midpoint
        .clone()
        .addScaledVector(
          perpendicular,
          deckWidth / 2,
        );

    widthEnd.y = 3;


    dimensions.add(
      new THREE.Line(
        new THREE.BufferGeometry()
          .setFromPoints([
            widthStart,
            widthEnd,
          ]),
        dimensionMaterial,
      ),
    );


    const lengthAnchor =
      pointAt(
        path,
        0.55,
      );

    lengthAnchor.y = 10;


    const widthAnchor =
      midpoint
        .clone()
        .addScaledVector(
          perpendicular,
          deckWidth + 5,
        );

    widthAnchor.y = 4;


    const pierAnchor =
      pointAt(
        path,
        0.24,
      );

    pierAnchor.y = -3;


    const spanAnchor =
      pointAt(
        path,
        0.78,
      );

    spanAnchor.y = 6;


    const bounds =
      new THREE.Box3()
        .setFromObject(bridge);

    const size =
      bounds.getSize(
        new THREE.Vector3(),
      );

    const center =
      bounds.getCenter(
        new THREE.Vector3(),
      );

    const maxHorizontal =
      Math.max(
        size.x,
        size.z,
        65,
      );


    camera.position.set(
      center.x +
        maxHorizontal * 0.58,

      42,

      center.z +
        maxHorizontal * 0.72,
    );

    controls.target.copy(center);


    const resize = () => {
      const width = Math.max(
        1,
        host.clientWidth,
      );

      const height = Math.max(
        1,
        host.clientHeight,
      );

      renderer.setSize(
        width,
        height,
        false,
      );

      camera.aspect =
        width / height;

      camera.updateProjectionMatrix();
    };


    resize();

    window.addEventListener(
      "resize",
      resize,
    );


    let frame = 0;

    const animate = () => {
      frame = requestAnimationFrame(
        animate,
      );

      controls.update();

      renderer.render(
        scene,
        camera,
      );

      if (showDimensions) {
        const width =
          host.clientWidth;

        const height =
          host.clientHeight;

        positionHtmlLabel(
          lengthLabelRef.current,
          lengthAnchor,
          camera,
          width,
          height,
        );

        positionHtmlLabel(
          widthLabelRef.current,
          widthAnchor,
          camera,
          width,
          height,
        );

        positionHtmlLabel(
          pierLabelRef.current,
          pierAnchor,
          camera,
          width,
          height,
        );

        positionHtmlLabel(
          spanLabelRef.current,
          spanAnchor,
          camera,
          width,
          height,
        );
      }
    };


    animate();


    return () => {
      cancelAnimationFrame(frame);

      window.removeEventListener(
        "resize",
        resize,
      );

      controls.dispose();

      scene.traverse((object) => {
        const mesh =
          object as THREE.Mesh;

        if (mesh.geometry) {
          mesh.geometry.dispose();
        }

        if (mesh.material) {
          if (Array.isArray(mesh.material)) {
            for (const material of mesh.material) {
              material.dispose();
            }
          } else {
            mesh.material.dispose();
          }
        }
      });

      renderer.dispose();

      if (
        renderer.domElement.parentElement ===
        host
      ) {
        host.removeChild(
          renderer.domElement,
        );
      }
    };
  }, [
    assetCode,
    payload,
    rawAlignment,
    widthM,
    pierCount,
    spanCount,
    showDimensions,
    isGodavari,
    isKanaka,
  ]);


  const asset = parseRecord(
    payload?.asset,
  );

  const assetName =
    String(
      asset.name ??
      (
        isGodavari
          ? "Godavari Arch Bridge"
          : isKanaka
            ? "Kanaka Durga Flyover"
            : "Bridge"
      ),
    );

  const district =
    String(
      asset.district ??
      "District unavailable",
    );


  const labelStyle = {
    position: "absolute" as const,
    padding: "7px 11px",
    border: "1px solid #67e8f9",
    borderRadius: "7px",
    background:
      "rgba(2, 12, 22, 0.94)",
    color: "#ecfbff",
    fontWeight: 700,
    fontSize: "14px",
    whiteSpace: "nowrap" as const,
    pointerEvents: "none" as const,
    zIndex: 15,
  };


  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "680px",
        minHeight: "620px",
        overflow: "hidden",
        background: "#06121e",
        borderRadius: "12px",
      }}
    >
      <div
        ref={canvasHostRef}
        style={{
          position: "absolute",
          inset: 0,
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 18,
          left: 18,
          zIndex: 20,
          width: 390,
          padding: "15px 17px",
          border:
            "1px solid rgba(103,232,249,.25)",
          borderRadius: 10,
          background:
            "rgba(2,12,22,.92)",
        }}
      >
        <div
          style={{
            color: "#67e8f9",
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: 1,
          }}
        >
          SIMRAS / BRIDGE ENGINEERING DIGITAL TWIN
        </div>

        <div
          style={{
            marginTop: 7,
            color: "#ffffff",
            fontSize: 21,
            fontWeight: 800,
          }}
        >
          {assetName}
        </div>

        <div
          style={{
            marginTop: 4,
            color: "#b6c7d3",
            fontSize: 12,
          }}
        >
          {assetCode} / {district}
        </div>

        <div
          style={{
            marginTop: 9,
            color: rawAlignment
              ? "#5ee6b1"
              : "#f4d86a",
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          {rawAlignment
            ? "REAL OSM ALIGNMENT + ENGINEERING DIMENSIONS"
            : "ENGINEERING PROCEDURAL ALIGNMENT · NO SAFE OSM MATCH"}
        </div>

        {geometrySource && (
          <div
            style={{
              marginTop: 5,
              color: "#8ea5b5",
              fontSize: 11,
            }}
          >
            Geometry source: {geometrySource}
          </div>
        )}

        {widthM === undefined && (
          <div
            style={{
              marginTop: 5,
              color: "#8ea5b5",
              fontSize: 11,
            }}
          >
            Width is unknown; display width is render-only.
          </div>
        )}
      </div>


      <button
        type="button"
        onClick={() =>
          setShowDimensions(
            (current) => !current,
          )
        }
        style={{
          position: "absolute",
          top: 18,
          right: 18,
          zIndex: 25,
          padding: "10px 15px",
          border:
            "1px solid #38bdf8",
          borderRadius: 8,
          background:
            "rgba(2,12,22,.94)",
          color: "white",
          cursor: "pointer",
          fontWeight: 700,
        }}
      >
        {showDimensions
          ? "Hide dimensions"
          : "Show dimensions"}
      </button>


      {showDimensions && (
        <>
          <div
            ref={lengthLabelRef}
            style={labelStyle}
          >
            Length:{" "}
            {lengthM !== undefined
              ? `${lengthM.toLocaleString()} m`
              : "UNKNOWN"}
          </div>

          <div
            ref={widthLabelRef}
            style={labelStyle}
          >
            Width:{" "}
            {widthM !== undefined
              ? `${widthM.toLocaleString()} m`
              : "UNKNOWN"}
          </div>

          <div
            ref={pierLabelRef}
            style={labelStyle}
          >
            Piers:{" "}
            {pierCount !== undefined
              ? Math.round(
                  pierCount,
                ).toLocaleString()
              : "UNKNOWN"}
          </div>

          <div
            ref={spanLabelRef}
            style={labelStyle}
          >
            Spans:{" "}
            {spanCount !== undefined
              ? Math.round(
                  spanCount,
                ).toLocaleString()
              : "UNKNOWN"}
          </div>
        </>
      )}


      {!payload && !error && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            color: "#bcd0dc",
            zIndex: 30,
          }}
        >
          Building bridge engineering twin...
        </div>
      )}


      {error && (
        <div
          style={{
            position: "absolute",
            left: 20,
            right: 20,
            bottom: 20,
            zIndex: 30,
            padding: 12,
            border:
              "1px solid #ef646b",
            borderRadius: 8,
            background:
              "rgba(45,8,12,.94)",
            color: "#ffd7da",
          }}
        >
          Bridge profile error: {error}
        </div>
      )}
    </div>
  );
}