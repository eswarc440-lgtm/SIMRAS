import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import {
  selectVerifiedDimensionMetrics,
  type SourceBackedDimensionMetric,
} from "./sourceBackedDimensions";

type Props = { assetCode?: string | null };
type AssetRecord = Record<string, unknown>;

type Metric = SourceBackedDimensionMetric;

type SourceProfile = {
  assetCode: string;
  name: string;
  type: "dam" | "barrage" | "bridge" | "airport" | "temple";
  fidelity: "L2" | "L1";
  source: string;
  sourceUrl?: string;
  headingDeg?: number;
  metrics: Metric[];
};

const verified = (
  key: string,
  label: string,
  value: string,
  source: string,
  category = "Dimensions",
): Metric => ({ key, label, value, status: "VERIFIED", source, category });

const APWRD = "Government of Andhra Pradesh Water Resources / KRMB project record";
const PPA = "Polavaram Project Authority, Government of India";
const CWC = "Central Water Commission / official project engineering record";
const AAI = "Airports Authority of India eAIP";
const ICID = "ICID technical record + Government of Andhra Pradesh expert committee";
const TTD = "Tirumala Tirupati Devasthanams published temple profile";

const SOURCE_PROFILES: Record<string, SourceProfile> = {
  AP_DAM_00001: {
    assetCode: "AP_DAM_00001",
    name: "Prakasam Barrage",
    type: "barrage",
    fidelity: "L2",
    source: APWRD,
    sourceUrl: "https://irrigation.ap.gov.in/wrd/home/projects/51",
    metrics: [
      verified("total_length_m", "Barrage length", "1232.92 m", APWRD),
      verified("gate_count", "Regulator gates", "70", APWRD, "Structure"),
      verified("gate_width_m", "Gate width", "12.19 m", APWRD, "Structure"),
      verified("gate_height_m", "Gate height", "3.66 m", APWRD, "Structure"),
      verified("left_scouring_sluice_count", "Left scour sluices", "6", APWRD, "Structure"),
      verified("right_scouring_sluice_count", "Right scour sluices", "8", APWRD, "Structure"),
      verified("construction_year", "Completion year", "1957", APWRD, "Construction"),
    ],
  },
  AP_DAM_00002: {
    assetCode: "AP_DAM_00002",
    name: "Polavaram Irrigation Project",
    type: "dam",
    fidelity: "L2",
    source: PPA,
    sourceUrl: "https://ppa.gov.in/WPSCore/Common/WebPages/Home/AboutProject.aspx",
    metrics: [
      verified("total_length_m", "Dam system length", "2454 m", PPA),
      verified("height_m", "Maximum dam height", "50 m", PPA),
      verified("spillway_length_m", "Spillway length", "1118.40 m", PPA, "Structure"),
      verified("gate_count", "Radial gates", "48", PPA, "Structure"),
      verified("gate_width_m", "Radial gate width", "16 m", PPA, "Structure"),
      verified("gate_height_m", "Radial gate height", "20 m", PPA, "Structure"),
      verified("power_capacity_mw", "Installed capacity", "960 MW", PPA, "Structure"),
      verified("power_unit_count", "Power units", "12", PPA, "Structure"),
      verified("live_storage_tmc", "Live reservoir capacity", "75.2 TMC", PPA, "Water / capacity"),
    ],
  },
  AP_DAM_NWDP_AP01VH0059: {
    assetCode: "AP_DAM_NWDP_AP01VH0059",
    name: "Srisailam Project",
    type: "dam",
    fidelity: "L2",
    source: CWC,
    metrics: [
      verified("total_length_m", "Dam length", "512 m", CWC),
      verified("height_m", "Dam height", "145 m", CWC),
      verified("gate_count", "Radial crest gates", "12", CWC, "Structure"),
      verified("gate_width_m", "Gate width", "18.3 m", CWC, "Structure"),
      verified("gate_height_m", "Gate height", "16.7 m", CWC, "Structure"),
      verified("gross_storage_mcm", "Gross storage", "6110.9 MCM", CWC, "Water / capacity"),
      verified("live_storage_mcm", "Live storage", "6014.17 MCM", CWC, "Water / capacity"),
    ],
  },
  AP_DAM_WRIS_AP01HH0062: {
    assetCode: "AP_DAM_WRIS_AP01HH0062",
    name: "Somasila Reservoir",
    type: "dam",
    fidelity: "L2",
    source: CWC,
    metrics: [
      verified("total_length_m", "Dam length", "760 m", CWC),
      verified("height_m", "Dam height", "39 m", CWC),
      verified("gross_storage_mcm", "Gross storage", "2208.37 MCM", CWC, "Water / capacity"),
      verified("live_storage_mcm", "Live storage", "1994.1 MCM", CWC, "Water / capacity"),
    ],
  },
  AP_BAR_WRIS_B00131: {
    assetCode: "AP_BAR_WRIS_B00131",
    name: "Sir Arthur Cotton Barrage",
    type: "barrage",
    fidelity: "L2",
    source: ICID,
    metrics: [
      verified("total_length_m", "Total barrage length", "3592.67 m", ICID),
      verified("height_m", "Height", "10.6 m", CWC),
      verified("gate_count", "Total vents", "175", ICID, "Structure"),
      verified("gate_width_m", "Gate width", "18.29 m", ICID, "Structure"),
      verified("gate_height_m", "Gate height", "3.34 m", ICID, "Structure"),
      verified("width_m", "Road width", "7.50 m", ICID),
    ],
  },
  AP_AIR_VOBZ: {
    assetCode: "AP_AIR_VOBZ",
    name: "Vijayawada Airport",
    type: "airport",
    fidelity: "L2",
    source: AAI,
    sourceUrl: "https://aim-india.aai.aero/",
    headingDeg: 77.75,
    metrics: [
      verified("runway_length_m", "Runway 08/26 length", "3360 m", AAI),
      verified("runway_width_m", "Runway width", "45 m", AAI),
      verified("runway_strip_length_m", "Runway strip length", "3480 m", AAI),
      verified("runway_strip_width_m", "Runway strip width", "280 m", AAI),
    ],
  },
  AP_AIR_VOTP: {
    assetCode: "AP_AIR_VOTP",
    name: "Tirupati Airport",
    type: "airport",
    fidelity: "L2",
    source: AAI,
    sourceUrl: "https://aim-india.aai.aero/",
    headingDeg: 81.5,
    metrics: [
      verified("runway_length_m", "Runway 08/26 length", "2285 m", AAI),
      verified("runway_width_m", "Runway width", "45 m", AAI),
      verified("runway_strip_length_m", "Runway strip length", "2405 m", AAI),
      verified("runway_strip_width_m", "Runway strip width", "150 m", AAI),
    ],
  },
  AP_TEMPLE_TIRUMALA: {
    assetCode: "AP_TEMPLE_TIRUMALA",
    name: "Sri Venkateswara Swamy Temple, Tirumala",
    type: "temple",
    fidelity: "L1",
    source: TTD,
    sourceUrl: "https://www.tirumala.org/TTDTempleHistory.aspx",
    metrics: [
      verified("land_area_acres", "Temple complex area", "16.2 acres", TTD),
      verified("gopuram_tiers", "Main entrance tiers", "7", TTD, "Structure"),
      verified("main_entrance_height_ft", "Main entrance height", "50 ft", TTD),
    ],
  },
};

