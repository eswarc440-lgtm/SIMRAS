import { buildAssetSpecificBarrage, buildAssetSpecificDam } from "./AssetSpecificWaterGeometry";
import {
  damBarrageFidelityLabel,
  getDamBarrageTwinProfile,
} from "./damBarrageTwinRegistry";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import {
  buildVerifiedWaterTopologyTwin,
  getVerifiedWaterEngineeringValues,
  isVerifiedWaterTopologyAsset,
} from "./verifiedWaterTopologyTwin";

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

type EvidenceState = "VERIFIED" | "ESTIMATED" | "UNAVAILABLE";

type EngineeringCategory =
  | "Dimensions"
  | "Structure"
  | "Construction"
  | "Water / capacity";

type EngineeringMetric = {
  key: string;
  label: string;
  value: string;
  status: EvidenceState;
  source: string;
  category: EngineeringCategory;
};

type MetricDefinition = {
  key: string;
  label: string;
  aliases: string[];
  category: EngineeringCategory;
  unit?: string;
  integer?: boolean;
};

type SourceProfile = {
  status: Exclude<EvidenceState, "UNAVAILABLE">;
  source: string;
  values: Record<string, string | number>;
};

const SOURCE_PROFILES: Record<string, SourceProfile> = {
  AP_DAM_00001: {
    status: "VERIFIED",
    source: "Krishna River Management Board project record",
    values: {
      total_length_m: 1232.92,
      gate_count: 70,
      gate_width_m: 12.19,
      gate_height_m: 3.66,
      construction_year: 1957,
      structural_form: "Gated barrage",
    },
  },
  AP_BR_00001: {
    status: "ESTIMATED",
    source: "SIMRAS source-linked profile; asset identity verification pending",
    values: {
      total_length_m: 2745,
      span_count: 28,
      main_span_m: 97.55,
      material: "Prestressed concrete",
      structural_form: "Bowstring girder / arch bridge",
    },
  },
  AP_DAM_NWDP_AP01VH0059: {
    status: "VERIFIED",
    source: "Krishna River Management Board project record",
    values: {
      total_length_m: 512,
      height_m: 143.26,
      spillway_length_m: 266.39,
      gate_count: 12,
      gate_width_m: 18.3,
      gate_height_m: 16.7,
      gross_storage_mcm: 6110.907,
      full_reservoir_level_m: 269.75,
      maximum_water_level_m: 271.88,
      discharge_m3s: 38365,
      structural_form: "Gravity dam",
    },
  },

  /*
   * SIMRAS_SIR_ARTHUR_SOURCE_PROFILE_V2
   *
   * Updated with verified values from ICID technical paper and
   * Government of Andhra Pradesh expert committee report.
   *
   * Four-arm barrage:
   *   Dowleswaram : 70 bays, 1437.92 m
   *   Ralli       : 43 bays, 884.45 m
   *   Madduru     : 23 bays, 469.66 m
   *   Vijjeswaram : 39 bays, 800.64 m
   *
   * Total = 175 bays, 3592.67 m
   */
  AP_BAR_WRIS_B00131: {
    status: "VERIFIED",
    source:
      "International Commission on Irrigation & Drainage (ICID) technical paper; Government of Andhra Pradesh expert committee report",
    values: {
      total_length_m: 3592.67,

      height_m: 10.6,

      width_m: 7.50,

      gate_count: 175,

      gate_width_m: 18.29,

      gate_height_m: 3.34,

      dowleswaram_arm_vent_count: 70,

      ralli_arm_vent_count: 43,

      madduru_arm_vent_count: 23,

      vijjeswaram_arm_vent_count: 39,

      structural_form:
        "Four-arm gated barrage on RCC raft",
    },
  },
};

const COMMON_METRICS: MetricDefinition[] = [
  {
    key: "total_length_m",
    label: "Total length",
    aliases: [
      "total_length_m",
      "length_m",
      "crest_length_m",
      "structure_length_m",
      "bridge_length_m",
      "dam_length_m",
      "length",
    ],
    category: "Dimensions",
    unit: "m",
  },
  {
    key: "width_m",
    label: "Width / breadth",
    aliases: [
      "width_m",
      "breadth_m",
      "deck_width_m",
      "crest_width_m",
      "structure_width_m",
      "overall_width_m",
      "width",
      "breadth",
    ],
    category: "Dimensions",
    unit: "m",
  },
  {
    key: "height_m",
    label: "Maximum height",
    aliases: [
      "height_m",
      "maximum_height_m",
      "max_height_m",
      "dam_height_m",
      "structure_height_m",
      "height",
    ],
    category: "Dimensions",
    unit: "m",
  },
  {
    key: "foundation_depth_m",
    label: "Foundation depth",
    aliases: ["foundation_depth_m", "depth_m", "foundation_depth"],
    category: "Dimensions",
    unit: "m",
  },
  {
    key: "land_area_ha",
    label: "Land / site area",
    aliases: ["land_area_ha", "site_area_ha", "area_ha"],
    category: "Dimensions",
    unit: "ha",
  },
  {
    key: "site_area_sqm",
    label: "Site / floor area",
    aliases: ["site_area_sqm", "terminal_area_sqm", "floor_area_sqm", "area_sqm"],
    category: "Dimensions",
    unit: "mÃ‚Â²",
  },
  {
    key: "construction_year",
    label: "Built / construction year",
    aliases: [
      "construction_year",
      "constructed_year",
      "built_year",
      "year_built",
      "completion_year",
    ],
    category: "Construction",
    integer: true,
  },
  {
    key: "commissioned_year",
    label: "Commissioned year",
    aliases: ["commissioned_year", "commissioning_year", "year_commissioned"],
    category: "Construction",
    integer: true,
  },
  {
    key: "design_life_years",
    label: "Design life",
    aliases: ["design_life_years", "design_life", "service_life_years"],
    category: "Construction",
    unit: "years",
  },
  {
    key: "material",
    label: "Primary material",
    aliases: ["material", "primary_material", "construction_material"],
    category: "Structure",
  },
  {
    key: "structural_form",
    label: "Structural type",
    aliases: [
      "structural_form",
      "structure_type",
      "bridge_type",
      "dam_type",
      "configuration",
    ],
    category: "Structure",
  },
  {
    key: "owner_operator",
    label: "Owner / operator",
    aliases: ["owner_operator", "owner", "operator", "agency", "authority"],
    category: "Construction",
  },
  {
    key: "operational_status",
    label: "Operational status",
    aliases: ["operational_status", "asset_status", "status"],
    category: "Construction",
  },
];

