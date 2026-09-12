import * as THREE from "three";
import { getDamBarrageTwinProfile } from "./damBarrageTwinRegistry";

function addMesh(
  group: THREE.Group,
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  position: [number, number, number],
) {
  const mesh = new THREE.Mesh(geometry, material);

  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);

  return mesh;
}

function addWater(
  group: THREE.Group,
  width: number,
  depth: number,
  y: number,
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
  water.userData.excludeFromMeasurement = true;

  group.add(water);
}

function hashCode(value: string): number {
  let hash = 2166136261;

  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }

  return hash >>> 0;
}

function assetSeed(assetCode: string): number {
  const profile = getDamBarrageTwinProfile(assetCode);

  const profileSeed =
    Number(profile?.geometry_seed);

  const codeSeed = hashCode(assetCode);

  if (Number.isFinite(profileSeed)) {
    return (
      (
        Math.abs(Math.trunc(profileSeed)) +
        codeSeed
      ) >>> 0
    );
  }

  return codeSeed;
}

function ranged(
  seed: number,
  channel: number,
  min: number,
  max: number,
): number {
  const raw =
    Math.sin(
      seed * 0.000001 +
      channel * 12.9898,
    ) * 43758.5453123;

  const fraction =
    raw - Math.floor(raw);

  return min + fraction * (max - min);
}

/*
 * IMPORTANT
 * ---------
 * These builders produce L1 asset-specific approximate geometry.
 *
 * Their generated dimensions are VISUAL proportions only.
 * They must never be interpreted or displayed as government
 * measurements.
 */

export function buildAssetSpecificBarrage(
  group: THREE.Group,
  assetCode: string,
) {
  const seed = assetSeed(assetCode);

  const concrete =
    new THREE.MeshStandardMaterial({
      color: 0xbec7cf,
      roughness: 0.82,
    });

  const darkConcrete =
    new THREE.MeshStandardMaterial({
      color: 0x727e89,
      roughness: 0.88,
    });

  const gates =
    new THREE.MeshStandardMaterial({
      color: 0x426f8e,
      roughness: 0.55,
      metalness: 0.28,
    });

  const road =
    new THREE.MeshStandardMaterial({
      color: 0x303840,
      roughness: 0.95,
    });

  const bank =
    new THREE.MeshStandardMaterial({
      color: 0x746b4e,
      roughness: 1,
    });

  const gateCount =
    Math.round(ranged(seed, 1, 7, 28));

  const length =
    ranged(seed, 2, 88, 158);

  const height =
    ranged(seed, 3, 4.2, 9.2);

  const depth =
    ranged(seed, 4, 6.2, 13.0);

  const pierWidth =
    ranged(seed, 5, 0.55, 1.20);

  const available =
    Math.max(
      length -
        pierWidth * (gateCount + 1),
      gateCount * 1.5,
    );

  const gateWidth =
    available / gateCount;

  addWater(
    group,
    length + 58,
    ranged(seed, 6, 58, 98),
    -2.2,
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      length + 5,
      2.1,
      depth + 2,
    ),
    concrete,
    [0, -0.9, 0],
  );

  for (
    let i = 0;
    i <= gateCount;
    i += 1
  ) {
    const x =
      -length / 2 +
      i * (gateWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(
        pierWidth,
        height + 3.5,
        depth,
      ),
      concrete,
      [x, height / 2 + 0.4, 0],
    );

    addMesh(
      group,
      new THREE.BoxGeometry(
        pierWidth + 0.3,
        0.42,
        depth + 0.8,
      ),
      darkConcrete,
      [x, height + 2.0, 0],
    );
  }

  for (
    let i = 0;
    i < gateCount;
    i += 1
  ) {
    const x =
      -length / 2 +
      pierWidth +
      gateWidth / 2 +
      i * (gateWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(
        Math.max(gateWidth * 0.90, 0.8),
        height,
        0.34,
      ),
      gates,
      [
        x,
        height / 2,
        depth * 0.18,
      ],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(
      length + 8,
      0.62,
      depth + 2.4,
    ),
    road,
    [0, height + 3.1, 0],
  );

  const bankWidth =
    ranged(seed, 7, 14, 29);

  addMesh(
    group,
    new THREE.BoxGeometry(
      bankWidth,
      ranged(seed, 8, 4, 7),
      depth + ranged(seed, 9, 10, 20),
    ),
    bank,
    [
      -length / 2 - bankWidth / 2,
      0.3,
      0,
    ],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      bankWidth,
      ranged(seed, 10, 4, 7),
      depth + ranged(seed, 11, 10, 20),
    ),
    bank,
    [
      length / 2 + bankWidth / 2,
      0.3,
      0,
    ],
  );

  /*
   * Add an asset-code-dependent service tower so even structures
   * with similar gate counts remain visually distinguishable.
   */
  const towerX =
    -length / 2 +
    ranged(seed, 12, 8, Math.max(10, length * 0.32));

  const towerHeight =
    ranged(seed, 13, 6, 12);

  addMesh(
    group,
    new THREE.BoxGeometry(
      ranged(seed, 14, 2.4, 5.4),
      towerHeight,
      ranged(seed, 15, 3.2, 6.8),
    ),
    darkConcrete,
    [
      towerX,
      towerHeight / 2 + height + 3.3,
      0,
    ],
  );

  group.userData.simrasGeometry = {
    assetCode,
    fidelity: "L1",
    geometrySource:
      "asset-specific deterministic approximate geometry",
    seed,
  };
}