function num(value: string | undefined) {
  if (!value) return null;
  const match = value.replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function metric(profile: SourceProfile, key: string) {
  return profile.metrics.find((item) => item.key === key);
}

function addBox(
  group: THREE.Group,
  size: [number, number, number],
  position: [number, number, number],
  material: THREE.Material,
  name: string,
) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.set(...position);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
}

const concrete = () => new THREE.MeshStandardMaterial({ color: 0xb7c0c6, roughness: 0.84 });
const dark = () => new THREE.MeshStandardMaterial({ color: 0x667985, roughness: 0.86 });
const metal = () => new THREE.MeshStandardMaterial({ color: 0x237e9c, roughness: 0.48, metalness: 0.25 });
const earth = () => new THREE.MeshStandardMaterial({ color: 0x756b55, roughness: 1 });
const asphalt = () => new THREE.MeshStandardMaterial({ color: 0x272d32, roughness: 0.96 });

function addWater(group: THREE.Group, length: number, width: number) {
  const mesh = addBox(
    group,
    [length, 0.18, width],
    [0, -0.35, 0],
    new THREE.MeshStandardMaterial({ color: 0x1576a0, transparent: true, opacity: 0.62, roughness: 0.28 }),
    "SIMRAS_WATER",
  );
  mesh.userData.excludeFromMeasurement = true;
}