const TYPE_METRICS: Record<string, MetricDefinition[]> = {
  bridge: [
    {
      key: "span_count",
      label: "Number of spans",
      aliases: ["span_count", "number_of_spans", "no_of_spans", "spans"],
      category: "Structure",
      integer: true,
    },
    {
      key: "pier_count",
      label: "Pillars / piers",
      aliases: [
        "pier_count",
        "pillar_count",
        "number_of_piers",
        "number_of_pillars",
        "no_of_piers",
        "piers",
        "pillars",
      ],
      category: "Structure",
      integer: true,
    },
    {
      key: "main_span_m",
      label: "Main span length",
      aliases: ["main_span_m", "typical_span_m", "maximum_span_m", "span_length_m"],
      category: "Structure",
      unit: "m",
    },
    {
      key: "abutment_count",
      label: "Abutments",
      aliases: ["abutment_count", "number_of_abutments", "abutments"],
      category: "Structure",
      integer: true,
    },
    {
      key: "lane_count",
      label: "Traffic lanes",
      aliases: ["lane_count", "number_of_lanes", "lanes"],
      category: "Structure",
      integer: true,
    },
    {
      key: "clearance_m",
      label: "Vertical clearance",
      aliases: ["clearance_m", "vertical_clearance_m", "navigation_clearance_m"],
      category: "Dimensions",
      unit: "m",
    },
  ],
  dam: [
    {
      key: "gate_count",
      label: "No. of gates",
      aliases: ["gate_count", "spillway_gate_count", "number_of_gates", "no_of_gates", "gates"],
      category: "Structure",
      integer: true,
    },
    {
      key: "gate_width_m",
      label: "Gate width",
      aliases: ["gate_width_m", "spillway_gate_width_m", "gate_width"],
      category: "Structure",
      unit: "m",
    },
    {
      key: "gate_height_m",
      label: "Gate height",
      aliases: ["gate_height_m", "spillway_gate_height_m", "gate_height"],
      category: "Structure",
      unit: "m",
    },
    {
      key: "spillway_length_m",
      label: "Spillway length",
      aliases: ["spillway_length_m", "spillway_length"],
      category: "Structure",
      unit: "m",
    },
  ],
  barrage: [
    {
      key: "dowleswaram_arm_vent_count",
      label: "Dowleswaram vents",
      aliases: ["dowleswaram_arm_vent_count", "dowleswaram_vent_count"],
      category: "Structure",
      integer: true,
    },
    {
      key: "ralli_arm_vent_count",
      label: "Ralli vents",
      aliases: ["ralli_arm_vent_count", "ralli_vent_count"],
      category: "Structure",
      integer: true,
    },
    {
      key: "madduru_arm_vent_count",
      label: "Madduru vents",
      aliases: ["madduru_arm_vent_count", "madduru_vent_count"],
      category: "Structure",
      integer: true,
    },
    {
      key: "vijjeswaram_arm_vent_count",
      label: "Vijjeswaram vents",
      aliases: ["vijjeswaram_arm_vent_count", "vijjeswaram_vent_count"],
      category: "Structure",
      integer: true,
    },
  ],
  airport: [
    {
      key: "runway_length_m",
      label: "Runway length",
      aliases: ["runway_length_m", "runway_length"],
      category: "Dimensions",
      unit: "m",
    },
    {
      key: "runway_width_m",
      label: "Runway width",
      aliases: ["runway_width_m", "runway_width"],
      category: "Dimensions",
      unit: "m",
    },
    {
      key: "terminal_height_m",
      label: "Terminal height",
      aliases: ["terminal_height_m", "building_height_m"],
      category: "Dimensions",
      unit: "m",
    },
    {
      key: "land_area_acres",
      label: "Land area",
      aliases: ["land_area_acres", "site_area_acres", "complex_land_area_acres"],
      category: "Dimensions",
      unit: "acres",
    },
  ],
  temple: [
    {
      key: "gopuram_height_m",
      label: "Gopuram height",
      aliases: [
        "gopuram_height_m",
        "main_gopuram_height_m",
        "rajagopuram_height_m",
        "tower_height_m",
        "temple_site_height_m",
        "gopuram_height",
      ],
      category: "Dimensions",
      unit: "m",
    },
    {
      key: "pillar_count",
      label: "Mandapa pillars",
      aliases: ["pillar_count", "mandapa_pillar_count", "number_of_pillars", "pillars"],
      category: "Structure",
      integer: true,
    },
    {
      key: "land_area_acres",
      label: "Temple complex area",
      aliases: ["complex_land_area_acres", "land_area_acres", "site_area_acres"],
      category: "Dimensions",
      unit: "acres",
    },
  ],
};

const WATER_METRICS: MetricDefinition[] = [
  {
    key: "gross_storage_mcm",
    label: "Gross water capacity",
    aliases: ["gross_storage_mcm", "gross_capacity_mcm", "reservoir_capacity_mcm", "storage_capacity_mcm"],
    category: "Water / capacity",
    unit: "MCM",
  },
  {
    key: "live_storage_mcm",
    label: "Live storage capacity",
    aliases: ["live_storage_mcm", "live_capacity_mcm"],
    category: "Water / capacity",
    unit: "MCM",
  },
  {
    key: "current_storage_mcm",
    label: "Current storage",
    aliases: ["current_storage_mcm", "reservoir_storage_mcm", "storage_mcm"],
    category: "Water / capacity",
    unit: "MCM",
  },
  {
    key: "water_level_m",
    label: "Current water level",
    aliases: ["water_level_m", "current_water_level_m", "reservoir_level_m"],
    category: "Water / capacity",
    unit: "m",
  },
  {
    key: "full_reservoir_level_m",
    label: "Full reservoir level",
    aliases: ["full_reservoir_level_m", "frl_m", "full_reservoir_level"],
    category: "Water / capacity",
    unit: "m",
  },
  {
    key: "flow_velocity_ms",
    label: "Water flow speed",
    aliases: ["flow_velocity_ms", "flow_velocity_m_s", "water_velocity_ms", "water_flow_speed_ms", "flow_speed_ms"],
    category: "Water / capacity",
    unit: "m/s",
  },
  {
    key: "discharge_m3s",
    label: "Discharge / flow rate",
    aliases: ["discharge_m3s", "flow_rate_m3s", "designed_total_spillway_capacity_m3s", "spillway_capacity_m3s"],
    category: "Water / capacity",
    unit: "mÃ‚Â³/s",
  },
];

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

function normaliseKey(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function assetIndex(asset: AssetRecord | null) {
  const index = new Map<string, unknown>();

  const walk = (value: unknown, depth: number) => {
    if (depth > 4 || value === null || value === undefined) return;

    if (Array.isArray(value)) {
      value.forEach((item) => walk(item, depth + 1));
      return;
    }

    if (typeof value !== "object") return;

    Object.entries(value as Record<string, unknown>).forEach(
      ([key, item]) => {
        const normalised = normaliseKey(key);
        if (!index.has(normalised)) index.set(normalised, item);
        walk(item, depth + 1);
      },
    );
  };

  walk(asset, 0);
  return index;
}

function present(value: unknown) {
  if (value === null || value === undefined || typeof value === "boolean") {
    return false;
  }

  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "string") return value.trim().length > 0;
  return false;
}

function parseNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;

  const match = value.replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  if (!match) return null;

  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatMetricValue(
  value: unknown,
  unit?: string,
  integer = false,
) {
  const numeric = parseNumber(value);

  if (numeric !== null) {
    const text = numeric.toLocaleString(undefined, {
      maximumFractionDigits: integer ? 0 : 3,
    });
    return unit ? `${text} ${unit}` : text;
  }

  const text = clean(value, "Not available");
  return unit && text !== "Not available" ? `${text} ${unit}` : text;
}

function evidenceState(
  index: Map<string, unknown>,
  matchedKey: string,
): Exclude<EvidenceState, "UNAVAILABLE"> {
  const candidates = [
    `${matchedKey}_status`,
    `${matchedKey}_quality`,
    "verification_status",
    "identity_status",
    "data_quality",
    "quality_flag",
  ];

  const signal = candidates
    .map((key) => index.get(normaliseKey(key)))
    .filter(present)
    .join(" ")
    .toLowerCase();

  if (signal.includes("verified") || signal.includes("authoritative")) {
    return "VERIFIED";
  }

  return "ESTIMATED";
}

function sourceLabel(index: Map<string, unknown>) {
  const sourceKeys = [
    "source_name",
    "data_source",
    "source",
    "source_title",
    "record_source",
  ];

  for (const key of sourceKeys) {
    const value = index.get(key);
    if (present(value)) return clean(value);
  }

  return "SIMRAS asset record";
}

function buildEngineeringMetrics(
  asset: AssetRecord | null,
  assetCode: string,
  type: string,
) {
  const index = assetIndex(asset);
  const profile = SOURCE_PROFILES[assetCode];
  const isWaterAsset = type === "dam" || type === "barrage" || type === "bridge";
  const typeDefinitions =
    type === "barrage" ? TYPE_METRICS.dam : TYPE_METRICS[type] ?? [];
  const definitions = [
    ...COMMON_METRICS,
    ...typeDefinitions,
    ...(isWaterAsset ? WATER_METRICS : []),
  ];

  const seen = new Set<string>();
  const metrics: EngineeringMetric[] = [];

  definitions.forEach((definition) => {
    if (seen.has(definition.key)) return;
    seen.add(definition.key);

    let value: unknown = null;
    let matchedKey = definition.key;

    for (const alias of definition.aliases) {
      const normalised = normaliseKey(alias);
      const candidate = index.get(normalised);
      if (!present(candidate)) continue;
      value = candidate;
      matchedKey = normalised;
      break;
    }

    let status: EvidenceState = "UNAVAILABLE";
    let source = "No linked source value";

    if (present(value)) {
      status = evidenceState(index, matchedKey);
      source = sourceLabel(index);
    } else if (profile && present(profile.values[definition.key])) {
      value = profile.values[definition.key];
      status = profile.status;
      source = profile.source;
    }

    metrics.push({
      key: definition.key,
      label: definition.label,
      value:
        status === "UNAVAILABLE"
          ? "Not available"
          : formatMetricValue(value, definition.unit, definition.integer),
      status,
      source,
      category: definition.category,
    });
  });

  const construction = metrics.find(
    (metric) =>
      metric.key === "construction_year" && metric.status !== "UNAVAILABLE",
  );
  const commissioned = metrics.find(
    (metric) =>
      metric.key === "commissioned_year" && metric.status !== "UNAVAILABLE",
  );
  const ageBase = construction ?? commissioned;

  if (ageBase) {
    const year = parseNumber(ageBase.value);
    if (year && year >= 1000 && year <= new Date().getUTCFullYear()) {
      const position = metrics.findIndex(
        (metric) => metric.key === "design_life_years",
      );
      metrics.splice(Math.max(position, 0), 0, {
        key: "current_age_years",
        label: "Current age",
        value: `${new Date().getUTCFullYear() - year} years`,
        status: ageBase.status,
        source: `Derived from ${ageBase.label.toLowerCase()}`,
        category: "Construction",
      });
    }
  }

  return metrics;
}

