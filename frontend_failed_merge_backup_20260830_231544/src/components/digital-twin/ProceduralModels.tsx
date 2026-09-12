/**
 * Procedural 3D Model Generators for Infrastructure Assets
 *
 * Creates Three.js geometry for infrastructure assets without pre-built models.
 * Each function generates a simple but recognizable 3D representation.
 *
 * Models are "Procedural 3D Representations" - NOT engineering-accurate BIM models.
 * They are visualization aids only.
 */

import * as THREE from "three";

export type InfrastructureType =
  | "dam"
  | "bridge"
  | "road"
  | "airport"
  | "port"
  | "barrage"
  | "flyover"
  | "powerplant"
  | "school"
  | "building"
  | "utility"
  | "other";

/**
 * Dam: Concrete dam structure
 */
export function createDam(): THREE.Group {
  const group = new THREE.Group();

  // Dam body (main structure)
  const damGeom = new THREE.BoxGeometry(3, 2.5, 0.8);
  const damMat = new THREE.MeshPhongMaterial({ color: 0xaaaaaa });
  const damMesh = new THREE.Mesh(damGeom, damMat);
  damMesh.position.y = 0.5;
  damMesh.castShadow = true;
  damMesh.receiveShadow = true;
  group.add(damMesh);

  // Water representation
  const waterGeom = new THREE.PlaneGeometry(4, 2);
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x0088ff,
    metalness: 0.3,
    roughness: 0.4,
  });
  const waterMesh = new THREE.Mesh(waterGeom, waterMat);
  waterMesh.rotation.x = -Math.PI / 2;
  waterMesh.position.y = 0.05;
  waterMesh.position.z = 1.5;
  group.add(waterMesh);

  // Spillway gates
  for (let i = 0; i < 3; i++) {
    const gateGeom = new THREE.BoxGeometry(0.6, 1.5, 0.15);
    const gateMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
    const gateMesh = new THREE.Mesh(gateGeom, gateMat);
    gateMesh.position.set(-1.2 + i * 1.2, 1, 0.5);
    gateMesh.castShadow = true;
    group.add(gateMesh);
  }

  return group;
}

/**
 * Bridge: Multi-span bridge structure
 */
export function createBridge(): THREE.Group {
  const group = new THREE.Group();

  // Deck (main span)
  const deckGeom = new THREE.BoxGeometry(4, 0.3, 1);
  const deckMat = new THREE.MeshPhongMaterial({ color: 0x555555 });
  const deckMesh = new THREE.Mesh(deckGeom, deckMat);
  deckMesh.position.y = 1.5;
  deckMesh.castShadow = true;
  deckMesh.receiveShadow = true;
  group.add(deckMesh);

  // Piers (supports)
  for (let i = 0; i < 4; i++) {
    const pierGeom = new THREE.BoxGeometry(0.4, 1.4, 0.4);
    const pierMat = new THREE.MeshPhongMaterial({ color: 0x888888 });
    const pierMesh = new THREE.Mesh(pierGeom, pierMat);
    pierMesh.position.x = -1.5 + i * 1;
    pierMesh.position.y = 0.2;
    pierMesh.castShadow = true;
    pierMesh.receiveShadow = true;
    group.add(pierMesh);
  }

  // Cables (if suspension bridge style)
  const cableGeom = new THREE.TubeGeometry(
    new THREE.LineCurve3(
      new THREE.Vector3(-2, 2, 0),
      new THREE.Vector3(2, 2, 0)
    ),
    8,
    0.08,
    8,
    false
  );
  const cableMat = new THREE.MeshPhongMaterial({ color: 0xcccccc });
  const cableMesh = new THREE.Mesh(cableGeom, cableMat);
  group.add(cableMesh);

  return group;
}

/**
 * Road: Highway/road segment
 */
export function createRoad(): THREE.Group {
  const group = new THREE.Group();

  // Road surface
  const roadGeom = new THREE.PlaneGeometry(4, 2);
  const roadMat = new THREE.MeshPhongMaterial({ color: 0x333333 });
  const roadMesh = new THREE.Mesh(roadGeom, roadMat);
  roadMesh.rotation.x = -Math.PI / 2;
  roadMesh.receiveShadow = true;
  group.add(roadMesh);

  // Road markings (lane lines)
  const lineGeom = new THREE.PlaneGeometry(0.2, 4);
  const lineMat = new THREE.MeshPhongMaterial({ color: 0xffff00 });
  const lineMesh = new THREE.Mesh(lineGeom, lineMat);
  lineMesh.rotation.x = -Math.PI / 2;
  lineMesh.position.y = 0.01;
  group.add(lineMesh);

  // Shoulders
  for (const side of [-1, 1]) {
    const shoulderGeom = new THREE.PlaneGeometry(0.4, 4);
    const shoulderMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
    const shoulderMesh = new THREE.Mesh(shoulderGeom, shoulderMat);
    shoulderMesh.rotation.x = -Math.PI / 2;
    shoulderMesh.position.x = side * 1.2;
    shoulderMesh.position.y = -0.01;
    group.add(shoulderMesh);
  }

  return group;
}