function buildWaterTwin(group: THREE.Group, profile: SourceProfile) {
  const lengthM = num(metric(profile, "total_length_m")?.value) ?? 1000;
  const heightM = num(metric(profile, "height_m")?.value) ?? 18;
  const gates = Math.round(num(metric(profile, "gate_count")?.value) ?? 0);
  const gateWidthM = num(metric(profile, "gate_width_m")?.value) ?? 10;
  const gateHeightM = num(metric(profile, "gate_height_m")?.value) ?? Math.min(heightM * 0.55, 10);

  const scale = Math.min(150 / lengthM, 0.18);
  const length = lengthM * scale;
  const height = Math.max(heightM * scale, 5.2);
  const depth = Math.max(7, height * 0.75);

  addWater(group, length * 1.35, 78);

  if (profile.assetCode === "AP_DAM_00002") {
    const spillwayM = num(metric(profile, "spillway_length_m")?.value) ?? 1118.4;
    const spillwayLength = spillwayM * scale;
    const embankmentLength = Math.max(length - spillwayLength * 0.35, length * 0.62);
    addBox(group, [embankmentLength, height, 15], [-length * 0.13, height / 2, 0], earth(), "POLAVARAM_ECRF");
    const spillwayX = length * 0.37;
    addBox(group, [spillwayLength, 1.2, 12], [spillwayX, 0.3, 18], concrete(), "POLAVARAM_SPILLWAY_FLOOR");
    const visualGateWidth = spillwayLength / Math.max(gates, 1);
    for (let i = 0; i < gates; i += 1) {
      const x = spillwayX - spillwayLength / 2 + visualGateWidth * (i + 0.5);
      addBox(group, [visualGateWidth * 0.68, Math.max(gateHeightM * scale, 2.2), 0.35], [x, Math.max(gateHeightM * scale, 2.2) / 2, 22], metal(), `POLAVARAM_GATE_${i + 1}`);
      addBox(group, [0.34, Math.max(gateHeightM * scale * 1.4, 4), 8], [x - visualGateWidth / 2, Math.max(gateHeightM * scale * 1.4, 4) / 2, 18], dark(), `POLAVARAM_PIER_${i + 1}`);
    }
    return;
  }

  if (profile.assetCode === "AP_BAR_WRIS_B00131") {
    const arms = [
      { length: 1437.92, count: 70, angle: 0, x: 0, z: 0 },
      { length: 884.45, count: 43, angle: Math.PI / 7, x: -14, z: -12 },
      { length: 469.66, count: 23, angle: -Math.PI / 7, x: 12, z: -9 },
      { length: 800.64, count: 39, angle: 0, x: 2, z: 20 },
    ];
    for (const [armIndex, arm] of arms.entries()) {
      const armGroup = new THREE.Group();
      const armLength = arm.length * 0.035;
      addBox(armGroup, [armLength, 1, 7], [0, 0, 0], concrete(), `COTTON_ARM_${armIndex + 1}`);
      const bay = armLength / arm.count;
      for (let i = 0; i < arm.count; i += 1) {
        const x = -armLength / 2 + bay * (i + 0.5);
        addBox(armGroup, [bay * 0.72, 2.7, 0.28], [x, 1.35, 3.4], metal(), `COTTON_GATE_${armIndex + 1}_${i + 1}`);
      }
      armGroup.position.set(arm.x, 0, arm.z);
      armGroup.rotation.y = arm.angle;
      group.add(armGroup);
    }
    return;
  }

  if (gates > 0) {
    const spillwayLength = Math.min(length * 0.78, Math.max(gates * gateWidthM * scale, length * 0.35));
    addBox(group, [length, height, depth], [0, height / 2, 0], concrete(), `${profile.assetCode}_BODY`);
    const bay = spillwayLength / gates;
    for (let i = 0; i < gates; i += 1) {
      const x = -spillwayLength / 2 + bay * (i + 0.5);
      addBox(group, [bay * 0.68, Math.max(gateHeightM * scale, 1.8), 0.3], [x, Math.max(gateHeightM * scale, 1.8) / 2, depth / 2 + 0.2], metal(), `${profile.assetCode}_GATE_${i + 1}`);
    }
  } else {
    const shape = new THREE.Shape();
    shape.moveTo(-12, 0);
    shape.lineTo(12, 0);
    shape.lineTo(4, height);
    shape.lineTo(-4, height);
    shape.closePath();
    const geometry = new THREE.ExtrudeGeometry(shape, { depth: length, bevelEnabled: false });
    geometry.rotateY(Math.PI / 2);
    geometry.translate(-length / 2, 0, 0);
    const mesh = new THREE.Mesh(geometry, concrete());
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
}

function buildAirportTwin(group: THREE.Group, profile: SourceProfile) {
  const lengthM = num(metric(profile, "runway_length_m")?.value) ?? 2000;
  const widthM = num(metric(profile, "runway_width_m")?.value) ?? 45;
  const scale = 150 / lengthM;
  const runwayLength = lengthM * scale;
  const runwayWidth = Math.max(widthM * scale, 3.2);

  addBox(group, [runwayLength, 0.35, runwayWidth], [0, 0, 0], asphalt(), `${profile.assetCode}_RUNWAY`);
  const stripe = new THREE.MeshStandardMaterial({ color: 0xf4f4ed, roughness: 0.8 });
  for (let i = 0; i < 18; i += 1) {
    const x = -runwayLength * 0.44 + (runwayLength * 0.88 * i) / 17;
    addBox(group, [3.6, 0.05, 0.18], [x, 0.22, 0], stripe, `RUNWAY_MARK_${i}`);
  }
  addBox(group, [42, 1, 22], [-25, 0.15, -runwayWidth * 4.2], new THREE.MeshStandardMaterial({ color: 0x6f777c, roughness: 0.92 }), "APRON");
  addBox(group, [25, 8, 14], [-30, 4, -runwayWidth * 6.6], concrete(), "TERMINAL_CONTEXT");
  addBox(group, [2.2, 14, 2.2], [-9, 7, -runwayWidth * 6.2], dark(), "ATC_CONTEXT");
  group.rotation.y = ((profile.headingDeg ?? 0) * Math.PI) / 180;
}

function buildTempleTwin(group: THREE.Group, profile: SourceProfile) {
  const stone = new THREE.MeshStandardMaterial({ color: 0xb89b71, roughness: 0.92 });
  addBox(group, [56, 2.4, 48], [0, 1.2, 0], stone, "TEMPLE_PLINTH");
  addBox(group, [27, 8, 23], [0, 6.4, 1], stone, "TEMPLE_MANDAPA");
  let y = 10.5;
  for (let tier = 0; tier < 7; tier += 1) {
    const w = 17 - tier * 1.8;
    const h = 3.1;
    addBox(group, [w, h, 8.5], [-16, y + h / 2, 15], stone, `TEMPLE_GOPURAM_TIER_${tier + 1}`);
    y += h;
  }
  const sanctum = new THREE.Mesh(new THREE.ConeGeometry(7, 12, 4), metal());
  sanctum.position.set(8, 16, 0);
  sanctum.rotation.y = Math.PI / 4;
  group.add(sanctum);
  group.userData.source = profile.source;
}

function buildFallback(group: THREE.Group, type: string, assetCode: string) {
  const m = concrete();
  if (type === "airport") {
    addBox(group, [140, 0.4, 5], [0, 0, 0], asphalt(), `${assetCode}_CONTEXT_RUNWAY`);
  } else if (type === "bridge") {
    addBox(group, [130, 1.4, 8], [0, 12, 0], asphalt(), `${assetCode}_CONTEXT_DECK`);
    for (const x of [-45, -15, 15, 45]) addBox(group, [2.4, 12, 4], [x, 6, 0], m, `${assetCode}_CONTEXT_PIER_${x}`);
  } else if (type === "temple") {
    addBox(group, [38, 3, 34], [0, 1.5, 0], m, `${assetCode}_CONTEXT_TEMPLE`);
    addBox(group, [16, 20, 12], [0, 13, 0], m, `${assetCode}_CONTEXT_TOWER`);
  } else {
    addBox(group, [120, 16, 10], [0, 8, 0], m, `${assetCode}_CONTEXT_STRUCTURE`);
    addWater(group, 165, 60);
  }
}

function inferType(code: string, asset: AssetRecord | null) {
  const explicit = String(asset?.asset_type ?? asset?.type ?? "").toLowerCase();
  if (explicit) return explicit;
  if (code.includes("_AIR_")) return "airport";
  if (code.includes("_TEMPLE_")) return "temple";
  if (code.includes("_BR_")) return "bridge";
  if (code.includes("_BAR_")) return "barrage";
  if (code.includes("_DAM_")) return "dam";
  return "infrastructure";
}

function measurementBounds(root: THREE.Object3D) {
  const bounds = new THREE.Box3();
  let found = false;
  root.updateMatrixWorld(true);
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    if (child.userData.excludeFromMeasurement === true) return;
    const b = new THREE.Box3().setFromObject(child);
    if (b.isEmpty()) return;
    bounds.union(b);
    found = true;
  });
  return found ? bounds : new THREE.Box3().setFromObject(root);
}

