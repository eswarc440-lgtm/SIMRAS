import * as THREE from "three";

/*
 * SIMRAS_VERIFIED_WATER_TOPOLOGY_V13
 *
 * SOURCE-BACKED TOPOLOGY
 *
 * Exact known component counts/dimensions are read from
 * real_twin_verified_topology_v1.json.
 *
 * Detailed shapes or positions without drawings/survey remain
 * visual approximations and are not promoted to L2/L3.
 */

type WaterAsset = {
  asset_code: string;
  asset_name: string;
  asset_type: string;
  topology_status: string;
  dimension_status: string;
  structure: Record<string, unknown>;
};

export type VerifiedWaterTwinSpec = {
  title: string;
  fidelity: string;
  evidence: string;
  dimensions: string[];
};

export type VerifiedWaterMetric = {
  key: string;
  label: string;
  value: string;
  category:
    | "Dimensions"
    | "Structure"
    | "Construction"
    | "Water / capacity";
};

const WATER: WaterAsset[] =
[
  {
    "asset_code": "AP_DAM_00001",
    "asset_name": "Prakasam Barrage",
    "asset_type": "BARRAGE",
    "topology_status": "OFFICIAL_TOPOLOGY_VERIFIED",
    "dimension_status": "OFFICIAL_ENGINEERING_VERIFIED",
    "structure": {
      "structural_type": "gated barrage",
      "main_length_m": 1232.92,
      "regulator_count": 70,
      "regulator_width_m": 12.19,
      "regulator_height_m": 3.66,
      "left_scouring_sluice_count": 6,
      "right_scouring_sluice_count": 8,
      "scouring_sluice_width_m": 5.18,
      "scouring_sluice_height_m": 3.66,
      "water_spread_area_sq_km": 30.0,
      "completion_year": 1957
    }
  },
  {
    "asset_code": "AP_DAM_00002",
    "asset_name": "Polavaram Irrigation Project",
    "asset_type": "DAM",
    "topology_status": "OFFICIAL_TOPOLOGY_VERIFIED",
    "dimension_status": "OFFICIAL_ENGINEERING_VERIFIED",
    "structure": {
      "structural_type": "earth-cum-rock-fill dam plus gated concrete spillway",
      "earth_rockfill_total_length_m": 2454.0,
      "maximum_dam_height_m": 50.0,
      "spillway_length_m": 1118.4,
      "radial_gate_count": 48,
      "radial_gate_width_m": 16.0,
      "radial_gate_height_m": 20.0,
      "powerhouse_installed_capacity_mw": 960,
      "power_unit_count": 12,
      "power_unit_capacity_mw": 80,
      "live_reservoir_capacity_tmc": 75.2,
      "spillway_design_discharge_cumec": 141435
    }
  },
  {
    "asset_code": "AP_DAM_NWDP_AP01VH0059",
    "asset_name": "Srisailam Project (N.S.R.S.P)",
    "asset_type": "DAM",
    "topology_status": "OFFICIAL_TOPOLOGY_VERIFIED",
    "dimension_status": "OFFICIAL_ENGINEERING_VERIFIED",
    "structure": {
      "structural_type": "concrete gravity dam",
      "dam_length_m": 512.0,
      "dam_height_m": 145.0,
      "radial_crest_gate_count": 12,
      "radial_gate_width_m": 18.3,
      "radial_gate_height_m": 16.7,
      "river_sluice_count": 2,
      "river_sluice_width_m": 3.65,
      "river_sluice_height_m": 9.14,
      "gross_storage_mcm": 6110.9,
      "live_storage_mcm": 6014.17,
      "designed_spillway_capacity_m3s": 38369
    }
  },
  {
    "asset_code": "AP_DAM_WRIS_AP01HH0062",
    "asset_name": "Somasila Reservoir",
    "asset_type": "DAM",
    "topology_status": "PARTIAL_OFFICIAL_TOPOLOGY",
    "dimension_status": "OFFICIAL_STATIC_ENGINEERING_VERIFIED",
    "structure": {
      "structural_type": "concrete gravity",
      "dam_length_m": 760.0,
      "dam_height_m": 39.0,
      "gross_storage_mcm": 2208.37,
      "live_storage_mcm": 1994.1,
      "designed_spillway_capacity_m3s": 22375,
      "gate_count": null,
      "gate_count_status": "NOT_VERIFIED"
    }
  },
  {
    "asset_code": "AP_BAR_WRIS_B00131",
    "asset_name": "Sir Arthur Cotton Barrage",
    "asset_type": "BARRAGE",
    "topology_status": "OFFICIAL_TOPOLOGY_VERIFIED",
    "dimension_status": "OFFICIAL_ENGINEERING_VERIFIED",
    "structure": {
      "structural_type": "four-arm gated barrage on RCC raft",
      "total_length_m": 3592.67,
      "height_m": 10.6,
      "gate_count": 175,
      "gate_width_m": 18.29,
      "gate_height_m": 3.34,
      "pier_width_m": 2.13,
      "road_width_m": 7.50,
      "dowleswaram_arm_length_m": 1437.92,
      "dowleswaram_arm_vent_count": 70,
      "ralli_arm_length_m": 884.45,
      "ralli_arm_vent_count": 43,
      "madduru_arm_length_m": 469.66,
      "madduru_arm_vent_count": 23,
      "vijjeswaram_arm_length_m": 800.64,
      "vijjeswaram_arm_vent_count": 39,
      "gross_storage_mcm": 83,
      "live_storage_mcm": 49
    }
  }
];