function metricByKey(metrics: EngineeringMetric[], ...keys: string[]) {
  return metrics.find(
    (metric) => keys.includes(metric.key) && metric.status !== "UNAVAILABLE",
  );
}


/*
 * SIMRAS_CWC_OFFICIAL_PROFILE_METRICS_V2
 *
 * CWC fields below are verified historical engineering
 * metadata/annotations only.
 *
 * IMPORTANT:
 * - They DO NOT scale the GLB.
 * - They DO NOT scale procedural geometry.
 * - They DO NOT promote fidelity above L1.
 */
function applyOfficialDamBarrageProfileMetrics(
  metrics: EngineeringMetric[],
  assetCode: string,
): EngineeringMetric[] {
  const profile =
    getDamBarrageTwinProfile(assetCode);

  if (
    !profile ||
    profile.dimension_status !==
      "OFFICIAL_CWC_ENGINEERING_AVAILABLE"
  ) {
    return metrics;
  }

  const dimensions =
    (profile.dimensions ?? {}) as Record<
      string,
      unknown
    >;

  const unsupportedStructuralKeys = new Set([
    "gate_count",
    "gate_width_m",
    "gate_height_m",
    "span_count",
    "pier_count",
    "pillar_count",
  ]);

  const result = metrics.filter((metric) => {
    if (!unsupportedStructuralKeys.has(metric.key)) {
      return true;
    }

    // Keep such a value only when this official profile
    // explicitly contains the corresponding field.
    return present(dimensions[metric.key]);
  });

  const cwcSource =
    "Central Water Commission (CWC) ? official historical register, snapshot 2014-07";

  const put = (
    key: string,
    label: string,
    rawValue: unknown,
    category: EngineeringCategory,
    unit?: string,
    integer = false,
  ) => {
    if (!present(rawValue)) return;

    const officialMetric: EngineeringMetric = {
      key,
      label,
      value: formatMetricValue(
        rawValue,
        unit,
        integer,
      ),
      status: "VERIFIED",
      source: cwcSource,
      category,
    };

    const existingIndex =
      result.findIndex(
        (metric) => metric.key === key,
      );

    if (existingIndex >= 0) {
      result[existingIndex] =
        officialMetric;
    } else {
      result.push(officialMetric);
    }
  };

  // ---------------------------------------------------------
  // These two keys are consumed directly by
  // createWorldDimensionAnnotations().
  // ---------------------------------------------------------

  put(
    "total_length_m",
    "Length",
    dimensions["length_m"],
    "Dimensions",
    "m",
  );

  put(
    "height_m",
    "Height",
    dimensions["height_m"],
    "Dimensions",
    "m",
  );

  // ---------------------------------------------------------
  // Additional official engineering metadata
  // ---------------------------------------------------------

  put(
    "construction_year",
    "Completion year",
    dimensions["completion_year"],
    "Construction",
    undefined,
    true,
  );

  put(
    "dam_type",
    "CWC dam type",
    dimensions["dam_type"],
    "Structure",
  );

  put(
    "gross_storage_capacity",
    "Gross storage capacity",
    dimensions["gross_storage_1000m3"],
    "Water / capacity",
    "10? m?",
  );

  put(
    "effective_storage_capacity",
    "Effective storage capacity",
    dimensions["effective_storage_1000m3"],
    "Water / capacity",
    "10? m?",
  );

  put(
    "reservoir_area",
    "Reservoir area",
    dimensions["reservoir_area_1000m2"],
    "Water / capacity",
    "10? m?",
  );

  put(
    "designed_spillway_capacity",
    "Designed spillway capacity",
    dimensions[
      "designed_spillway_capacity_m3s"
    ],
    "Water / capacity",
    "m?/s",
  );

  put(
    "dam_material_volume",
    "Dam material volume",
    dimensions[
      "dam_material_volume_1000m3"
    ],
    "Structure",
    "10? m?",
  );

  return result;
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
  water.userData.excludeFromMeasurement = true;
  group.add(water);
}

function disposeObject(root: THREE.Object3D) {
  root.traverse((child) => {
    if (
      !(child instanceof THREE.Mesh) &&
      !(child instanceof THREE.LineSegments)
    ) {
      return;
    }

    child.geometry?.dispose();
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    materials.forEach((material) => material?.dispose());
  });
}

function disposeDimensionAnnotations(root: THREE.Object3D) {
  root.traverse((child) => {
    if (child instanceof THREE.Line || child instanceof THREE.Mesh) {
      child.geometry?.dispose();
    }

    const candidate = child as THREE.Object3D & {
      material?: THREE.Material | THREE.Material[];
    };
    if (!candidate.material) return;

    const materials = Array.isArray(candidate.material)
      ? candidate.material
      : [candidate.material];
    materials.forEach((material) => {
      if (material instanceof THREE.SpriteMaterial) material.map?.dispose();
      material.dispose();
    });
  });
}


/*
 * ============================================================
 * SIMRAS_GLOBAL_TWIN_QUALITY_GATE_V2
 * ============================================================
 *
 * Rules:
 *  1. Prefer the exact asset GLB.
 *  2. Ignore oversized ground/image/context planes.
 *  3. Reject geometrically unusable GLBs.
 *  4. Use deterministic asset-specific L1 geometry as fallback.
 *
 * Engineering dimensions are metadata only.
 * They never establish real mesh scale here.
 */

function simrasTwinSeed(assetCode: string) {
  let h = 2166136261;

  for (let i = 0; i < assetCode.length; i += 1) {
    h ^= assetCode.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }

  return Math.abs(h >>> 0);
}