function spriteLabel(text: string, sceneSize: number) {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.font = "700 34px Inter, Arial, sans-serif";
  const width = Math.ceil(context.measureText(text).width) + 34;
  canvas.width = width;
  canvas.height = 62;
  context.fillStyle = "rgba(2,18,29,.96)";
  context.strokeStyle = "rgba(103,232,249,.96)";
  context.lineWidth = 3;
  context.beginPath();
  context.roundRect(2, 2, width - 4, 58, 11);
  context.fill();
  context.stroke();
  context.font = "700 34px Inter, Arial, sans-serif";
  context.fillStyle = "#effcff";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, width / 2, 31);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  const h = Math.max(sceneSize * 0.055, 3.4);
  sprite.scale.set(h * (width / 62), h, 1);
  sprite.renderOrder = 100;
  return sprite;
}

function addDimensionLine(
  group: THREE.Group,
  start: THREE.Vector3,
  end: THREE.Vector3,
  label: string,
  sceneSize: number,
  labelOffset: THREE.Vector3,
) {
  const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
  const line = new THREE.Line(
    geometry,
    new THREE.LineBasicMaterial({ color: 0x67e8f9, transparent: true, opacity: 1, depthTest: false }),
  );
  line.renderOrder = 90;
  group.add(line);
  for (const point of [start, end]) {
    const dot = new THREE.Mesh(
      new THREE.SphereGeometry(Math.max(sceneSize * 0.006, 0.25), 10, 8),
      new THREE.MeshBasicMaterial({ color: 0xe6fbff, depthTest: false }),
    );
    dot.position.copy(point);
    dot.renderOrder = 91;
    group.add(dot);
  }
  const sprite = spriteLabel(label, sceneSize);
  if (sprite) {
    sprite.position.copy(start.clone().add(end).multiplyScalar(0.5).add(labelOffset));
    group.add(sprite);
  }
}