const BY_CODE =
  new Map(
    WATER.map(
      (asset) => [
        asset.asset_code,
        asset,
      ],
    ),
  );


function n(
  asset: WaterAsset,
  key: string,
): number | null {
  const value = asset.structure[key];

  return (
    typeof value === "number" &&
    Number.isFinite(value)
  )
    ? value
    : null;
}


function req(
  asset: WaterAsset,
  key: string,
): number {
  const value = n(asset, key);

  if (value === null) {
    throw new Error(
      `${asset.asset_code}: missing ${key}`,
    );
  }

  return value;
}


const concrete =
  new THREE.MeshStandardMaterial({
    color: 0xb7c0c6,
    roughness: 0.84,
  });

const darkConcrete =
  new THREE.MeshStandardMaterial({
    color: 0x6d7d87,
    roughness: 0.87,
  });

const gateMaterial =
  new THREE.MeshStandardMaterial({
    color: 0x247c99,
    roughness: 0.53,
    metalness: 0.20,
  });

const earthMaterial =
  new THREE.MeshStandardMaterial({
    color: 0x766b54,
    roughness: 0.98,
  });

const roadMaterial =
  new THREE.MeshStandardMaterial({
    color: 0x262c31,
    roughness: 0.98,
  });

const markingMaterial =
  new THREE.MeshStandardMaterial({
    color: 0xf2e7aa,
    roughness: 0.76,
  });

const waterMaterial =
  new THREE.MeshStandardMaterial({
    color: 0x176f98,
    transparent: true,
    opacity: 0.58,
    roughness: 0.32,
  });


function box(
  group: THREE.Group,
  sx: number,
  sy: number,
  sz: number,
  x: number,
  y: number,
  z: number,
  material: THREE.Material,
  name: string,
) {
  const mesh =
    new THREE.Mesh(
      new THREE.BoxGeometry(
        sx,
        sy,
        sz,
      ),
      material,
    );

  mesh.position.set(
    x,
    y,
    z,
  );

  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);

  return mesh;
}


function water(
  group: THREE.Group,
  length: number,
  depth: number,
) {
  box(
    group,
    length,
    0.18,
    depth,
    0,
    -0.28,
    0,
    waterMaterial,
    "SIMRAS_WATER",
  );
}


function road(
  group: THREE.Group,
  length: number,
  y: number,
  width: number,
  prefix: string,
) {
  box(
    group,
    length,
    0.24,
    width,
    0,
    y,
    0,
    roadMaterial,
    `${prefix}_ROAD`,
  );

  box(
    group,
    length,
    0.55,
    0.24,
    0,
    y + 0.39,
    width / 2,
    concrete,
    `${prefix}_PARAPET_A`,
  );

  box(
    group,
    length,
    0.55,
    0.24,
    0,
    y + 0.39,
    -width / 2,
    concrete,
    `${prefix}_PARAPET_B`,
  );

  const count =
    Math.max(
      10,
      Math.floor(length / 7),
    );

  const spacing =
    length / count;

  for (
    let i = 0;
    i < count;
    i += 1
  ) {
    box(
      group,
      spacing * 0.43,
      0.025,
      0.10,
      -length / 2 +
        spacing / 2 +
        i * spacing,
      y + 0.14,
      0,
      markingMaterial,
      `${prefix}_ROAD_MARK_${i}`,
    );
  }
}