function installQualityFallback(
  root: THREE.Object3D,
  assetType: string,
  assetCode: string,
) {
  /*
   * Remove the rejected visual scene only.
   * Original .glb file on disk is untouched.
   */
  while (root.children.length > 0) {
    root.remove(root.children[0]);
  }

  const group = new THREE.Group();

  group.name =
    "SIMRAS_ASSET_SPECIFIC_L1_FALLBACK";

  const seed =
    simrasTwinSeed(
      assetCode || assetType || "SIMRAS",
    );

  const a =
    (seed % 997) / 997;

  const b =
    ((seed >>> 8) % 991) / 991;

  const c =
    ((seed >>> 16) % 983) / 983;

  const main =
    new THREE.MeshStandardMaterial({
      color: 0x607989,
      roughness: 0.76,
      metalness: 0.04,
    });

  const dark =
    new THREE.MeshStandardMaterial({
      color: 0x344d5b,
      roughness: 0.82,
    });

  const accent =
    new THREE.MeshStandardMaterial({
      color: 0x0fa8c5,
      roughness: 0.48,
      metalness: 0.14,
    });

  const waterMaterial =
    new THREE.MeshStandardMaterial({
      color: 0x155f7a,
      transparent: true,
      opacity: 0.40,
      roughness: 0.30,
    });

  const box = (
    sx: number,
    sy: number,
    sz: number,
    x: number,
    y: number,
    z: number,
    material: THREE.Material,
  ) => {
    const mesh =
      new THREE.Mesh(
        new THREE.BoxGeometry(sx, sy, sz),
        material,
      );

    mesh.position.set(x, y, z);

    group.add(mesh);

    return mesh;
  };

  const type =
    String(assetType || "").toLowerCase();

  /*
   * DAM / BARRAGE
   */
  if (
    type === "dam" ||
    type === "barrage"
  ) {
    const length =
      90 + a * 65;

    const height =
      15 + b * 15;

    const depth =
      12 + c * 9;

    const sections =
      5 + (seed % 7);

    box(
      length,
      height,
      depth,
      0,
      height / 2,
      0,
      main,
    );

    const sectionWidth =
      length / sections;

    for (
      let i = 0;
      i <= sections;
      i += 1
    ) {
      const x =
        -length / 2 +
        i * sectionWidth;

      box(
        1.0,
        height + 2.5,
        depth + 1.7,
        x,
        height / 2,
        0,
        dark,
      );
    }

    if (type === "barrage") {
      for (
        let i = 0;
        i < sections;
        i += 1
      ) {
        const x =
          -length / 2 +
          sectionWidth / 2 +
          i * sectionWidth;

        box(
          sectionWidth * 0.68,
          height * 0.55,
          0.5,
          x,
          height * 0.40,
          depth / 2 + 0.35,
          accent,
        );
      }
    }

    const water =
      box(
        length * 1.25,
        0.25,
        depth * 2.8,
        0,
        0.12,
        -depth * 1.05,
        waterMaterial,
      );

    water.userData.excludeFromMeasurement =
      true;

    water.userData.simrasContextPlane =
      true;
  }

  /*
   * BRIDGE / ROAD
   */
  else if (
    type === "bridge" ||
    type === "road"
  ) {
    const length =
      100 + a * 75;

    const width =
      10 + b * 6;

    const pierHeight =
      12 + c * 16;

    const piers =
      3 + (seed % 5);

    box(
      length,
      1.8,
      width,
      0,
      pierHeight,
      0,
      main,
    );

    for (
      let i = 0;
      i < piers;
      i += 1
    ) {
      const x =
        -length * 0.40 +
        (
          length * 0.80 *
          i /
          Math.max(piers - 1, 1)
        );

      box(
        2.3,
        pierHeight,
        3.4,
        x,
        pierHeight / 2,
        0,
        dark,
      );
    }

    box(
      length * 0.96,
      0.35,
      width * 0.68,
      0,
      pierHeight + 1.3,
      0,
      accent,
    );
  }

  /*
   * AIRPORT
   */
  else if (type === "airport") {
    const runway =
      125 + a * 50;

    const runwayWidth =
      15 + b * 8;

    box(
      runway,
      0.45,
      runwayWidth,
      0,
      0.23,
      0,
      dark,
    );

    box(
      34 + c * 18,
      9 + b * 7,
      20 + a * 10,
      -runway * 0.20,
      5,
      -runwayWidth * 1.35,
      main,
    );

    box(
      26,
      2.2,
      7,
      runway * 0.12,
      1.2,
      -runwayWidth * 0.78,
      accent,
    );
  }

  /*
   * TEMPLE
   */
  else if (type === "temple") {
    const base =
      27 + a * 13;

    box(
      base,
      3,
      base,
      0,
      1.5,
      0,
      main,
    );

    const levels =
      4 + (seed % 4);

    let currentY = 3;

    for (
      let level = 0;
      level < levels;
      level += 1
    ) {
      const scale =
        1 -
        level /
        (levels + 2);

      const size =
        base * 0.58 * scale;

      const levelHeight =
        4 + b * 1.6;

      box(
        size,
        levelHeight,
        size,
        0,
        currentY + levelHeight / 2,
        0,
        level % 2 === 0
          ? main
          : dark,
      );

      currentY += levelHeight;
    }

    const cone =
      new THREE.Mesh(
        new THREE.ConeGeometry(
          5 + c * 2,
          6 + a * 3,
          4,
        ),
        accent,
      );

    cone.position.y =
      currentY + 3;

    cone.rotation.y =
      Math.PI / 4;

    group.add(cone);
  }

  /*
   * GENERIC INFRASTRUCTURE
   */
  else {
    box(
      60 + a * 45,
      12 + b * 10,
      22 + c * 10,
      0,
      8,
      0,
      main,
    );
  }

  /*
   * Small deterministic visual variation.
   * This does NOT represent surveyed orientation.
   */
  group.rotation.y =
    (
      ((seed % 15) - 7) *
      Math.PI
    ) /
    180;

  root.add(group);

  root.userData.simrasFallback = {
    active: true,
    assetCode,
    reason:
      "SOURCE_GLB_FAILED_QUALITY_GATE",
    fidelity:
      "L1",
    geometryMode:
      "ASSET_SPECIFIC_APPROXIMATE",
    engineeringScaleVerified:
      false,
  };
}


function prepareAssetModel(
  root: THREE.Object3D,
  assetType = "",
  assetCode = "",
) {
  type MeshQuality = {
    mesh: THREE.Mesh;
    size: THREE.Vector3;
    footprint: number;
    footprintShare: number;
    verticalRatio: number;
  };

  root.updateWorldMatrix(
    true,
    true,
  );

  const rootBounds =
    new THREE.Box3().setFromObject(root);

  const rootSize =
    rootBounds.getSize(
      new THREE.Vector3(),
    );

  const rootFootprint =
    Math.max(
      rootSize.x * rootSize.z,
      0.000001,
    );

  const records: MeshQuality[] = [];

  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) {
      return;
    }

    if (
      child.name ===
      "SIMRAS_HOLOGRAM_OUTLINE"
    ) {
      return;
    }

    const bounds =
      new THREE.Box3().setFromObject(child);

    if (bounds.isEmpty()) {
      return;
    }

    const size =
      bounds.getSize(
        new THREE.Vector3(),
      );

    const footprint =
      Math.max(size.x, 0) *
      Math.max(size.z, 0);

    const narrowHorizontal =
      Math.max(
        Math.min(size.x, size.z),
        0.000001,
      );

    records.push({
      mesh: child,
      size,
      footprint,
      footprintShare:
        footprint / rootFootprint,
      verticalRatio:
        size.y / narrowHorizontal,
    });
  });

  const type =
    String(assetType || "").toLowerCase();

  const airport =
    type === "airport";

  /*
   * Detect giant flat context / image / terrain surfaces.
   *
   * Long dam walls are not classified by X length alone;
   * their narrow depth keeps the verticalRatio meaningful.
   */
  const contextCandidates =
    records.filter(
      (record) =>
        !airport &&
        record.verticalRatio < 0.025 &&
        record.footprintShare >= 0.18,
    );

  const structuralCandidates =
    records.filter(
      (record) =>
        airport ||
        record.verticalRatio >= 0.025 ||
        (
          record.size.y > 0.10 &&
          record.footprintShare < 0.18
        ),
    );

  const largestStructuralFootprint =
    structuralCandidates.reduce(
      (largest, record) =>
        Math.max(
          largest,
          record.footprint,
        ),
      0,
    );

  let excludedContextMeshes = 0;

  if (
    !airport &&
    structuralCandidates.length > 0
  ) {
    contextCandidates.forEach(
      (record) => {
        const dominant =
          record.footprintShare >= 0.30 ||
          record.footprint >=
            Math.max(
              largestStructuralFootprint * 1.4,
              0.001,
            );

        if (!dominant) {
          return;
        }

        record.mesh.visible =
          false;

        record.mesh.userData
          .excludeFromMeasurement =
          true;

        record.mesh.userData
          .simrasContextPlane =
          true;

        excludedContextMeshes += 1;
      },
    );
  }

  root.updateWorldMatrix(
    true,
    true,
  );

  let visibleMeshes = 0;
  let substantialMeshes = 0;

  root.traverse((child) => {
    if (
      !(child instanceof THREE.Mesh) ||
      child.visible === false ||
      child.userData
        .excludeFromMeasurement === true
    ) {
      return;
    }

    const bounds =
      new THREE.Box3().setFromObject(child);

    if (bounds.isEmpty()) {
      return;
    }

    visibleMeshes += 1;

    const size =
      bounds.getSize(
        new THREE.Vector3(),
      );

    if (
      size.x > 0.05 &&
      size.y > 0.05 &&
      size.z > 0.05
    ) {
      substantialMeshes += 1;
    }
  });

  let bounds =
    measurementBounds(root);

  let size =
    bounds.getSize(
      new THREE.Vector3(),
    );

  const horizontal =
    Math.max(
      size.x,
      size.z,
      0.000001,
    );

  const sceneVerticalRatio =
    size.y / horizontal;

  /*
   * Reject GLB when useful structural geometry is absent.
   */
  const qualityFailed =
    bounds.isEmpty() ||
    visibleMeshes === 0 ||
    (
      !airport &&
      substantialMeshes === 0
    ) ||
    (
      !airport &&
      sceneVerticalRatio < 0.001
    );

  if (qualityFailed) {
    installQualityFallback(
      root,
      assetType,
      assetCode,
    );

    root.updateWorldMatrix(
      true,
      true,
    );

    bounds =
      measurementBounds(root);

    size =
      bounds.getSize(
        new THREE.Vector3(),
      );
  }

  /*
   * Visual preparation.
   */
  root.traverse((child) => {
    if (
      !(child instanceof THREE.Mesh) ||
      child.visible === false ||
      child.userData
        .simrasContextPlane === true
    ) {
      return;
    }

    child.castShadow = true;
    child.receiveShadow = true;
  });

  root.updateWorldMatrix(
    true,
    true,
  );

  const structuralBounds =
    measurementBounds(root);

  if (!structuralBounds.isEmpty()) {
    const structuralSize =
      structuralBounds.getSize(
        new THREE.Vector3(),
      );

    const maxDimension =
      Math.max(
        structuralSize.x,
        structuralSize.y,
        structuralSize.z,
        1,
      );

    /*
     * Visual viewer units only.
     * NOT metres and NOT engineering scale.
     */
    const visualScale =
      132 / maxDimension;

    root.scale.multiplyScalar(
      visualScale,
    );

    root.updateWorldMatrix(
      true,
      true,
    );

    const scaledBounds =
      measurementBounds(root);

    const center =
      scaledBounds.getCenter(
        new THREE.Vector3(),
      );

    root.position.set(
      -center.x,
      -scaledBounds.min.y - 2.65,
      -center.z,
    );

    root.updateWorldMatrix(
      true,
      true,
    );
  }

  root.userData.simrasModelPreparation = {
    qualityGate:
      "SIMRAS_GLOBAL_TWIN_QUALITY_GATE_V2",

    sourceGlbAccepted:
      !qualityFailed,

    fallbackActive:
      qualityFailed,

    excludedContextMeshes,

    visibleMeshes,

    substantialMeshes,

    fidelity:
      "L1_UNLESS_SEPARATELY_VERIFIED",

    engineeringScaleVerified:
      false,

    officialDimensionsUsedAsMeshScale:
      false,
  };
}