export function buildAssetSpecificDam(
  group: THREE.Group,
  assetCode: string,
  assetName: string,
) {
  const seed = assetSeed(assetCode);

  const concrete =
    new THREE.MeshStandardMaterial({
      color: 0xaeb7bf,
      roughness: 0.85,
    });

  const rock =
    new THREE.MeshStandardMaterial({
      color: 0x6f695e,
      roughness: 1,
    });

  const gates =
    new THREE.MeshStandardMaterial({
      color: 0x386f8f,
      roughness: 0.60,
      metalness: 0.22,
    });

  const wallLength =
    ranged(seed, 21, 82, 152);

  const wallHeight =
    ranged(seed, 22, 12.5, 28.5);

  const wallDepth =
    ranged(seed, 23, 7, 16);

  const spillways =
    Math.round(ranged(seed, 24, 4, 17));

  const openingWidth =
    Math.max(
      2.4,
      Math.min(
        5.8,
        wallLength /
          Math.max(spillways * 1.9, 1),
      ),
    );

  const spillwayZone =
    Math.min(
      wallLength * 0.72,
      spillways *
        (openingWidth + 1.2),
    );

  const spacing =
    spillways > 1
      ? spillwayZone /
        (spillways - 1)
      : openingWidth;

  addWater(
    group,
    wallLength + ranged(seed, 25, 35, 70),
    ranged(seed, 26, 65, 108),
    -2.5,
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      wallLength,
      wallHeight,
      wallDepth,
    ),
    concrete,
    [0, wallHeight / 2 - 2, 0],
  );

  for (
    let i = 0;
    i < spillways;
    i += 1
  ) {
    const x =
      spillways === 1
        ? 0
        : -spillwayZone / 2 +
          i * spacing;

    addMesh(
      group,
      new THREE.BoxGeometry(
        openingWidth,
        wallHeight *
          ranged(seed, 30 + i, 0.32, 0.52),
        0.45,
      ),
      gates,
      [
        x,
        wallHeight * 0.30,
        wallDepth / 2 + 0.12,
      ],
    );
  }

  const abutmentWidth =
    ranged(seed, 60, 14, 30);

  const leftDepth =
    ranged(seed, 61, 24, 45);

  const rightDepth =
    ranged(seed, 62, 24, 45);

  addMesh(
    group,
    new THREE.BoxGeometry(
      abutmentWidth,
      wallHeight * 0.78,
      leftDepth,
    ),
    rock,
    [
      -wallLength / 2 -
        abutmentWidth / 2,
      wallHeight * 0.30,
      0,
    ],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      abutmentWidth *
        ranged(seed, 63, 0.8, 1.15),
      wallHeight *
        ranged(seed, 64, 0.68, 0.88),
      rightDepth,
    ),
    rock,
    [
      wallLength / 2 +
        abutmentWidth / 2,
      wallHeight * 0.28,
      0,
    ],
  );

  const crestWidth =
    ranged(seed, 65, 3.5, 8.5);

  addMesh(
    group,
    new THREE.BoxGeometry(
      wallLength + 2,
      0.55,
      crestWidth,
    ),
    concrete,
    [0, wallHeight - 1.5, 0],
  );

  /*
   * Deterministic intake/control block:
   * another geometry feature derived from asset identity.
   */
  const controlWidth =
    ranged(seed, 66, 4, 10);

  const controlHeight =
    ranged(seed, 67, 5, 13);

  addMesh(
    group,
    new THREE.BoxGeometry(
      controlWidth,
      controlHeight,
      ranged(seed, 68, 5, 11),
    ),
    concrete,
    [
      wallLength *
        ranged(seed, 69, -0.28, 0.28),
      wallHeight +
        controlHeight / 2 - 1.2,
      0,
    ],
  );

  group.userData.simrasGeometry = {
    assetCode,
    assetName,
    fidelity: "L1",
    geometrySource:
      "asset-specific deterministic approximate geometry",
    seed,
  };
}