function gateArray(
  group: THREE.Group,
  prefix: string,
  count: number,
  totalLength: number,
  sourceGateWidth: number,
  gateHeight: number,
  pierHeight: number,
  depth: number,
  centerX = 0,
  centerZ = 0,
) {
  /*
   * count and sourceGateWidth are source-backed.
   * Remaining pier width is only visual spacing.
   */

  const gatesWidth =
    count *
    sourceGateWidth;

  const remaining =
    Math.max(
      totalLength -
        gatesWidth,
      totalLength * 0.04,
    );

  const pierWidth =
    remaining /
    (count + 1);

  const actualLength =
    gatesWidth +
    pierWidth *
      (count + 1);

  const start =
    centerX -
    actualLength / 2;

  for (
    let i = 0;
    i <= count;
    i += 1
  ) {
    const x =
      start +
      pierWidth / 2 +
      i *
      (
        sourceGateWidth +
        pierWidth
      );

    box(
      group,
      Math.max(
        pierWidth * 0.90,
        0.08,
      ),
      pierHeight,
      depth,
      x,
      pierHeight / 2,
      centerZ,
      darkConcrete,
      `${prefix}_PIER_${String(i + 1).padStart(3, "0")}`,
    );
  }

  for (
    let i = 0;
    i < count;
    i += 1
  ) {
    const x =
      start +
      pierWidth +
      sourceGateWidth / 2 +
      i *
      (
        sourceGateWidth +
        pierWidth
      );

    box(
      group,
      sourceGateWidth * 0.92,
      gateHeight,
      0.28,
      x,
      gateHeight / 2,
      centerZ +
        depth / 2 +
        0.16,
      gateMaterial,
      `${prefix}_GATE_${String(i + 1).padStart(3, "0")}`,
    );
  }
}


function embankment(
  group: THREE.Group,
  length: number,
  height: number,
  centerX: number,
  name: string,
) {
  const shape =
    new THREE.Shape();

  shape.moveTo(
    -11,
    0,
  );

  shape.lineTo(
    11,
    0,
  );

  shape.lineTo(
    3.0,
    height,
  );

  shape.lineTo(
    -3.0,
    height,
  );

  shape.closePath();

  const geometry =
    new THREE.ExtrudeGeometry(
      shape,
      {
        depth: length,
        bevelEnabled: false,
      },
    );

  geometry.rotateY(
    Math.PI / 2,
  );

  geometry.translate(
    -length / 2,
    0,
    0,
  );

  const mesh =
    new THREE.Mesh(
      geometry,
      earthMaterial,
    );

  mesh.position.x =
    centerX;

  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);
}


/*
 * ==========================================================
 * PRAKASAM
 * 70 regulators
 * 6 left scouring sluices
 * 8 right scouring sluices
 * ==========================================================
 */
function buildPrakasam(
  group: THREE.Group,
  asset: WaterAsset,
) {
  const lengthM =
    req(
      asset,
      "main_length_m",
    );

  const gates =
    req(
      asset,
      "regulator_count",
    );

  const gateWidthM =
    req(
      asset,
      "regulator_width_m",
    );

  const gateHeightM =
    req(
      asset,
      "regulator_height_m",
    );

  const leftScour =
    req(
      asset,
      "left_scouring_sluice_count",
    );

  const rightScour =
    req(
      asset,
      "right_scouring_sluice_count",
    );

  const scourWidthM =
    req(
      asset,
      "scouring_sluice_width_m",
    );

  const scourHeightM =
    req(
      asset,
      "scouring_sluice_height_m",
    );

  const scale = 0.10;

  const length =
    lengthM * scale;

  const gateWidth =
    gateWidthM * scale;

  const gateHeight =
    gateHeightM * scale;

  /*
   * Existing official level differences.
   */
  const regulatorFloorRL =
    12.21;

  const roadRL =
    25.02;

  const hoistRL =
    30.36;

  const roadwayY =
    (
      roadRL -
      regulatorFloorRL
    ) * scale;

  const hoistY =
    (
      hoistRL -
      regulatorFloorRL
    ) * scale;

  const depth = 4.8;

  water(
    group,
    length * 1.30,
    56,
  );

  box(
    group,
    length + 3,
    0.55,
    depth + 2,
    0,
    -0.26,
    0,
    concrete,
    "PRAKASAM_FLOOR",
  );

  gateArray(
    group,
    "PRAKASAM",
    gates,
    length,
    gateWidth,
    gateHeight,
    hoistY,
    depth,
  );

  road(
    group,
    length,
    roadwayY,
    4.1,
    "PRAKASAM",
  );

  box(
    group,
    length,
    0.28,
    3.8,
    0,
    hoistY,
    0,
    darkConcrete,
    "PRAKASAM_HOIST_BRIDGE",
  );

  const scourWidth =
    scourWidthM *
    scale;

  const scourHeight =
    scourHeightM *
    scale;

  /*
   * Counts are real.
   * Exact placement remains approximate.
   */
  gateArray(
    group,
    "PRAKASAM_LEFT_SCOUR",
    leftScour,
    length * 0.13,
    scourWidth,
    scourHeight,
    hoistY * 0.75,
    depth * 0.75,
    -length * 0.40,
    -6,
  );

  gateArray(
    group,
    "PRAKASAM_RIGHT_SCOUR",
    rightScour,
    length * 0.13,
    scourWidth,
    scourHeight,
    hoistY * 0.75,
    depth * 0.75,
    length * 0.40,
    -6,
  );

  group.userData.simrasVerifiedTopology = {
    assetCode:
      asset.asset_code,

    exactGateCount:
      gates,

    exactLeftScouringCount:
      leftScour,

    exactRightScouringCount:
      rightScour,

    sourceLengthM:
      lengthM,

    detailedSurveyGeometry:
      false,
  };
}