/**
 * Airport: Airport terminal and runway
 */
export function createAirport(): THREE.Group {
  const group = new THREE.Group();

  // Runway
  const runwayGeom = new THREE.PlaneGeometry(0.8, 5);
  const runwayMat = new THREE.MeshPhongMaterial({ color: 0x444444 });
  const runwayMesh = new THREE.Mesh(runwayGeom, runwayMat);
  runwayMesh.rotation.x = -Math.PI / 2;
  runwayMesh.receiveShadow = true;
  group.add(runwayMesh);

  // Terminal building
  const terminalGeom = new THREE.BoxGeometry(2, 1.5, 1);
  const terminalMat = new THREE.MeshPhongMaterial({ color: 0xccaa88 });
  const terminalMesh = new THREE.Mesh(terminalGeom, terminalMat);
  terminalMesh.position.set(2, 0.75, 0);
  terminalMesh.castShadow = true;
  terminalMesh.receiveShadow = true;
  group.add(terminalMesh);

  // Control tower
  const towerGeom = new THREE.CylinderGeometry(0.3, 0.4, 2, 8);
  const towerMat = new THREE.MeshPhongMaterial({ color: 0xffffff });
  const towerMesh = new THREE.Mesh(towerGeom, towerMat);
  towerMesh.position.set(3, 1, -1);
  towerMesh.castShadow = true;
  group.add(towerMesh);

  // Radar dome on tower
  const radarGeom = new THREE.SphereGeometry(0.35, 16, 16);
  const radarMat = new THREE.MeshPhongMaterial({ color: 0xff6600 });
  const radarMesh = new THREE.Mesh(radarGeom, radarMat);
  radarMesh.position.set(3, 2.2, -1);
  radarMesh.scale.z = 0.6;
  radarMesh.castShadow = true;
  group.add(radarMesh);

  return group;
}

/**
 * Port: Harbor with dock and container crane
 */
export function createPort(): THREE.Group {
  const group = new THREE.Group();

  // Dock structure
  const dockGeom = new THREE.BoxGeometry(3, 0.5, 1);
  const dockMat = new THREE.MeshPhongMaterial({ color: 0x777777 });
  const dockMesh = new THREE.Mesh(dockGeom, dockMat);
  dockMesh.position.y = 0.25;
  dockMesh.castShadow = true;
  dockMesh.receiveShadow = true;
  group.add(dockMesh);

  // Water
  const waterGeom = new THREE.PlaneGeometry(4, 2);
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x002266,
    metalness: 0.2,
  });
  const waterMesh = new THREE.Mesh(waterGeom, waterMat);
  waterMesh.rotation.x = -Math.PI / 2;
  waterMesh.position.y = -0.1;
  waterMesh.position.z = 1;
  group.add(waterMesh);

  // Container crane (gantry)
  const craneBaseGeom = new THREE.BoxGeometry(0.4, 0.5, 3);
  const craneMat = new THREE.MeshPhongMaterial({ color: 0xff9900 });
  const craneBaseMesh = new THREE.Mesh(craneBaseGeom, craneMat);
  craneBaseMesh.position.set(-1, 0.5, 0);
  craneBaseMesh.castShadow = true;
  group.add(craneBaseMesh);

  // Crane boom
  const boomGeom = new THREE.BoxGeometry(0.2, 0.2, 2.5);
  const boomMesh = new THREE.Mesh(boomGeom, craneMat);
  boomMesh.position.set(-1, 1.5, 0);
  boomMesh.castShadow = true;
  group.add(boomMesh);

  return group;
}

/**
 * Barrage: Water flow control structure
 */
export function createBarrage(): THREE.Group {
  const group = new THREE.Group();

  // Main structure (similar to dam)
  const barrageGeom = new THREE.BoxGeometry(2.5, 1.8, 0.6);
  const barrageMat = new THREE.MeshPhongMaterial({ color: 0x888888 });
  const barrageMesh = new THREE.Mesh(barrageGeom, barrageMat);
  barrageMesh.position.y = 0.4;
  barrageMesh.castShadow = true;
  barrageMesh.receiveShadow = true;
  group.add(barrageMesh);

  // Control gates
  for (let i = 0; i < 4; i++) {
    const gateGeom = new THREE.BoxGeometry(0.5, 1.2, 0.12);
    const gateMat = new THREE.MeshPhongMaterial({ color: 0x555555 });
    const gateMesh = new THREE.Mesh(gateGeom, gateMat);
    gateMesh.position.set(-1 + i * 0.8, 0.8, 0.4);
    gateMesh.castShadow = true;
    group.add(gateMesh);
  }

  // Water flow representation
  const waterGeom = new THREE.PlaneGeometry(3, 1.5);
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x0099ff,
    metalness: 0.4,
  });
  const waterMesh = new THREE.Mesh(waterGeom, waterMat);
  waterMesh.rotation.x = -Math.PI / 2;
  waterMesh.position.y = 0.05;
  waterMesh.position.z = 1;
  group.add(waterMesh);

  return group;
}