function addDimensions(root: THREE.Group, profile: SourceProfile, type: string) {
  const dimensions = new THREE.Group();
  dimensions.name = "SIMRAS_SOURCE_BACKED_DIMENSIONS";
  const bounds = measurementBounds(root);
  if (bounds.isEmpty()) return dimensions;
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const sceneSize = Math.max(size.x, size.y, size.z, 1);
  const margin = sceneSize * 0.08;
  const metrics = selectVerifiedDimensionMetrics(profile.metrics, type);

  const length = metrics.find((m) =>
    ["total_length_m", "length_m", "dam_length_m", "barrage_length_m", "bridge_length_m", "runway_length_m", "temple_length_m"].includes(m.key),
  );
  const height = metrics.find((m) =>
    ["height_m", "dam_height_m", "barrage_height_m", "bridge_height_m", "gopuram_height_m", "temple_height_m", "main_entrance_height_ft"].includes(m.key),
  );
  const width = metrics.find((m) =>
    ["width_m", "breadth_m", "deck_width_m", "runway_width_m", "temple_width_m", "gate_width_m"].includes(m.key),
  );
  const runwayStripLength = metrics.find((m) => m.key === "runway_strip_length_m");
  const runwayStripWidth = metrics.find((m) => m.key === "runway_strip_width_m");

  if (length) {
    const y = bounds.max.y + margin;
    addDimensionLine(
      dimensions,
      new THREE.Vector3(bounds.min.x, y, center.z),
      new THREE.Vector3(bounds.max.x, y, center.z),
      `${length.label}: ${length.value}`,
      sceneSize,
      new THREE.Vector3(0, margin * 0.45, 0),
    );
  }
  if (height) {
    const x = bounds.max.x + margin;
    addDimensionLine(
      dimensions,
      new THREE.Vector3(x, bounds.min.y, center.z),
      new THREE.Vector3(x, bounds.max.y, center.z),
      `${height.label}: ${height.value}`,
      sceneSize,
      new THREE.Vector3(margin * 0.75, 0, 0),
    );
  }
  if (width) {
    const z = bounds.max.z + margin * 0.45;
    const span = width.key === "gate_width_m" ? Math.max(size.x * 0.08, 3) : Math.max(size.z, size.x * 0.18);
    addDimensionLine(
      dimensions,
      new THREE.Vector3(bounds.min.x, bounds.min.y + Math.max(size.y * 0.28, 1), z),
      new THREE.Vector3(Math.min(bounds.min.x + span, bounds.max.x), bounds.min.y + Math.max(size.y * 0.28, 1), z),
      `${width.label}: ${width.value}`,
      sceneSize,
      new THREE.Vector3(0, margin * 0.38, 0),
    );
  }

  if (runwayStripLength) {
    const y = bounds.min.y + Math.max(size.y * 0.12, 0.8);
    const z = bounds.min.z - margin * 0.7;
    addDimensionLine(
      dimensions,
      new THREE.Vector3(bounds.min.x, y, z),
      new THREE.Vector3(bounds.max.x, y, z),
      `${runwayStripLength.label}: ${runwayStripLength.value}`,
      sceneSize,
      new THREE.Vector3(0, margin * 0.4, -margin * 0.25),
    );
  }

  if (runwayStripWidth) {
    const x = bounds.max.x - Math.max(size.x * 0.12, 2);
    addDimensionLine(
      dimensions,
      new THREE.Vector3(x, bounds.min.y + Math.max(size.y * 0.18, 0.8), bounds.min.z),
      new THREE.Vector3(x, bounds.min.y + Math.max(size.y * 0.18, 0.8), bounds.max.z),
      `${runwayStripWidth.label}: ${runwayStripWidth.value}`,
      sceneSize,
      new THREE.Vector3(margin * 0.45, margin * 0.35, 0),
    );
  }

  const countMetrics = metrics.filter((m) =>
    ["gate_count", "span_count", "pier_count", "pillar_count", "gopuram_tiers"].includes(m.key),
  );
  if (countMetrics.length) {
    const sprite = spriteLabel(countMetrics.map((m) => `${m.label}: ${m.value}`).join(" · "), sceneSize);
    if (sprite) {
      sprite.position.set(center.x, bounds.max.y + margin * 2.05, bounds.max.z + margin * 0.3);
      dimensions.add(sprite);
    }
  }

  return dimensions;
}