/*
 * ==========================================================
 * POLAVARAM
 *
 * Gap I   - left bank
 * Gap II  - main channel
 * Gap III - right bank
 * Spillway - right-bank side
 * Powerhouse - left-flank side
 * ==========================================================
 */
function buildPolavaram(
  group: THREE.Group,
  asset: WaterAsset,
) {
  const totalLengthM =
    req(
      asset,
      "earth_rockfill_total_length_m",
    );

  const heightM =
    req(
      asset,
      "maximum_dam_height_m",
    );

  const spillwayLengthM =
    req(
      asset,
      "spillway_length_m",
    );

  const gates =
    req(
      asset,
      "radial_gate_count",
    );

  const gateWidthM =
    req(
      asset,
      "radial_gate_width_m",
    );

  const gateHeightM =
    req(
      asset,
      "radial_gate_height_m",
    );

  const units =
    req(
      asset,
      "power_unit_count",
    );

  const scale = 0.055;

  const totalLength =
    totalLengthM * scale;

  const height =
    heightM * scale;

  const spillwayLength =
    spillwayLengthM *
    scale;

  const gateWidth =
    gateWidthM *
    scale;

  const gateHeight =
    gateHeightM *
    scale;

  /*
   * Source-backed lengths.
   */
  const gapI =
    564 *
    scale;

  const gapII =
    1750 *
    scale;

  const gapIII =
    140 *
    scale;

  const separation =
    2.2;

  const x1 =
    -totalLength / 2 +
    gapI / 2;

  const x2 =
    x1 +
    gapI / 2 +
    separation +
    gapII / 2;

  const x3 =
    x2 +
    gapII / 2 +
    separation +
    gapIII / 2;

  water(
    group,
    totalLength +
      spillwayLength +
      80,
    100,
  );

  embankment(
    group,
    gapI,
    height * 0.82,
    x1,
    "POLAVARAM_GAP_I",
  );

  embankment(
    group,
    gapII,
    height,
    x2,
    "POLAVARAM_GAP_II",
  );

  embankment(
    group,
    gapIII,
    height * 0.78,
    x3,
    "POLAVARAM_GAP_III",
  );

  /*
   * Right-bank topology verified.
   * Exact surveyed offset still pending.
   */
  const spillwayX =
    x3 +
    gapIII / 2 +
    16 +
    spillwayLength / 2;

  const spillwayZ =
    24;

  box(
    group,
    spillwayLength + 4,
    0.55,
    11,
    spillwayX,
    -0.26,
    spillwayZ,
    concrete,
    "POLAVARAM_SPILLWAY_FLOOR",
  );

  const spillwayPierHeight =
    Math.max(
      gateHeight * 1.65,
      3.6,
    );

  gateArray(
    group,
    "POLAVARAM_SPILLWAY",
    gates,
    spillwayLength,
    gateWidth,
    gateHeight,
    spillwayPierHeight,
    8,
    spillwayX,
    spillwayZ,
  );

  /*
   * Road/deck here remains visual context.
   */
  const roadGroup =
    new THREE.Group();

  road(
    roadGroup,
    spillwayLength,
    spillwayPierHeight +
      0.65,
    7.2,
    "POLAVARAM_SPILLWAY",
  );

  roadGroup.position.x =
    spillwayX;

  roadGroup.position.z =
    spillwayZ;

  group.add(
    roadGroup,
  );

  /*
   * 12 exact power-unit representations.
   * Detailed powerhouse architecture pending.
   */
  const powerhouseX =
    x1 -
    gapI / 2 -
    10;

  for (
    let i = 0;
    i < units;
    i += 1
  ) {
    box(
      group,
      4.2,
      3.5,
      1.25,
      powerhouseX,
      1.75,
      -30 +
        i * 1.7,
      darkConcrete,
      `POLAVARAM_POWER_UNIT_${String(i + 1).padStart(2, "0")}`,
    );
  }

  group.userData.simrasVerifiedTopology = {
    assetCode:
      asset.asset_code,

    exactGateCount:
      gates,

    exactPowerUnitCount:
      units,

    sourceDamLengthM:
      totalLengthM,

    sourceSpillwayLengthM:
      spillwayLengthM,

    spillwayTopology:
      "RIGHT_BANK",

    powerhouseTopology:
      "LEFT_FLANK",

    detailedSurveyGeometry:
      false,
  };
}