function measurementBounds(root: THREE.Object3D) {
  const bounds = new THREE.Box3();
  let found = false;

  root.updateWorldMatrix(true, true);
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    if (child.userData.excludeFromMeasurement === true) return;

    const childBounds = new THREE.Box3().setFromObject(child);
    if (childBounds.isEmpty()) return;
    bounds.union(childBounds);
    found = true;
  });

  return found ? bounds : new THREE.Box3().setFromObject(root);
}

function addWorldLine(
  group: THREE.Group,
  start: THREE.Vector3,
  end: THREE.Vector3,
  color = 0xbdeff5,
) {
  const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.95,
    depthTest: false,
  });
  const line = new THREE.Line(geometry, material);
  line.renderOrder = 50;
  group.add(line);
}

function addWorldDot(
  group: THREE.Group,
  position: THREE.Vector3,
  radius: number,
) {
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 12, 8),
    new THREE.MeshBasicMaterial({
      color: 0xd8f8fb,
      depthTest: false,
    }),
  );
  dot.position.copy(position);
  dot.renderOrder = 51;
  group.add(dot);
}

function addWorldLabel(
  group: THREE.Group,
  text: string,
  position: THREE.Vector3,
  sceneSize: number,
) {
  const fontSize = 38;
  const horizontalPadding = 18;
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) return;

  context.font = `700 ${fontSize}px Inter, Arial, sans-serif`;
  const measuredWidth = Math.ceil(context.measureText(text).width);
  canvas.width = measuredWidth + horizontalPadding * 2;
  canvas.height = 68;

  context.fillStyle = "rgba(2, 18, 29, 0.96)";
  context.strokeStyle = "rgba(103, 232, 249, 0.9)";
  context.lineWidth = 3;
  context.beginPath();
  context.roundRect(1.5, 1.5, canvas.width - 3, canvas.height - 3, 12);
  context.fill();
  context.stroke();
  context.font = `700 ${fontSize}px Inter, Arial, sans-serif`;
  context.fillStyle = "#eefcff";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, canvas.width / 2, canvas.height / 2 + 1);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;

  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  const height = Math.max(sceneSize * 0.038, 1.8);
  const width = height * (canvas.width / canvas.height);
  sprite.scale.set(width, height, 1);
  sprite.position.copy(position);
  sprite.renderOrder = 60;
  group.add(sprite);
}

function createWorldDimensionAnnotations(
  owner: THREE.Group,
  content: THREE.Group,
  metrics: EngineeringMetric[],
  type: string,
) {
  const dimensions = new THREE.Group();
  dimensions.name = "SIMRAS_WORLD_DIMENSIONS";

  const worldBounds = measurementBounds(content);
  const worldMin = worldBounds.min.clone();
  const worldMax = worldBounds.max.clone();
  const min = owner.worldToLocal(worldMin);
  const max = owner.worldToLocal(worldMax);
  const size = new THREE.Vector3().subVectors(max, min);
  const center = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5);
  const sceneSize = Math.max(size.x, size.y, size.z, 1);
  const margin = sceneSize * 0.065;
  const dotRadius = Math.max(sceneSize * 0.005, 0.18);
  const length = metricByKey(metrics, "total_length_m", "runway_length_m");
  const width = metricByKey(metrics, "width_m", "runway_width_m", "gate_width_m");
  const height = metricByKey(
    metrics,
    "height_m",
    "terminal_height_m",
    "gopuram_height_m",
    "gate_height_m",
  );
  const counts = metrics.filter(
    (metric) =>
      ["span_count", "pier_count", "pillar_count", "gate_count"].includes(
        metric.key,
      ) && metric.status !== "UNAVAILABLE",
  );

  if (length) {
    const y = max.y + margin;
    const start = new THREE.Vector3(min.x, y, center.z);
    const end = new THREE.Vector3(max.x, y, center.z);
    addWorldLine(dimensions, start, end);
    addWorldDot(dimensions, start, dotRadius);
    addWorldDot(dimensions, end, dotRadius);
    addWorldLabel(
      dimensions,
      `${
        length.status === "VERIFIED" &&
        length.source.includes("Central Water Commission")
          ? "Length"
          : type === "airport"
            ? "Runway length"
            : "Total length"
      } ${length.value}`,
      new THREE.Vector3(center.x, y + margin * 0.32, center.z),
      sceneSize,
    );
  }

  if (height) {
    const x = max.x + margin;
    const start = new THREE.Vector3(x, min.y, center.z);
    const end = new THREE.Vector3(x, max.y, center.z);
    addWorldLine(dimensions, start, end);
    addWorldDot(dimensions, start, dotRadius);
    addWorldDot(dimensions, end, dotRadius);
    const heightLabel =
      height.key === "gate_height_m"
        ? "Gate height"
        : height.key === "gopuram_height_m"
          ? "Gopuram height"
          : height.key === "terminal_height_m"
            ? "Terminal height"
            : "Height";
    addWorldLabel(
      dimensions,
      `${
        height.status === "VERIFIED" &&
        height.source.includes("Central Water Commission")
          ? "Height"
          : heightLabel
      } ${height.value}`,
      new THREE.Vector3(x + margin * 0.65, center.y, center.z),
      sceneSize,
    );
  }

  if (width) {
    const y = min.y + Math.max(size.y * 0.24, margin * 0.5);
    const z = max.z + margin * 0.35;
    const gateWidth = width.key === "gate_width_m";
    const widthSpan = gateWidth
      ? Math.max(size.x / Math.max(parseNumber(metricByKey(metrics, "gate_count")?.value) ?? 1, 1), size.x * 0.045)
      : size.x * 0.23;
    const start = new THREE.Vector3(min.x, y, z);
    const end = new THREE.Vector3(Math.min(min.x + widthSpan, max.x), y, z);
    addWorldLine(dimensions, start, end);
    addWorldDot(dimensions, start, dotRadius);
    addWorldDot(dimensions, end, dotRadius);
    const widthLabel = gateWidth
      ? "Gate width"
      : width.key === "runway_width_m"
        ? "Runway width"
        : type === "bridge"
          ? "Deck width"
          : "Width / breadth";
    addWorldLabel(
      dimensions,
      `${widthLabel} ${width.value}`,
      new THREE.Vector3((start.x + end.x) / 2, y + margin * 0.42, z),
      sceneSize,
    );
  }

  if (counts.length > 0) {
    const label = counts.map((metric) => `${metric.label}: ${metric.value}`).join(" Ã‚Â· ");
    addWorldLabel(
      dimensions,
      label,
      new THREE.Vector3(center.x, min.y + size.y * 0.72, max.z + margin * 0.42),
      sceneSize,
    );
  }

  /*
   * SIMRAS_FOUR_ARM_TOPOLOGY_ANNOTATIONS
   *
   * Special handling for Sir Arthur Cotton Barrage four-arm structure
   */
  const fourArmMetrics = metrics.filter(
    (metric) =>
      [
        "dowleswaram_arm_vent_count",
        "ralli_arm_vent_count", 
        "madduru_arm_vent_count",
        "vijjeswaram_arm_vent_count",
      ].includes(metric.key) && metric.status !== "UNAVAILABLE",
  );

  if (fourArmMetrics.length > 0) {
    const armLabel = fourArmMetrics
      .map((metric) => {
        const armName = metric.key.replace("_arm_vent_count", "");
        const formattedName = armName.charAt(0).toUpperCase() + armName.slice(1);
        return `${formattedName}: ${metric.value}`;
      })
      .join(" | ");
    
    addWorldLabel(
      dimensions,
      `Four-arm vents: ${armLabel}`,
      new THREE.Vector3(center.x, min.y + size.y * 0.85, max.z + margin * 0.55),
      sceneSize,
    );
  }


  /*
   * SIMRAS_ENGINEERING_WORLD_LABELS_V3
   *
   * Evidence values below move with the 3D scene.
   */
  const extraMetrics: Array<[string, EngineeringMetric | undefined]> = [];

  let evidenceLabelIndex = 0;

  extraMetrics.forEach(
    ([label, metric]) => {
      if (
        !metric ||
        metric.status === "UNAVAILABLE"
      ) {
        return;
      }

      addWorldLabel(
        dimensions,
        `${label}: ${metric.value}`,
        new THREE.Vector3(
          center.x,
          max.y +
            margin *
              (
                1.25 +
                evidenceLabelIndex * 0.72
              ),
          max.z +
            margin * 0.30,
        ),
        sceneSize,
      );

      evidenceLabelIndex += 1;
    },
  );

  return dimensions;
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


  /*
   * SIMRAS_PRAKASAM_MARKINGS_V42
   * The existing road deck stays unchanged.
   */
  const roadMarking =
    new THREE.MeshStandardMaterial({
      color: 0xf0dc78,
      roughness: 0.72,
    });

  for (
    let i = 0;
    i < 18;
    i += 1
  ) {
    const x =
      -72 + i * 8.5;

    addMesh(
      group,
      new THREE.BoxGeometry(
        4.0,
        0.05,
        0.14,
      ),
      roadMarking,
      [
        x,
        gateHeight + 3.43,
        0,
      ],
    );
  }

}