/**
 * Flyover: Elevated highway/flyover
 */
export function createFlyover(): THREE.Group {
  const group = new THREE.Group();

  // Elevated deck
  const deckGeom = new THREE.BoxGeometry(3.5, 0.4, 0.8);
  const deckMat = new THREE.MeshPhongMaterial({ color: 0x444444 });
  const deckMesh = new THREE.Mesh(deckGeom, deckMat);
  deckMesh.position.y = 1.2;
  deckMesh.castShadow = true;
  deckMesh.receiveShadow = true;
  group.add(deckMesh);

  // Support pillars
  for (let i = 0; i < 3; i++) {
    const pillarGeom = new THREE.CylinderGeometry(0.25, 0.3, 1.1, 8);
    const pillarMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
    const pillarMesh = new THREE.Mesh(pillarGeom, pillarMat);
    pillarMesh.position.x = -1.5 + i * 1.5;
    pillarMesh.position.y = 0.55;
    pillarMesh.castShadow = true;
    pillarMesh.receiveShadow = true;
    group.add(pillarMesh);
  }

  // Railing
  const railGeom = new THREE.BoxGeometry(3.5, 0.3, 0.1);
  const railMat = new THREE.MeshPhongMaterial({ color: 0xaaaaaa });
  const railMesh = new THREE.Mesh(railGeom, railMat);
  railMesh.position.set(0, 1.5, 0.45);
  group.add(railMesh);

  return group;
}

/**
 * Power Plant: Industrial structure with cooling towers
 */
export function createPowerPlant(): THREE.Group {
  const group = new THREE.Group();

  // Main building
  const buildingGeom = new THREE.BoxGeometry(2, 1.5, 2);
  const buildingMat = new THREE.MeshPhongMaterial({ color: 0x888888 });
  const buildingMesh = new THREE.Mesh(buildingGeom, buildingMat);
  buildingMesh.position.set(0, 0.75, 0);
  buildingMesh.castShadow = true;
  buildingMesh.receiveShadow = true;
  group.add(buildingMesh);

  // Cooling towers
  for (let i = 0; i < 2; i++) {
    const towerGeom = new THREE.CylinderGeometry(0.6, 0.7, 2, 16);
    const towerMat = new THREE.MeshPhongMaterial({ color: 0xcccccc });
    const towerMesh = new THREE.Mesh(towerGeom, towerMat);
    towerMesh.position.set(-1.2 + i * 2.4, 1, -1.5);
    towerMesh.castShadow = true;
    group.add(towerMesh);
  }

  // Smokestack/chimney
  const stackGeom = new THREE.CylinderGeometry(0.25, 0.3, 3, 8);
  const stackMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
  const stackMesh = new THREE.Mesh(stackGeom, stackMat);
  stackMesh.position.set(-2, 2, 0.5);
  stackMesh.castShadow = true;
  group.add(stackMesh);

  // Power lines/transmissions
  const lineGeom = new THREE.TubeGeometry(
    new THREE.LineCurve3(
      new THREE.Vector3(-0.5, 2, 0),
      new THREE.Vector3(2, 2.5, -1)
    ),
    4,
    0.05,
    6,
    false
  );
  const lineMat = new THREE.MeshPhongMaterial({ color: 0x333333 });
  const lineMesh = new THREE.Mesh(lineGeom, lineMat);
  group.add(lineMesh);

  return group;
}

/**
 * School: Educational building
 */