/*
 * ==========================================================
 * SRISAILAM
 * 512 m gravity dam
 * 12 gates
 * 2 river sluices
 * ==========================================================
 */
function buildSrisailam(
  group: THREE.Group,
  asset: WaterAsset,
) {
  const lengthM =
    req(
      asset,
      "dam_length_m",
    );

  const heightM =
    req(
      asset,
      "dam_height_m",
    );

  const gates =
    req(
      asset,
      "radial_crest_gate_count",
    );

  const gateWidthM =
    req(
      asset,
      "radial_gate_width_m",
    );

  const gateHeightM =
    req(
      asset,
      "radial_gate_height_m",
    );

  const sluices =
    req(
      asset,
      "river_sluice_count",
    );

  const sluiceWidthM =
    req(
      asset,
      "river_sluice_width_m",
    );

  const sluiceHeightM =
    req(
      asset,
      "river_sluice_height_m",
    );

  const spillwayLengthM =
    266.39;

  const scale =
    0.24;

  const length =
    lengthM *
    scale;

  const height =
    heightM *
    scale;

  const spillwayLength =
    spillwayLengthM *
    scale;

  const gateWidth =
    gateWidthM *
    scale;

  const gateHeight =
    gateHeightM *
    scale;

  water(
    group,
    length * 1.25,
    85,
  );

  /*
   * Gravity profile.
   */
  const shape =
    new THREE.Shape();

  shape.moveTo(-15, 0);
  shape.lineTo(15, 0);
  shape.lineTo(3.5, height);
  shape.lineTo(-3.5, height);
  shape.closePath();

  const geometry =
    new THREE.ExtrudeGeometry(
      shape,
      {
        depth: length,
        bevelEnabled: false,
      },
    );

  geometry.rotateY(
    Math.PI / 2,
  );

  geometry.translate(
    -length / 2,
    0,
    0,
  );

  const mesh =
    new THREE.Mesh(
      geometry,
      concrete,
    );

  mesh.name =
    "SRISAILAM_GRAVITY_DAM";

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);

  gateArray(
    group,
    "SRISAILAM_SPILLWAY",
    gates,
    spillwayLength,
    gateWidth,
    gateHeight,
    Math.max(
      gateHeight * 1.50,
      8,
    ),
    8,
    0,
    2,
  );

  const sluiceWidth =
    sluiceWidthM *
    scale;

  const sluiceHeight =
    sluiceHeightM *
    scale;

  for (
    let i = 0;
    i < sluices;
    i += 1
  ) {
    box(
      group,
      sluiceWidth,
      sluiceHeight,
      0.35,
      (
        i === 0
          ? -1
          : 1
      ) *
        sluiceWidth *
        1.4,
      sluiceHeight / 2,
      15.2,
      gateMaterial,
      `SRISAILAM_RIVER_SLUICE_${i + 1}`,
    );
  }

  group.userData.simrasVerifiedTopology = {
    assetCode:
      asset.asset_code,

    exactGateCount:
      gates,

    exactRiverSluiceCount:
      sluices,

    sourceLengthM:
      lengthM,

    sourceHeightM:
      heightM,

    sourceSpillwayLengthM:
      spillwayLengthM,

    detailedSurveyGeometry:
      false,
  };
}