/*
 * SIMRAS_CREST_ROAD_V42
 *
 * Visual-only L1 crest/service roadway.
 * This is not used as engineering evidence.
 */
function addSimrasCrestRoad(
  group: THREE.Group,
  length: number,
  y: number,
  width = 7.4,
) {
  const asphalt =
    new THREE.MeshStandardMaterial({
      color: 0x242b31,
      roughness: 0.97,
    });

  const barrier =
    new THREE.MeshStandardMaterial({
      color: 0xaebac2,
      roughness: 0.84,
    });

  const marking =
    new THREE.MeshStandardMaterial({
      color: 0xf1dc78,
      roughness: 0.72,
    });

  addMesh(
    group,
    new THREE.BoxGeometry(
      length,
      0.52,
      width,
    ),
    asphalt,
    [0, y, 0],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      length,
      0.68,
      0.28,
    ),
    barrier,
    [
      0,
      y + 0.54,
      width / 2 - 0.16,
    ],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      length,
      0.68,
      0.28,
    ),
    barrier,
    [
      0,
      y + 0.54,
      -width / 2 + 0.16,
    ],
  );

  const dashCount =
    Math.max(
      8,
      Math.floor(length / 9),
    );

  const spacing =
    length / dashCount;

  for (
    let i = 0;
    i < dashCount;
    i += 1
  ) {
    const x =
      -length / 2 +
      spacing / 2 +
      i * spacing;

    addMesh(
      group,
      new THREE.BoxGeometry(
        spacing * 0.44,
        0.05,
        0.13,
      ),
      marking,
      [
        x,
        y + 0.29,
        0,
      ],
    );
  }

  group.userData.simrasRoadDeck = {
    visualOnly: true,
    engineeringEvidence: false,
  };
}


/*
 * SIMRAS_GENERIC_BARRAGE_V42
 *
 * Unique L1 visual barrage.
 * Visual bay count is not reported as actual gate count.
 */