export default function RealityTwinAssetViewer({ assetCode }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [dimensionsVisible, setDimensionsVisible] = useState(true);

  useEffect(() => {
    let active = true;
    fetch("/reality-twin/assets.json", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : []))
      .then((rows) => active && setAssets(Array.isArray(rows) ? rows : []))
      .catch(() => active && setAssets([]));
    return () => { active = false; };
  }, []);

  const selectedAsset = useMemo(
    () => assets.find((asset) => String(asset.asset_code ?? "") === String(assetCode ?? "")) ?? null,
    [assets, assetCode],
  );

  const profile = assetCode ? SOURCE_PROFILES[assetCode] : undefined;
  const type = profile?.type ?? inferType(String(assetCode ?? ""), selectedAsset);
  const name = profile?.name ?? String(selectedAsset?.name ?? selectedAsset?.asset_name ?? assetCode ?? "Infrastructure");
  const district = String(selectedAsset?.district ?? "");
  const displayedMetrics = profile ? profile.metrics.filter((item) => item.status === "VERIFIED") : [];

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !assetCode) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07111f);
    scene.fog = new THREE.Fog(0x07111f, 260, 620);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 2500);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    host.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.maxPolarAngle = Math.PI * 0.49;

    scene.add(new THREE.HemisphereLight(0xd8efff, 0x24323d, 2.3));
    const sun = new THREE.DirectionalLight(0xffffff, 4.4);
    sun.position.set(120, 170, 95);
    sun.castShadow = true;
    scene.add(sun);

    const world = new THREE.Group();
    const content = new THREE.Group();
    world.add(content);
    scene.add(world);

    const ground = addBox(world, [260, 1.2, 150], [0, -3.6, 0], new THREE.MeshStandardMaterial({ color: 0x142331, roughness: 0.98 }), "GROUND");
    ground.userData.excludeFromMeasurement = true;
    const grid = new THREE.GridHelper(240, 34, 0x35bdd1, 0x123f52);
    grid.position.y = -2.95;
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.32;
    world.add(grid);

    if (profile?.type === "dam" || profile?.type === "barrage") buildWaterTwin(content, profile);
    else if (profile?.type === "airport") buildAirportTwin(content, profile);
    else if (profile?.type === "temple") buildTempleTwin(content, profile);
    else buildFallback(content, type, assetCode);

    const bounds = measurementBounds(content);
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    content.position.sub(center);
    content.position.y += size.y / 2 - bounds.min.y - 2.1;
    content.updateMatrixWorld(true);

    let dimensionGroup: THREE.Group | null = null;
    if (profile) {
      dimensionGroup = addDimensions(content, profile, type);
      dimensionGroup.visible = dimensionsVisible;
      dimensionGroup.renderOrder = 80;
      world.add(dimensionGroup);
    }

    const maxDimension = Math.max(size.x, size.y, size.z, 1);
    camera.position.set(maxDimension * 0.95, maxDimension * 0.60, maxDimension * 0.78);
    camera.near = Math.max(maxDimension / 2500, 0.05);
    camera.far = Math.max(maxDimension * 22, 1200);
    camera.updateProjectionMatrix();
    controls.target.set(0, Math.max(size.y * 0.15, 0), 0);
    controls.minDistance = maxDimension * 0.16;
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
      if (dimensionGroup) dimensionGroup.visible = dimensionsVisible;
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.dispose();
      host.replaceChildren();
    };
  }, [assetCode, profile, type, dimensionsVisible]);

  return (
    <div className="space-y-3" data-simras-reality-view="SOURCE_BACKED_L2_TWIN">
      <div className="relative h-[72vh] min-h-[620px] max-h-[820px] overflow-hidden rounded-xl border border-slate-700/60 bg-[#07111f]">
        <div ref={hostRef} className="absolute inset-0" />

        <div className="pointer-events-none absolute left-4 top-4 z-20 max-w-[520px] rounded-xl border border-white/10 bg-slate-950/90 px-4 py-3 text-white shadow-2xl backdrop-blur-md">
          <div className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-cyan-300">SIMRAS / REAL-WORLD ENGINEERING TWIN</div>
          <div className="mt-1 text-lg font-semibold">{name}</div>
          <div className="mt-1 text-[11px] text-slate-400">{assetCode}{district ? ` · ${district}` : ""}</div>
          <div className="mt-2 text-[10px] font-bold text-emerald-300">
            {profile ? `${profile.fidelity} ${profile.fidelity === "L2" ? "SOURCE-MATCHED ENGINEERING TWIN" : "SOURCE-BACKED PARAMETRIC TWIN"}` : "L0 CONTEXT MODEL"}
          </div>
          {profile && <div className="mt-1 text-[10px] leading-4 text-slate-400">Source: {profile.source}</div>}
        </div>

        <button
          type="button"
          className="absolute bottom-4 right-4 z-30 rounded-lg border border-cyan-300/30 bg-slate-950/90 px-3 py-2 text-xs font-semibold text-cyan-200"
          onClick={() => setDimensionsVisible((value) => !value)}
        >
          {dimensionsVisible ? "Hide dimensions" : "Show dimensions"}
        </button>

        {dimensionsVisible && displayedMetrics.length > 0 && (
          <div
            className="absolute right-4 top-4 z-30 w-[310px] max-h-[46%] overflow-y-auto rounded-xl border border-cyan-400/20 bg-slate-950/92 p-3 shadow-2xl backdrop-blur-md"
            data-simras-dimension-overlay="visible"
          >
            <div className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.2em] text-cyan-300">Verified engineering evidence</div>
            <div className="grid gap-2">
              {displayedMetrics.map((item) => (
                <div key={item.key} className="rounded-lg border border-cyan-400/15 bg-cyan-400/[0.04] p-2.5">
                  <div className="text-[9px] font-bold uppercase tracking-wide text-slate-400">{item.label}</div>
                  <div className="mt-0.5 text-sm font-bold text-white">{item.value}</div>
                  <div className="mt-1 text-[9px] leading-4 text-slate-500">{item.source}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {profile && (
        <section className="rounded-xl border bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">Infrastructure information</div>
              <h3 className="mt-1 text-sm font-semibold">Government/source-backed engineering facts</h3>
            </div>
            {profile.sourceUrl && (
              <a href={profile.sourceUrl} target="_blank" rel="noreferrer" className="text-xs font-semibold text-cyan-500 hover:underline">Open source</a>
            )}
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {displayedMetrics.map((item) => (
              <article key={`panel-${item.key}`} className="rounded-lg border p-3">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{item.label}</div>
                <div className="mt-1 text-sm font-semibold">{item.value}</div>
                <div className="mt-1 text-[10px] text-muted-foreground">{item.source}</div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