/*
 * ==========================================================
 * SOMASILA
 *
 * Source-backed 760 m x 39 m envelope.
 * No gate geometry because count is not verified.
 * ==========================================================
 */
function buildSomasila(
  group: THREE.Group,
  asset: WaterAsset,
) {
  const lengthM =
    req(
      asset,
      "dam_length_m",
    );

  const heightM =
    req(
      asset,
      "dam_height_m",
    );

  const scale =
    0.18;

  const length =
    lengthM *
    scale;

  const height =
    heightM *
    scale;

  water(
    group,
    length * 1.20,
    75,
  );

  const shape =
    new THREE.Shape();

  shape.moveTo(-10, 0);
  shape.lineTo(10, 0);
  shape.lineTo(3, height);
  shape.lineTo(-3, height);
  shape.closePath();

  const geometry =
    new THREE.ExtrudeGeometry(
      shape,
      {
        depth: length,
        bevelEnabled: false,
      },
    );

  geometry.rotateY(
    Math.PI / 2,
  );

  geometry.translate(
    -length / 2,
    0,
    0,
  );

  const mesh =
    new THREE.Mesh(
      geometry,
      concrete,
    );

  mesh.name =
    "SOMASILA_SOURCE_BACKED_BODY";

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  group.add(mesh);

  group.userData.simrasVerifiedTopology = {
    assetCode:
      asset.asset_code,

    sourceLengthM:
      lengthM,

    sourceHeightM:
      heightM,

    gateCount:
      null,

    gateGeometryWithheld:
      true,

    detailedSurveyGeometry:
      false,
  };
}


/*
 * ==========================================================
 * SIR ARTHUR COTTON BARRAGE
 *
 * Four-arm barrage with verified topology:
 * - Dowleswaram: 70 vents, 1437.92 m
 * - Ralli: 43 vents, 884.45 m
 * - Madduru: 23 vents, 469.66 m
 * - Vijjeswaram: 39 vents, 800.64 m
 * Total: 175 vents, 3592.67 m
 * ==========================================================
 */