function buildSimrasBarrage(
  group: THREE.Group,
  assetCode: string,
) {
  const concrete =
    new THREE.MeshStandardMaterial({
      color: 0xb8c3cb,
      roughness: 0.84,
    });

  const pier =
    new THREE.MeshStandardMaterial({
      color: 0x738590,
      roughness: 0.87,
    });

  const gate =
    new THREE.MeshStandardMaterial({
      color: 0x277c99,
      roughness: 0.54,
      metalness: 0.20,
    });

  let seed = 11;

  for (
    let i = 0;
    i < assetCode.length;
    i += 1
  ) {
    seed =
      (
        seed * 31 +
        assetCode.charCodeAt(i)
      ) >>> 0;
  }

  const length =
    112 + seed % 34;

  const height =
    7.6 +
    ((seed >>> 5) % 22) / 10;

  const visualBays =
    10 + seed % 8;

  const pierWidth =
    1.15;

  const bayWidth =
    (
      length -
      pierWidth *
        (visualBays + 1)
    ) /
    visualBays;

  addWater(
    group,
    length * 1.55,
    72,
    -2.1,
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      length + 8,
      2,
      11,
    ),
    concrete,
    [0, -0.8, 0],
  );

  for (
    let i = 0;
    i <= visualBays;
    i += 1
  ) {
    const x =
      -length / 2 +
      i *
        (bayWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(
        pierWidth,
        height + 4,
        9,
      ),
      pier,
      [
        x,
        height / 2 + 0.5,
        0,
      ],
    );
  }

  for (
    let i = 0;
    i < visualBays;
    i += 1
  ) {
    const x =
      -length / 2 +
      pierWidth +
      bayWidth / 2 +
      i *
        (bayWidth + pierWidth);

    addMesh(
      group,
      new THREE.BoxGeometry(
        Math.max(
          bayWidth * 0.84,
          0.8,
        ),
        height,
        0.38,
      ),
      gate,
      [
        x,
        height / 2,
        1.55,
      ],
    );
  }

  addMesh(
    group,
    new THREE.BoxGeometry(
      length + 5,
      0.8,
      8.7,
    ),
    concrete,
    [
      0,
      height + 1.45,
      0,
    ],
  );

  addSimrasCrestRoad(
    group,
    length + 7,
    height + 3.05,
    8.6,
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      14,
      height * 0.85,
      25,
    ),
    concrete,
    [
      -length / 2 - 8,
      height * 0.32,
      0,
    ],
  );

  addMesh(
    group,
    new THREE.BoxGeometry(
      14,
      height * 0.85,
      25,
    ),
    concrete,
    [
      length / 2 + 8,
      height * 0.32,
      0,
    ],
  );

  group.userData.simrasApproximateBarrage = {
    assetCode,
    fidelity: "L1",
    visualBayCount: visualBays,
    visualBayCountIsEvidence: false,
  };
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


  /*
   * SIMRAS_DAM_ROAD_V42
   */
  addSimrasCrestRoad(
    group,
    wallLength * 0.94,
    wallHeight - 1.25,
    isPolavaram ? 8.3 : 7.4,
  );

  // Visual downstream apron.
  addMesh(
    group,
    new THREE.BoxGeometry(
      wallLength * 0.88,
      0.72,
      15,
    ),
    concrete,
    [0, -1.18, 9],
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
  /*
   * SIMRAS_VERIFIED_WATER_ROUTE_V13
   */
  const verifiedWaterSpec =
    buildVerifiedWaterTopologyTwin(
      group,
      assetCode,
    );

  if (verifiedWaterSpec) {
    return verifiedWaterSpec;
  }


  if (assetCode === "AP_DAM_00001") {
    buildPrakasamBarrage(group);

    return {
      title: "Source-linked barrage model",
      fidelity: damBarrageFidelityLabel(assetCode, "L2 SOURCE-BACKED PARAMETRIC TWIN"),
      evidence:
        "Prakasam identity is source-linked. The current visible geometry remains an L1 engineering approximation until strict-source engineering dimensions are linked.",
      dimensions: ["Strict-source engineering dimensions not yet available"],
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
        fidelity: damBarrageFidelityLabel(assetCode, "L1/L2 SOURCE-AWARE VISUAL TWIN"),
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
      fidelity: damBarrageFidelityLabel(assetCode, "L1/L2 SOURCE-AWARE VISUAL TWIN"),
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
      fidelity: damBarrageFidelityLabel(assetCode, "L1/L2 SOURCE-AWARE VISUAL TWIN"),
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
      fidelity: damBarrageFidelityLabel(assetCode, "L1 ASSET-SPECIFIC VISUAL TWIN"),
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
    buildSimrasBarrage(group, assetCode);

    return {
      title: "Barrage engineering visual twin",
      fidelity: damBarrageFidelityLabel(assetCode, "L1/L2 SOURCE-AWARE PARAMETRIC TWIN"),
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
    buildAssetSpecificDam(group, assetCode, name);

    return {
      title: "Dam engineering visual twin",
      fidelity: damBarrageFidelityLabel(assetCode, "L1/L2 SOURCE-AWARE PARAMETRIC TWIN"),
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
    fidelity: damBarrageFidelityLabel(assetCode, "L1 VISUAL TWIN"),
    evidence:
      "A generic infrastructure form is used because no verified type-specific engineering geometry is available.",
    dimensions: ["Verified geometry not available"],
  };
}

/*
 * SIMRAS_V23_ASSET_SPECIFIC_ENGINEERING_TWIN
 *
 * One clean Three.js twin.
 * Zero map/tile dependencies.
 * Loads one unique per-asset GLB when available.
 * Zero duplicate viewer.
 */
export default function RealityTwinAssetViewer({
  assetCode,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const dimensionGroupRef = useRef<THREE.Group | null>(null);
  const dimensionsVisibleRef = useRef(true);
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [sceneReady, setSceneReady] = useState(false);
  const [spec, setSpec] = useState<TwinSpec | null>(null);
  const [dimensionsVisible, setDimensionsVisible] = useState(true);

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

  const engineeringMetrics = useMemo(() => {
    /*
     * SIMRAS_VERIFIED_WATER_METRICS_V13
     */
    const metrics =
      buildEngineeringMetrics(
        selectedAsset,
        assetCode ?? "",
        type,
      );

    const verified =
      getVerifiedWaterEngineeringValues(
        assetCode,
      );

    for (const item of verified) {
      const verifiedMetric:
        EngineeringMetric = {
          key: item.key,
          label: item.label,
          value: item.value,
          status: "VERIFIED",
          source:
            "Verified Real Twin topology manifest",
          category:
            item.category,
        };

      const index =
        metrics.findIndex(
          (metric) =>
            metric.key ===
            item.key,
        );

      if (index >= 0) {
        metrics[index] =
          verifiedMetric;
      } else {
        metrics.push(
          verifiedMetric,
        );
      }
    }

    return metrics;
  }, [
    selectedAsset,
    assetCode,
    type,
  ]);

  /*
   * SIMRAS_CLEAN_3D_METRICS_V42
   *
   * Dam/barrage scene labels:
   *   Length
   *   Height
   *   No. of gates
   *
   * Remaining evidence stays in the side panel.
   */
  const dimensionOverlayMetrics = useMemo(() => {
    /*
     * SIMRAS_GLOBAL_ASSET_DIMENSIONS_V2
     *
     * Dimension annotations are supported for:
     * DAM
     * BARRAGE
     * BRIDGE
     * AIRPORT
     * TEMPLE
     *
     * Only existing source/evidence-backed values are rendered.
     * The visual 3D mesh is never used to invent dimensions.
     */

    const aliasesByType:
      Record<string, Set<string>> = {

      dam: new Set([
        "total_length_m",
        "length_m",
        "dam_length_m",

        "width_m",
        "breadth_m",
        "crest_width_m",
        "dam_width_m",

        "height_m",
        "dam_height_m",
        "maximum_dam_height_m",

        "gate_count",
        "number_of_gates",

        "gate_width_m",
        "gate_height_m",

        "spillway_length_m",
      ]),

      barrage: new Set([
        "total_length_m",
        "length_m",
        "barrage_length_m",

        "width_m",
        "breadth_m",

        "height_m",
        "barrage_height_m",

        "gate_count",
        "number_of_gates",
        "regulator_count",

        "gate_width_m",
        "gate_height_m",
      ]),

      bridge: new Set([
        "total_length_m",
        "length_m",
        "bridge_length_m",

        "width_m",
        "bridge_width_m",
        "deck_width_m",

        "height_m",
        "bridge_height_m",

        "clearance_m",
        "vertical_clearance_m",

        "span_count",
        "number_of_spans",

        "pier_count",
        "number_of_piers",

        "pillar_count",
        "number_of_pillars",

        "main_span_m",
        "span_length_m",
      ]),

      airport: new Set([
        "runway_length_m",
        "runway_width_m",

        "total_length_m",
        "length_m",

        "width_m",

        "terminal_length_m",
        "terminal_width_m",
        "terminal_height_m",

        "airport_area_m2",
        "airport_area_sq_m",
      ]),

      temple: new Set([
        "total_length_m",
        "length_m",
        "temple_length_m",

        "width_m",
        "temple_width_m",
        "breadth_m",

        "height_m",
        "temple_height_m",

        "gopuram_height_m",

        "prakara_count",
        "number_of_prakarams",
      ]),
    };

    const allowed =
      aliasesByType[type] ??
      new Set([
        "total_length_m",
        "length_m",
        "width_m",
        "height_m",
      ]);

    const unavailableValues =
      new Set([
        "",
        "N/A",
        "NA",
        "NULL",
        "NONE",
        "UNKNOWN",
        "WITHHELD",
        "NOT VERIFIED",
        "NOT_VERIFIED",
        "NOT AVAILABLE",
        "NOT_AVAILABLE",
      ]);

    return engineeringMetrics.filter(
      (metric) => {
        if (!allowed.has(metric.key)) {
          return false;
        }

        /*
         * SIMRAS_REAL_DIMENSIONS_ONLY_V1
         *
         * Moving engineering dimensions must be VERIFIED.
         * ESTIMATED values can remain available elsewhere in
         * the UI, but are not drawn as authoritative geometry
         * annotations.
         */
        if (metric.status !== "VERIFIED") {
          return false;
        }

        const normalized =
          String(
            metric.value ?? "",
          )
            .trim()
            .toUpperCase();

        if (
          unavailableValues.has(
            normalized,
          )
        ) {
          return false;
        }

        return true;
      },
    );
  }, [engineeringMetrics, type]);



  /*
   * SIMRAS_ENGINEERING_EVIDENCE_PANEL_V3
   *
   * Uses only existing source-linked EngineeringMetric values.
   * Missing fields remain NOT VERIFIED.
   */
  const engineeringEvidenceCards = useMemo(() => {
    const resolve = (
      key: string,
      label: string,
      ...metricKeys: string[]
    ) => {
      const metric =
        metricByKey(
          engineeringMetrics,
          ...metricKeys,
        );

      const available =
        Boolean(metric) &&
        metric?.status !== "UNAVAILABLE";

      return {
        key,
        label,

        value:
          available && metric
            ? metric.value
            : "NOT VERIFIED",

        source:
          available && metric
            ? metric.source
            : "Evidence required",

        available,
      };
    };

    return [
      resolve(
        "length",
        "Length",
        "total_length_m",
        "runway_length_m",
      ),

      resolve(
        "width",
        "Width / Breadth",
        "width_m",
        "breadth_m",
        "runway_width_m",
      ),

      resolve(
        "height",
        "Height",
        "height_m",
        "terminal_height_m",
        "gopuram_height_m",
      ),

      resolve(
        "area",
        "Reservoir / Occupied Area",
        "reservoir_area",
        "reservoir_area_m2",
        "water_spread_area_m2",
        "land_area_m2",
      ),

      resolve(
        "gross_storage",
        "Gross Water Storage",
        "gross_storage_capacity",
        "storage_capacity",
        "water_capacity",
      ),

      resolve(
        "live_storage",
        "Live / Effective Storage",
        "effective_storage_capacity",
        "live_storage_capacity",
      ),

      resolve(
        "spillway",
        "Spillway / Discharge Capacity",
        "designed_spillway_capacity",
        "spillway_capacity",
        "discharge_capacity",
      ),

      resolve(
        "gates",
        "No. of Gates",
        "gate_count",
      ),

      resolve(
        "gate_width",
        "Gate Width",
        "gate_width_m",
      ),

      resolve(
        "gate_height",
        "Gate Height",
        "gate_height_m",
      ),

      resolve(
        "flow_speed",
        "Water / Flow Speed",
        "water_velocity_mps",
        "flow_velocity_mps",
        "flow_speed_mps",
      ),

      resolve(
        "year",
        "Built / Completion Year",
        "construction_year",
        "completion_year",
        "built_year",
      ),
    ];
  }, [engineeringMetrics]);



  useEffect(() => {
    dimensionsVisibleRef.current = dimensionsVisible;
    if (dimensionGroupRef.current) {
      dimensionGroupRef.current.visible = dimensionsVisible;
    }
  }, [dimensionsVisible]);

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

    const contentGroup = new THREE.Group();
    group.add(contentGroup);

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

    const grid = new THREE.GridHelper(210, 32, 0x35bdd1, 0x123f52);
    grid.position.y = -2.65;
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.38;
    group.add(grid);

    const builtSpec = buildTwin(
      contentGroup,
      assetCode,
      type,
      name,
    );

    setSpec({
      ...builtSpec,
      title: "Loading unique asset-specific 3D modelÃ¢â‚¬Â¦",
    });

    const fitScene = () => {
      group.position.set(0, 0, 0);

      const bounds = measurementBounds(contentGroup);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());

      group.position.sub(center);

      const maxDimension = Math.max(size.x, size.y, size.z, 1);
      const distance = maxDimension * 0.95;

      camera.near = Math.max(maxDimension / 2000, 0.05);
      camera.far = Math.max(maxDimension * 18, 1000);
      camera.position.set(distance, distance * 0.62, distance * 0.78);
      camera.updateProjectionMatrix();

      controls.target.set(0, 0, 0);
      controls.minDistance = maxDimension * 0.18;
      controls.maxDistance = maxDimension * 5.5;
      controls.update();
    };

    fitScene();

    let worldDimensions: THREE.Group | null = null;
    const refreshWorldDimensions = () => {
      if (worldDimensions) {
        group.remove(worldDimensions);
        disposeDimensionAnnotations(worldDimensions);
      }

      group.updateMatrixWorld(true);
      worldDimensions = createWorldDimensionAnnotations(
        group,
        contentGroup,
        dimensionOverlayMetrics,
        type,
      );
      worldDimensions.visible = dimensionsVisibleRef.current;
      group.add(worldDimensions);
      dimensionGroupRef.current = worldDimensions;
    };

    refreshWorldDimensions();

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

    if (
      isVerifiedWaterTopologyAsset(
        assetCode,
      ) ||
      assetCode === "AP_BAR_WRIS_B00131"
    ) {
      /*
       * SIMRAS_VERIFIED_WATER_GLB_LOCK_V13
       *
       * The source-backed model created by buildTwin stays
       * visible. An unverified GLB cannot replace it.
       */
      setSpec(builtSpec);
    } else {
      const loader = new GLTFLoader();
      const modelUrl = `/reality-twin/models/${encodeURIComponent(assetCode)}/${encodeURIComponent(assetCode)}.glb`;

      loader.load(
        modelUrl,
        (gltf) => {
          if (disposed) {
            disposeObject(gltf.scene);
            return;
          }

          disposeObject(contentGroup);
          contentGroup.clear();
          prepareAssetModel(gltf.scene, type, assetCode ?? "");
          contentGroup.add(gltf.scene);

          setSpec({
            ...builtSpec,
            title: "Asset-specific approximate 3D representation",
            fidelity: damBarrageFidelityLabel(assetCode, "ASSET-SPECIFIC GLB + SOURCE-LINKED ENGINEERING DATA"),
            evidence:
              "The selected asset's own 3D model is displayed. Dimension labels and engineering values remain source-linked and are not inferred from visual model scale.",
          });

          if (worldDimensions) {
            group.remove(worldDimensions);
            disposeDimensionAnnotations(worldDimensions);
            worldDimensions = null;
          }
          fitScene();
          refreshWorldDimensions();
        },
        undefined,
        () => {
          if (disposed) return;

          setSpec({
            ...builtSpec,
            title: `${builtSpec.title} Ã¢â‚¬â€ procedural fallback`,
            evidence: `${builtSpec.evidence} The unique ${assetCode} GLB was not available, so this asset is clearly marked as a fallback.`,
          });
        },
      );
    }

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();

      if (dimensionGroupRef.current === worldDimensions) {
        dimensionGroupRef.current = null;
      }

      if (worldDimensions) {
        group.remove(worldDimensions);
        disposeDimensionAnnotations(worldDimensions);
        worldDimensions = null;
      }
      disposeObject(group);

      renderer.dispose();
      host.replaceChildren();
    };
  }, [assetCode, type, name, engineeringMetrics]);

  return (
    <div
      data-simras-reality-view="V23_ASSET_SPECIFIC_ENGINEERING_TWIN"
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

        <button
          type="button"
          className="rt-dimension-toggle"
          aria-pressed={dimensionsVisible}
          onClick={() => setDimensionsVisible((visible) => !visible)}
        >
          {dimensionsVisible ? "Hide dimensions" : "Show dimensions"}
        </button>

        {dimensionsVisible && (
          <div className="pointer-events-auto absolute right-4 top-4 z-30 w-[280px] max-w-[calc(100%-2rem)] max-h-[42%] overflow-y-auto rounded-xl border border-cyan-400/20 bg-slate-950/88 p-3 shadow-xl backdrop-blur-md">

            <div className="mb-3 flex items-start justify-between gap-3">

              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">
                  Engineering Digital Twin
                </div>

                <div className="mt-1 text-sm font-semibold text-white">
                  Dimensions ? Water ? Capacity ? Gates
                </div>
              </div>

              <div className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-emerald-300">
                Evidence gated
              </div>

            </div>

            <div className="grid grid-cols-2 gap-2">

              {engineeringEvidenceCards
                .filter(
                  (card) =>
                    card.key !== "gross_storage" &&
                    card.key !== "live_storage",
                )
                .filter((card) => card.available).map(
                (card) => (
                  <div
                    key={card.key}
                    className={`rounded-xl border p-3 ${
                      card.available
                        ? "border-cyan-400/20 bg-cyan-400/[0.04]"
                        : "border-amber-400/15 bg-amber-400/[0.03]"
                    }`}
                  >

                    <div className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-400">
                      {card.label}
                    </div>

                    <div
                      className={`mt-1 break-words text-sm font-bold ${
                        card.available
                          ? "text-white"
                          : "text-amber-300"
                      }`}
                    >
                      {card.value}
                    </div>

                    <div className="mt-1 text-[9px] leading-4 text-slate-500">
                      {card.source}
                    </div>

                  </div>
                ),
              )}

            </div>

            <div className="mt-3 rounded-lg border border-slate-700/60 bg-slate-900/70 px-3 py-2 text-[9px] leading-4 text-slate-400">
              Only verified or source-linked engineering values are displayed.
              Missing values remain NOT VERIFIED. L1 visual geometry is never
              treated as a measurement source.
            </div>

          </div>
        )}


      </div>

      <section className="rt-engineering-panel">
        <header className="rt-engineering-header">
          <div>
            <span>INFRASTRUCTURE INFORMATION</span>
            <h3>Engineering specifications</h3>
            <p>
              Asset-specific dimensions, structural details, construction data,
              and hydrology. Missing fields are intentionally not fabricated.
            </p>
          </div>

          <div className="rt-evidence-legend" aria-label="Evidence status legend">
            <span data-status="VERIFIED">Verified</span>
            <span data-status="ESTIMATED">Estimated</span>
            <span data-status="UNAVAILABLE">Unavailable</span>
          </div>
        </header>

        <div className="rt-engineering-groups">
          {(
            [
              "Dimensions",
              "Structure",
              "Construction",
              "Water / capacity",
            ] as EngineeringCategory[]
          ).map((category) => {
            const categoryMetrics = engineeringMetrics.filter(
              (metric) => metric.category === category,
            );

            if (categoryMetrics.length === 0) return null;

            return (
              <article className="rt-engineering-group" key={category}>
                <h4>{category}</h4>
                <div className="rt-engineering-grid">
                  {categoryMetrics.map((metric) => (
                    <div
                      className="rt-engineering-field"
                      data-status={metric.status}
                      key={metric.key}
                    >
                      <div className="rt-engineering-field-head">
                        <span>{metric.label}</span>
                        <small data-status={metric.status}>
                          {metric.status}
                        </small>
                      </div>
                      <strong>{metric.value}</strong>
                      <p title={metric.source}>{metric.source}</p>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </section>

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