export function createSchool(): THREE.Group {
  const group = new THREE.Group();

  // Main building
  const buildingGeom = new THREE.BoxGeometry(2.5, 1.8, 2);
  const buildingMat = new THREE.MeshPhongMaterial({ color: 0xdd7755 });
  const buildingMesh = new THREE.Mesh(buildingGeom, buildingMat);
  buildingMesh.position.set(0, 0.9, 0);
  buildingMesh.castShadow = true;
  buildingMesh.receiveShadow = true;
  group.add(buildingMesh);

  // Roof (pyramid style)
  const roofGeom = new THREE.ConeGeometry(1.45, 0.6, 4);
  const roofMat = new THREE.MeshPhongMaterial({ color: 0xff5500 });
  const roofMesh = new THREE.Mesh(roofGeom, roofMat);
  roofMesh.position.y = 1.85;
  roofMesh.castShadow = true;
  group.add(roofMesh);

  // Flagpole
  const poleGeom = new THREE.CylinderGeometry(0.08, 0.08, 1.2, 8);
  const poleMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
  const poleMesh = new THREE.Mesh(poleGeom, poleMat);
  poleMesh.position.set(1, 2.2, -0.8);
  poleMesh.castShadow = true;
  group.add(poleMesh);

  // Flag
  const flagGeom = new THREE.PlaneGeometry(0.4, 0.25);
  const flagMat = new THREE.MeshPhongMaterial({ color: 0xff6600 });
  const flagMesh = new THREE.Mesh(flagGeom, flagMat);
  flagMesh.position.set(1.3, 2.25, -0.8);
  group.add(flagMesh);

  return group;
}

/**
 * Building: Generic commercial/residential building
 */
export function createBuilding(): THREE.Group {
  const group = new THREE.Group();

  // Main structure
  const buildingGeom = new THREE.BoxGeometry(1.5, 2, 1.5);
  const buildingMat = new THREE.MeshPhongMaterial({ color: 0xccccaa });
  const buildingMesh = new THREE.Mesh(buildingGeom, buildingMat);
  buildingMesh.position.y = 1;
  buildingMesh.castShadow = true;
  buildingMesh.receiveShadow = true;
  group.add(buildingMesh);

  // Windows (grid pattern)
  const windowMat = new THREE.MeshPhongMaterial({ color: 0x3366ff });
  for (let x = 0; x < 3; x++) {
    for (let y = 0; y < 4; y++) {
      const windowGeom = new THREE.BoxGeometry(0.2, 0.2, 0.1);
      const windowMesh = new THREE.Mesh(windowGeom, windowMat);
      windowMesh.position.set(
        -0.4 + x * 0.35,
        0.4 + y * 0.4,
        0.76
      );
      group.add(windowMesh);
    }
  }

  // Entrance door
  const doorGeom = new THREE.BoxGeometry(0.4, 0.8, 0.1);
  const doorMat = new THREE.MeshPhongMaterial({ color: 0x8b4513 });
  const doorMesh = new THREE.Mesh(doorGeom, doorMat);
  doorMesh.position.set(0, 0.3, 0.76);
  group.add(doorMesh);

  return group;
}

/**
 * Generic utility structure
 */
export function createUtility(): THREE.Group {
  const group = new THREE.Group();

  // Tower base
  const baseGeom = new THREE.CylinderGeometry(0.3, 0.4, 0.6, 8);
  const baseMat = new THREE.MeshPhongMaterial({ color: 0x888888 });
  const baseMesh = new THREE.Mesh(baseGeom, baseMat);
  baseMesh.position.y = 0.3;
  baseMesh.castShadow = true;
  baseMesh.receiveShadow = true;
  group.add(baseMesh);

  // Tower shaft
  const shaftGeom = new THREE.CylinderGeometry(0.15, 0.15, 2.5, 8);
  const shaftMat = new THREE.MeshPhongMaterial({ color: 0x666666 });
  const shaftMesh = new THREE.Mesh(shaftGeom, shaftMat);
  shaftMesh.position.y = 1.6;
  shaftMesh.castShadow = true;
  group.add(shaftMesh);

  // Equipment at top
  const equipGeom = new THREE.BoxGeometry(0.5, 0.3, 0.5);
  const equipMat = new THREE.MeshPhongMaterial({ color: 0xff0000 });
  const equipMesh = new THREE.Mesh(equipGeom, equipMat);
  equipMesh.position.y = 2.8;
  equipMesh.castShadow = true;
  group.add(equipMesh);

  return group;
}

/**
 * Generic/default model
 */
export function createDefault(): THREE.Group {
  const group = new THREE.Group();

  const geom = new THREE.BoxGeometry(1, 1, 1);
  const mat = new THREE.MeshPhongMaterial({ color: 0x666666 });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);

  return group;
}

/**
 * Factory function to create appropriate model for asset type
 */
export function createProceduralModel(
  assetType: string | null | undefined
): THREE.Group {
  const type = (assetType?.toLowerCase() || "other") as InfrastructureType;

  switch (type) {
    case "dam":
      return createDam();
    case "bridge":
      return createBridge();
    case "road":
      return createRoad();
    case "airport":
      return createAirport();
    case "port":
      return createPort();
    case "barrage":
      return createBarrage();
    case "flyover":
      return createFlyover();
    case "powerplant":
      return createPowerPlant();
    case "school":
      return createSchool();
    case "building":
      return createBuilding();
    case "utility":
      return createUtility();
    default:
      return createDefault();
  }
}