function buildSirArthurCotton(
  group: THREE.Group,
  asset: WaterAsset,
) {
  const totalLengthM =
    req(
      asset,
      "total_length_m",
    );

  const heightM =
    req(
      asset,
      "height_m",
    );

  const gateCount =
    req(
      asset,
      "gate_count",
    );

  const gateWidthM =
    req(
      asset,
      "gate_width_m",
    );

  const gateHeightM =
    req(
      asset,
      "gate_height_m",
    );

  const pierWidthM =
    req(
      asset,
      "pier_width_m",
    );

  const dowleswaramLengthM =
    req(
      asset,
      "dowleswaram_arm_length_m",
    );

  const dowleswaramVents =
    req(
      asset,
      "dowleswaram_arm_vent_count",
    );

  const ralliLengthM =
    req(
      asset,
      "ralli_arm_length_m",
    );

  const ralliVents =
    req(
      asset,
      "ralli_arm_vent_count",
    );

  const madduruLengthM =
    req(
      asset,
      "madduru_arm_length_m",
    );

  const madduruVents =
    req(
      asset,
      "madduru_arm_vent_count",
    );

  const vijjeswaramLengthM =
    req(
      asset,
      "vijjeswaram_arm_length_m",
    );

  const vijjeswaramVents =
    req(
      asset,
      "vijjeswaram_arm_vent_count",
    );

  const scale = 0.028;

  const totalLength =
    totalLengthM * scale;

  const height =
    heightM * scale;

  const gateWidth =
    gateWidthM * scale;

  const gateHeight =
    gateHeightM * scale;

  const pierWidth =
    pierWidthM * scale;

  /*
   * Four-arm layout with angular separation
   * Visual approximation of actual river branching
   */
  const armAngle = Math.PI / 6; // 30 degrees between arms

  water(
    group,
    totalLength * 1.40,
    95,
  );

  /*
   * Dowleswaram arm (main arm) - centered
   */
  const dowleswaramLength =
    dowleswaramLengthM * scale;

  const dowleswaramGroup =
    new THREE.Group();

  box(
    dowleswaramGroup,
    dowleswaramLength + 2,
    0.35,
    6,
    0,
    -0.16,
    0,
    concrete,
    "DOWLESWARAM_FLOOR",
  );

  gateArray(
    dowleswaramGroup,
    "DOWLESWARAM",
    dowleswaramVents,
    dowleswaramLength,
    gateWidth,
    gateHeight,
    height + 2.5,
    6,
  );

  road(
    dowleswaramGroup,
    dowleswaramLength,
    height + 3.2,
    4.5,
    "DOWLESWARAM",
  );

  dowleswaramGroup.rotation.y = 0;
  group.add(dowleswaramGroup);

  /*
   * Ralli arm (left branch)
   */
  const ralliLength =
    ralliLengthM * scale;

  const ralliGroup =
    new THREE.Group();

  box(
    ralliGroup,
    ralliLength + 2,
    0.35,
    5,
    0,
    -0.16,
    0,
    concrete,
    "RALLI_FLOOR",
  );

  gateArray(
    ralliGroup,
    "RALLI",
    ralliVents,
    ralliLength,
    gateWidth,
    gateHeight,
    height + 2.5,
    5,
  );

  road(
    ralliGroup,
    ralliLength,
    height + 3.2,
    4.0,
    "RALLI",
  );

  ralliGroup.rotation.y = armAngle;
  ralliGroup.position.x = -8;
  ralliGroup.position.z = -12;
  group.add(ralliGroup);

  /*
   * Madduru arm (right branch)
   */
  const madduruLength =
    madduruLengthM * scale;

  const madduruGroup =
    new THREE.Group();

  box(
    madduruGroup,
    madduruLength + 2,
    0.35,
    4,
    0,
    -0.16,
    0,
    concrete,
    "MADDURU_FLOOR",
  );

  gateArray(
    madduruGroup,
    "MADDURU",
    madduruVents,
    madduruLength,
    gateWidth,
    gateHeight,
    height + 2.5,
    4,
  );

  road(
    madduruGroup,
    madduruLength,
    height + 3.2,
    3.5,
    "MADDURU",
  );

  madduruGroup.rotation.y = -armAngle;
  madduruGroup.position.x = 8;
  madduruGroup.position.z = -10;
  group.add(madduruGroup);

  /*
   * Vijjeswaram arm (continuation)
   */
  const vijjeswaramLength =
    vijjeswaramLengthM * scale;

  const vijjeswaramGroup =
    new THREE.Group();

  box(
    vijjeswaramGroup,
    vijjeswaramLength + 2,
    0.35,
    5.5,
    0,
    -0.16,
    0,
    concrete,
    "VIJJESWARAM_FLOOR",
  );

  gateArray(
    vijjeswaramGroup,
    "VIJJESWARAM",
    vijjeswaramVents,
    vijjeswaramLength,
    gateWidth,
    gateHeight,
    height + 2.5,
    5.5,
  );

  road(
    vijjeswaramGroup,
    vijjeswaramLength,
    height + 3.2,
    4.2,
    "VIJJESWARAM",
  );

  vijjeswaramGroup.rotation.y = 0;
  vijjeswaramGroup.position.x = 0;
  vijjeswaramGroup.position.z = 18;
  group.add(vijjeswaramGroup);

  /*
   * Central junction structure
   */
  box(
    group,
    12,
    height + 1.5,
    12,
    0,
    (height + 1.5) / 2 - 0.16,
    0,
    darkConcrete,
    "COTTON_JUNCTION",
  );

  group.userData.simrasVerifiedTopology = {
    assetCode:
      asset.asset_code,

    exactTotalGateCount:
      gateCount,

    exactDowleswaramVents:
      dowleswaramVents,

    exactRalliVents:
      ralliVents,

    exactMadduruVents:
      madduruVents,

    exactVijjeswaramVents:
      vijjeswaramVents,

    sourceTotalLengthM:
      totalLengthM,

    fourArmTopology:
      "VERIFIED",

    detailedSurveyGeometry:
      false,
  };
}


export function isVerifiedWaterTopologyAsset(
  assetCode:
    | string
    | null
    | undefined,
) {
  return (
    !!assetCode &&
    BY_CODE.has(assetCode)
  );
}


export function getVerifiedWaterEngineeringValues(
  assetCode:
    | string
    | null
    | undefined,
): VerifiedWaterMetric[] {
  if (!assetCode) {
    return [];
  }

  const asset =
    BY_CODE.get(assetCode);

  if (!asset) {
    return [];
  }

  const values:
    VerifiedWaterMetric[] =
    [];

  const push = (
    key: string,
    label: string,
    sourceKey: string,
    suffix: string,
    category:
      VerifiedWaterMetric["category"],
  ) => {
    const value =
      n(
        asset,
        sourceKey,
      );

    if (value === null) {
      return;
    }

    values.push({
      key,
      label,
      value:
        `${value}${suffix}`,
      category,
    });
  };

  switch (assetCode) {
    case "AP_DAM_00001":
      push(
        "total_length_m",
        "Length",
        "main_length_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_count",
        "No. of gates",
        "regulator_count",
        "",
        "Structure",
      );

      push(
        "gate_width_m",
        "Gate width",
        "regulator_width_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_height_m",
        "Gate height",
        "regulator_height_m",
        " m",
        "Dimensions",
      );
      break;

    case "AP_DAM_00002":
      push(
        "total_length_m",
        "Dam length",
        "earth_rockfill_total_length_m",
        " m",
        "Dimensions",
      );

      push(
        "height_m",
        "Height",
        "maximum_dam_height_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_count",
        "No. of gates",
        "radial_gate_count",
        "",
        "Structure",
      );

      push(
        "gate_width_m",
        "Gate width",
        "radial_gate_width_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_height_m",
        "Gate height",
        "radial_gate_height_m",
        " m",
        "Dimensions",
      );

      push(
        "power_unit_count",
        "Power units",
        "power_unit_count",
        "",
        "Structure",
      );
      break;

    case "AP_DAM_NWDP_AP01VH0059":
      push(
        "total_length_m",
        "Length",
        "dam_length_m",
        " m",
        "Dimensions",
      );

      push(
        "height_m",
        "Height",
        "dam_height_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_count",
        "No. of gates",
        "radial_crest_gate_count",
        "",
        "Structure",
      );

      push(
        "gate_width_m",
        "Gate width",
        "radial_gate_width_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_height_m",
        "Gate height",
        "radial_gate_height_m",
        " m",
        "Dimensions",
      );
      break;

    case "AP_DAM_WRIS_AP01HH0062":
      push(
        "total_length_m",
        "Length",
        "dam_length_m",
        " m",
        "Dimensions",
      );

      push(
        "height_m",
        "Height",
        "dam_height_m",
        " m",
        "Dimensions",
      );
      break;

    case "AP_BAR_WRIS_B00131":
      push(
        "total_length_m",
        "Total length",
        "total_length_m",
        " m",
        "Dimensions",
      );

      push(
        "height_m",
        "Height",
        "height_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_count",
        "Total vents",
        "gate_count",
        "",
        "Structure",
      );

      push(
        "gate_width_m",
        "Vent width",
        "gate_width_m",
        " m",
        "Dimensions",
      );

      push(
        "gate_height_m",
        "Vent height",
        "gate_height_m",
        " m",
        "Dimensions",
      );

      push(
        "dowleswaram_arm_vent_count",
        "Dowleswaram vents",
        "dowleswaram_arm_vent_count",
        "",
        "Structure",
      );

      push(
        "ralli_arm_vent_count",
        "Ralli vents",
        "ralli_arm_vent_count",
        "",
        "Structure",
      );

      push(
        "madduru_arm_vent_count",
        "Madduru vents",
        "madduru_arm_vent_count",
        "",
        "Structure",
      );

      push(
        "vijjeswaram_arm_vent_count",
        "Vijjeswaram vents",
        "vijjeswaram_arm_vent_count",
        "",
        "Structure",
      );
      break;
  }

  return values;
}


export function buildVerifiedWaterTopologyTwin(
  group: THREE.Group,
  assetCode: string,
): VerifiedWaterTwinSpec | null {
  const asset =
    BY_CODE.get(assetCode);

  if (!asset) {
    return null;
  }

  switch (assetCode) {
    case "AP_DAM_00001":
      buildPrakasam(
        group,
        asset,
      );
      break;

    case "AP_DAM_00002":
      buildPolavaram(
        group,
        asset,
      );
      break;

    case "AP_DAM_NWDP_AP01VH0059":
      buildSrisailam(
        group,
        asset,
      );
      break;

    case "AP_DAM_WRIS_AP01HH0062":
      buildSomasila(
        group,
        asset,
      );
      break;

    case "AP_BAR_WRIS_B00131":
      buildSirArthurCotton(
        group,
        asset,
      );
      break;

    default:
      return null;
  }

  return {
    title:
      "Source-backed verified topology twin",

    fidelity:
      "L1 SOURCE-BACKED VERIFIED TOPOLOGY",

    evidence:
      "Known component counts and engineering dimensions are source-backed. Detailed component positioning and unsourced geometry remain approximate until drawings, CAD/BIM, survey or photogrammetry are verified.",

    dimensions: [
      asset.topology_status,
      asset.dimension_status,
    ],
  };
}
