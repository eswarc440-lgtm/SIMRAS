Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$utf8 = [System.Text.UTF8Encoding]::new($false)

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force $parent | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

function Replace-Once {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New
    )

    $content = [System.IO.File]::ReadAllText($Path)
    if ($content.Contains($New)) {
        return
    }
    if (-not $content.Contains($Old)) {
        throw "Expected text was not found in $Path"
    }
    Write-Utf8File -Path $Path -Content $content.Replace($Old, $New)
}

$requiredFiles = @(
    "backend\app\services\risk_engine.py",
    "backend\app\schemas\twin.py",
    "frontend\src\types\twin.ts",
    "frontend\src\features\digital-twin\AssetSpecificModels.tsx",
    "frontend\src\features\digital-twin\TwinViewer3D.tsx",
    "frontend\src\features\digital-twin\TwinPanels.tsx",
    "frontend\src\styles.css"
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $root $relativePath
    if (-not (Test-Path $fullPath)) {
        throw "Required project file not found: $fullPath"
    }
}

$riskEnginePath = Join-Path $root "backend\app\services\risk_engine.py"
$riskEngine = @'
from dataclasses import asdict, dataclass
from datetime import date


@dataclass(slots=True)
class RiskInput:
    built_year: int | None = None
    design_life_years: int | None = None
    condition: str | None = None
    inspection_score: float | None = None
    days_since_inspection: int | None = None
    days_since_maintenance: int | None = None
    rainfall_mm_24h: float | None = None
    rainfall_mm_7d: float | None = None
    water_level_anomaly_m: float | None = None
    flood_exposure: float | None = None
    traffic_load_ratio: float | None = None
    source_confidence: float | None = None


@dataclass(slots=True)
class RiskResult:
    health_score: float | None
    risk_score: float | None
    risk_level: str | None
    hazard_score: float | None
    hazard_level: str | None
    confidence: float | None
    remaining_life_years: None
    model_version: str
    feature_version: str
    status: str
    prediction_method: str
    model_validated: bool
    factors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def score_risk(data: RiskInput, *, current_year: int | None = None) -> RiskResult:
    """Return a transparent engineering decision-support baseline.

    This function is intentionally not described as trained ML. It keeps the
    application operational while labelled inspection history is collected.
    Structural health and risk remain unavailable without structural evidence.
    Environmental hazard is reported separately and never presented as health.
    """

    year = current_year or date.today().year
    penalty = 0.0
    structural_hazard = 0.0
    environmental_hazard = 0.0
    hazard_inputs = 0
    factors: list[str] = []
    known = 0
    expected = 10

    if data.built_year and data.design_life_years and data.design_life_years > 0:
        known += 1
        age = max(0, year - data.built_year)
        ratio = age / data.design_life_years
        penalty += clamp(ratio * 24, 0, 30)
        if ratio >= 0.75:
            factors.append(f"Age is {ratio:.0%} of stated design life")

    condition_penalty = {
        "GOOD": 3,
        "FAIR": 13,
        "POOR": 28,
        "CRITICAL": 45,
    }
    if data.condition:
        known += 1
        normalized = data.condition.upper()
        penalty += condition_penalty.get(normalized, 12)
        if normalized in {"POOR", "CRITICAL"}:
            factors.append(f"Recorded condition is {normalized.lower()}")

    if data.inspection_score is not None:
        known += 1
        score = clamp(data.inspection_score)
        penalty += (100 - score) * 0.25
        if score < 60:
            factors.append("Latest inspection score is below 60")

    if data.days_since_inspection is not None:
        known += 1
        if data.days_since_inspection > 365:
            penalty += min(15, (data.days_since_inspection - 365) / 90 * 2)
            factors.append("Inspection is more than one year old")

    if data.days_since_maintenance is not None:
        known += 1
        if data.days_since_maintenance > 730:
            penalty += min(10, (data.days_since_maintenance - 730) / 365 * 2)
            factors.append("No recorded maintenance within two years")

    if data.rainfall_mm_24h is not None:
        known += 1
        hazard_inputs += 1
        rain = max(0.0, data.rainfall_mm_24h)
        structural_hazard += clamp((rain - 50) / 8, 0, 12)
        environmental_hazard += clamp(rain / 150 * 30, 0, 30)
        if rain >= 100:
            factors.append("Very heavy 24-hour rainfall exposure")

    if data.rainfall_mm_7d is not None:
        known += 1
        hazard_inputs += 1
        rain = max(0.0, data.rainfall_mm_7d)
        structural_hazard += clamp((rain - 150) / 25, 0, 8)
        environmental_hazard += clamp(rain / 400 * 20, 0, 20)
        if rain >= 250:
            factors.append("High cumulative seven-day rainfall")

    if data.water_level_anomaly_m is not None:
        known += 1
        hazard_inputs += 1
        anomaly = max(0.0, data.water_level_anomaly_m)
        structural_hazard += clamp(anomaly * 6, 0, 18)
        environmental_hazard += clamp(anomaly / 3 * 25, 0, 25)
        if anomaly >= 1.5:
            factors.append("Water level is materially above baseline")

    if data.flood_exposure is not None:
        known += 1
        hazard_inputs += 1
        exposure = max(0.0, min(1.0, data.flood_exposure))
        structural_hazard += exposure * 15
        environmental_hazard += exposure * 20
        if exposure >= 0.7:
            factors.append("High mapped flood exposure")

    if data.traffic_load_ratio is not None:
        known += 1
        hazard_inputs += 1
        ratio = max(0.0, data.traffic_load_ratio)
        structural_hazard += clamp((ratio - 0.7) * 20, 0, 10)
        environmental_hazard += clamp((ratio - 0.7) * 10, 0, 5)
        if ratio > 1:
            factors.append("Estimated traffic/load exceeds reference capacity")

    hazard_score = (
        round(clamp(environmental_hazard), 1) if hazard_inputs else None
    )
    if hazard_score is None:
        hazard_level = None
    elif hazard_score >= 70:
        hazard_level = "HIGH"
    elif hazard_score >= 40:
        hazard_level = "MEDIUM"
    else:
        hazard_level = "LOW"

    # Identity, age and location do not establish structural condition.
    has_structural_evidence = bool(data.condition) or data.inspection_score is not None
    if has_structural_evidence:
        health = round(clamp(100 - penalty), 1)
        risk = round(clamp((100 - health) * 0.72 + structural_hazard), 1)
        risk_level = "HIGH" if risk >= 70 else "MEDIUM" if risk >= 40 else "LOW"
    else:
        health = None
        risk = None
        risk_level = None

    completeness = known / expected
    source_confidence = 0.5 if data.source_confidence is None else data.source_confidence
    confidence = (
        round(max(0.1, min(1.0, completeness * 0.7 + source_confidence * 0.3)), 2)
        if has_structural_evidence
        else None
    )

    if not has_structural_evidence:
        factors.insert(
            0,
            "Health and structural risk require a condition assessment or inspection",
        )
        factors.append("Environmental hazard does not prove structural condition")
        factors.append("Verified identity and location do not verify structural condition")
    elif not factors:
        factors.append("No major threshold exceedance in available features")
    if hazard_score is not None:
        factors.append(
            f"Available environmental exposure gives a {hazard_level.lower()} hazard index"
        )
    if completeness < 0.6:
        factors.append("Result confidence reduced by missing input data")
    factors.append("RUL disabled until longitudinal deterioration data are validated")

    return RiskResult(
        health_score=health,
        risk_score=risk,
        risk_level=risk_level,
        hazard_score=hazard_score,
        hazard_level=hazard_level,
        confidence=confidence,
        remaining_life_years=None,
        model_version="transparent_rules_v2",
        feature_version="asset_state_v1",
        status="DECISION_SUPPORT" if has_structural_evidence else "INSUFFICIENT_DATA",
        prediction_method="transparent_engineering_rules",
        model_validated=False,
        factors=factors,
    )
'@
Write-Utf8File -Path $riskEnginePath -Content $riskEngine

$schemaPath = Join-Path $root "backend\app\schemas\twin.py"
$schemaOldScores = @'
    risk_level: str | None = None
    remaining_life_years: float | None = None
'@
$schemaNewScores = @'
    risk_level: str | None = None
    hazard_score: float | None = None
    hazard_level: str | None = None
    remaining_life_years: float | None = None
'@
Replace-Once -Path $schemaPath -Old $schemaOldScores -New $schemaNewScores

$schemaOldMethod = @'
    status: str
    factors: list[str] = Field(default_factory=list)
'@
$schemaNewMethod = @'
    status: str
    prediction_method: str = "unknown"
    model_validated: bool = False
    factors: list[str] = Field(default_factory=list)
'@
Replace-Once -Path $schemaPath -Old $schemaOldMethod -New $schemaNewMethod

$typesPath = Join-Path $root "frontend\src\types\twin.ts"
$types = @'
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface GeometryPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface AssetSummary {
  asset_code: string;
  name: string;
  asset_type: "bridge" | "dam" | "barrage";
  subtype?: string | null;
  district?: string | null;
  identity_status: string;
  condition?: string | null;
  geometry: GeometryPoint;
  risk_score?: number | null;
  risk_level?: RiskLevel | null;
  data_confidence?: number | null;
}

export interface AssetListResponse {
  items: AssetSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceValue {
  value: number | string | null;
  unit?: string | null;
  source: string;
  source_type: string;
  observed_at?: string | null;
  ingested_at?: string | null;
  quality_flag: string;
  confidence?: number | null;
  is_estimated: boolean;
}

export interface TwinResponse {
  asset: AssetSummary;
  static: Record<string, unknown>;
  twin: {
    format: string;
    uri?: string | null;
    version: string;
    fidelity_level: string;
    model_source: string;
    source_url?: string | null;
    dimensions: Record<string, unknown>;
    is_asset_specific: boolean;
    heading_deg?: number | null;
    elevation_m?: number | null;
    horizontal_accuracy_m?: number | null;
  };
  environment: Record<string, SourceValue>;
  inspection: {
    inspection_date?: string | null;
    condition?: string | null;
    score?: number | null;
    quality_flag: string;
    is_synthetic: boolean;
  };
  maintenance: Array<Record<string, unknown>>;
  sensors_status: string;
  ai: {
    health_score?: number | null;
    risk_score?: number | null;
    risk_level?: RiskLevel | null;
    hazard_score?: number | null;
    hazard_level?: RiskLevel | null;
    remaining_life_years?: number | null;
    confidence?: number | null;
    model_version: string;
    feature_version: string;
    prediction_time: string;
    status: string;
    prediction_method?: string;
    model_validated?: boolean;
    factors: string[];
  };
  freshness: Record<string, string>;
  generated_at: string;
}
'@
Write-Utf8File -Path $typesPath -Content $types

$modelsPath = Join-Path $root "frontend\src\features\digital-twin\AssetSpecificModels.tsx"
$assetSpecificModels = @'
import { Html, Line } from "@react-three/drei";
import { useMemo } from "react";
import { CatmullRomCurve3, Vector3 } from "three";
import type { TwinResponse } from "../../types/twin";

interface ModelProps {
  twin: TwinResponse;
  colour: string;
  showDimensions: boolean;
}

interface DimensionLineProps {
  start: [number, number, number];
  end: [number, number, number];
  label: string;
  labelOffset?: [number, number, number];
}

function numericDimension(
  dimensions: Record<string, unknown>,
  key: string,
  fallback: number,
) {
  const value = Number(dimensions[key]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function DimensionLine({
  start,
  end,
  label,
  labelOffset = [0, 0.18, 0],
}: DimensionLineProps) {
  const midpoint: [number, number, number] = [
    (start[0] + end[0]) / 2 + labelOffset[0],
    (start[1] + end[1]) / 2 + labelOffset[1],
    (start[2] + end[2]) / 2 + labelOffset[2],
  ];

  return (
    <group>
      <Line points={[start, end]} color="#67e8f9" lineWidth={1.8} />
      <mesh position={start}>
        <sphereGeometry args={[0.06, 10, 10]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>
      <mesh position={end}>
        <sphereGeometry args={[0.06, 10, 10]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>
      <Html position={midpoint} center distanceFactor={9}>
        <span className="model-dimension-label">{label}</span>
      </Html>
    </group>
  );
}

function PrakasamBarrage({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  const dimensions = twin.twin.dimensions;
  const gateCount = Math.round(numericDimension(dimensions, "gate_count", 70));
  const lengthM = numericDimension(dimensions, "length_m", 1232.92);
  const gateWidthM = numericDimension(dimensions, "gate_width_m", 12.19);
  const gateHeightM = numericDimension(dimensions, "gate_height_m", 3.66);
  const previewLength = 18;
  const bayWidth = previewLength / gateCount;

  return (
    <group rotation={[0, -0.18, 0]}>
      <mesh position={[0, 1.55, 0]} castShadow receiveShadow>
        <boxGeometry args={[previewLength + 0.3, 0.3, 1.35]} />
        <meshStandardMaterial color="#d9e2e8" roughness={0.72} />
      </mesh>

      {Array.from({ length: gateCount + 1 }, (_, index) => {
        const x = -previewLength / 2 + index * bayWidth;
        return (
          <mesh key={`pier-${index}`} position={[x, 0.1, 0]} castShadow>
            <boxGeometry args={[0.055, 2.65, 1.15]} />
            <meshStandardMaterial color="#c7d2d9" roughness={0.8} />
          </mesh>
        );
      })}

      {Array.from({ length: gateCount }, (_, index) => {
        const x = -previewLength / 2 + (index + 0.5) * bayWidth;
        return (
          <mesh key={`gate-${index}`} position={[x, 0.05, 0.04]}>
            <boxGeometry args={[bayWidth * 0.82, 2.2, 0.09]} />
            <meshStandardMaterial
              color={colour}
              metalness={0.62}
              roughness={0.38}
            />
          </mesh>
        );
      })}

      <mesh position={[0, -1.4, 2.25]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[22, 6]} />
        <meshStandardMaterial color="#167da8" transparent opacity={0.72} />
      </mesh>

      {showDimensions && (
        <group>
          <DimensionLine
            start={[-previewLength / 2, 2.35, -0.75]}
            end={[previewLength / 2, 2.35, -0.75]}
            label={`Total length ${lengthM.toFixed(2)} m`}
          />
          <DimensionLine
            start={[-previewLength / 2, -1.25, -0.8]}
            end={[-previewLength / 2 + bayWidth, -1.25, -0.8]}
            label={`Gate width ${gateWidthM.toFixed(2)} m`}
            labelOffset={[0.55, -0.28, 0]}
          />
          <DimensionLine
            start={[previewLength / 2 + 0.65, -1.2, -0.7]}
            end={[previewLength / 2 + 0.65, 1.45, -0.7]}
            label={`Gate height ${gateHeightM.toFixed(2)} m`}
            labelOffset={[0.85, 0, 0]}
          />
          <Html position={[0, -0.9, -0.85]} center distanceFactor={9}>
            <span className="model-dimension-label">{gateCount} gates</span>
          </Html>
        </group>
      )}
    </group>
  );
}

function GodavariArchBridge({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  const dimensions = twin.twin.dimensions;
  const spanCount = Math.round(numericDimension(dimensions, "span_count", 28));
  const lengthM = numericDimension(dimensions, "length_m", 2745);
  const mainSpanM = numericDimension(dimensions, "main_span_m", 97.55);
  const previewLength = 20;
  const spanWidth = previewLength / spanCount;

  const arches = useMemo(
    () =>
      Array.from({ length: spanCount }, (_, spanIndex) => {
        const start = -previewLength / 2 + spanIndex * spanWidth;
        const points = Array.from({ length: 9 }, (_, pointIndex) => {
          const t = pointIndex / 8;
          return {
            x: start + t * spanWidth,
            y: 0.35 + Math.sin(Math.PI * t) * 0.72,
          };
        });
        return [-0.42, 0.42].map(
          (z) =>
            new CatmullRomCurve3(
              points.map((point) => new Vector3(point.x, point.y, z)),
            ),
        );
      }),
    [spanCount, spanWidth],
  );

  return (
    <group rotation={[0, -0.12, 0]}>
      <mesh position={[0, 0.08, 0]} castShadow receiveShadow>
        <boxGeometry args={[previewLength, 0.18, 1.05]} />
        <meshStandardMaterial color="#aeb9c3" roughness={0.62} />
      </mesh>

      {arches.flatMap((spanArches, spanIndex) =>
        spanArches.map((curve, archIndex) => (
          <mesh key={`arch-${spanIndex}-${archIndex}`} castShadow>
            <tubeGeometry args={[curve, 20, 0.038, 7, false]} />
            <meshStandardMaterial color={colour} roughness={0.48} />
          </mesh>
        )),
      )}

      {Array.from({ length: spanCount + 1 }, (_, index) => {
        const x = -previewLength / 2 + index * spanWidth;
        return (
          <mesh key={`pier-${index}`} position={[x, -0.9, 0]} castShadow>
            <boxGeometry args={[0.12, 1.9, 0.74]} />
            <meshStandardMaterial color="#8c99a5" roughness={0.8} />
          </mesh>
        );
      })}

      {Array.from({ length: spanCount }, (_, spanIndex) =>
        [0.22, 0.4, 0.6, 0.78].flatMap((t) => {
          const x =
            -previewLength / 2 + spanIndex * spanWidth + t * spanWidth;
          const height = Math.sin(Math.PI * t) * 0.72;
          return [-0.42, 0.42].map((z) => (
            <mesh
              key={`hanger-${spanIndex}-${t}-${z}`}
              position={[x, 0.34 + height / 2, z]}
            >
              <cylinderGeometry args={[0.009, 0.009, height, 5]} />
              <meshStandardMaterial color="#dce6ec" metalness={0.55} />
            </mesh>
          ));
        }),
      )}

      <mesh position={[0, -1.55, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[23, 7]} />
        <meshStandardMaterial color="#176f9d" transparent opacity={0.68} />
      </mesh>

      {showDimensions && (
        <group>
          <DimensionLine
            start={[-previewLength / 2, 2, -0.8]}
            end={[previewLength / 2, 2, -0.8]}
            label={`Total length ${lengthM.toFixed(0)} m`}
          />
          <DimensionLine
            start={[-previewLength / 2, -1.32, -0.8]}
            end={[-previewLength / 2 + spanWidth, -1.32, -0.8]}
            label={`Main span ${mainSpanM.toFixed(2)} m`}
            labelOffset={[0.62, -0.27, 0]}
          />
          <Html position={[0, -0.85, -0.9]} center distanceFactor={9}>
            <span className="model-dimension-label">{spanCount} spans</span>
          </Html>
        </group>
      )}
    </group>
  );
}

function MissingAssetModel({ twin }: { twin: TwinResponse }) {
  return (
    <Html center distanceFactor={12}>
      <div className="twin-model-empty">
        <strong>Asset-specific 3D not available</strong>
        <span>{twin.asset.name}</span>
        <small>Use the real-world map while measured geometry is acquired.</small>
      </div>
    </Html>
  );
}

export function AssetSpecificModel({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  if (twin.asset.asset_code === "AP_DAM_00001") {
    return (
      <PrakasamBarrage
        twin={twin}
        colour={colour}
        showDimensions={showDimensions}
      />
    );
  }

  if (twin.asset.asset_code === "AP_BR_00001") {
    return (
      <GodavariArchBridge
        twin={twin}
        colour={colour}
        showDimensions={showDimensions}
      />
    );
  }

  return <MissingAssetModel twin={twin} />;
}
'@
Write-Utf8File -Path $modelsPath -Content $assetSpecificModels

$viewerPath = Join-Path $root "frontend\src\features\digital-twin\TwinViewer3D.tsx"
$viewer = @'
import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useMemo, useState } from "react";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";
import { AssetSpecificModel } from "./AssetSpecificModels";

function GlbModel({ uri }: { uri: string }) {
  const { scene } = useGLTF(uri);
  const instance = useMemo(() => scene.clone(true), [scene]);
  return <primitive object={instance} scale={1} />;
}

export function TwinViewer3D({ twin }: { twin: TwinResponse }) {
  const [showDimensions, setShowDimensions] = useState(true);
  const colour = riskColor(twin.ai.risk_level);
  const hasAssetSpecificModel =
    Boolean(twin.twin.uri) || twin.twin.is_asset_specific;
  const hasDimensions = Object.keys(twin.twin.dimensions).length > 0;

  return (
    <div className="twin-canvas">
      <Canvas camera={{ position: [12, 7, 15], fov: 42 }} shadows>
        <color attach="background" args={["#07111c"]} />
        <ambientLight intensity={0.78} />
        <directionalLight
          position={[8, 12, 7]}
          intensity={2.4}
          castShadow
        />
        <gridHelper
          args={[30, 30, "#1c516b", "#122a3a"]}
          position={[0, -1.58, 0]}
        />
        <Suspense fallback={null}>
          {twin.twin.uri ? (
            <GlbModel uri={twin.twin.uri} />
          ) : (
            <AssetSpecificModel
              twin={twin}
              colour={colour}
              showDimensions={showDimensions}
            />
          )}
        </Suspense>
        <OrbitControls makeDefault minDistance={4} maxDistance={42} />
      </Canvas>

      <div className="viewer-label">
        <strong>{twin.twin.fidelity_level}</strong>
        <span>
          {hasAssetSpecificModel
            ? "Asset-specific, dimension-derived model"
            : "No asset-specific model - location view only"}
        </span>
      </div>

      {hasDimensions && !twin.twin.uri && (
        <button
          className="dimension-toggle"
          type="button"
          aria-pressed={showDimensions}
          onClick={() => setShowDimensions((current) => !current)}
        >
          {showDimensions ? "Hide dimensions" : "Show dimensions"}
        </button>
      )}
    </div>
  );
}
'@
Write-Utf8File -Path $viewerPath -Content $viewer

$panelsPath = Join-Path $root "frontend\src\features\digital-twin\TwinPanels.tsx"
$panels = @'
import { StatusPill } from "../../components/StatusPill";
import type { TwinResponse } from "../../types/twin";
import { formatValue, riskColor } from "../../utils";

const unavailable = "\u2014";

function dimensionLabel(key: string) {
  return key.replace(/_m$/, " (m)").replaceAll("_", " ");
}

function dimensionValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2);
  }
  return String(value).replaceAll("_", " ");
}

function scoreValue(value?: number | null) {
  return value != null ? (
    <>
      {value.toFixed(0)}
      <small>/100</small>
    </>
  ) : (
    unavailable
  );
}

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  const dimensions = Object.entries(twin.twin.dimensions).filter(
    ([key]) => key !== "representation",
  );
  const methodLabel = twin.ai.model_validated
    ? "Validated ML model"
    : twin.ai.status === "DECISION_SUPPORT"
      ? "Engineering estimate - ML validation pending"
      : "ML prediction unavailable";

  return (
    <div className="twin-panels">
      <section className="panel score-panel score-panel-four">
        <div>
          <span>Health</span>
          <strong>{scoreValue(twin.ai.health_score)}</strong>
        </div>
        <div>
          <span>Structural risk</span>
          <strong style={{ color: riskColor(twin.ai.risk_level) }}>
            {scoreValue(twin.ai.risk_score)}
          </strong>
        </div>
        <div>
          <span>Environment hazard</span>
          <strong style={{ color: riskColor(twin.ai.hazard_level) }}>
            {scoreValue(twin.ai.hazard_score)}
          </strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>
            {twin.ai.confidence != null
              ? `${Math.round(twin.ai.confidence * 100)}%`
              : unavailable}
          </strong>
        </div>
      </section>

      <section className="panel prediction-disclosure">
        <div>
          <span>Prediction method</span>
          <strong>{methodLabel}</strong>
        </div>
        <div>
          <span>Engine</span>
          <strong>{twin.ai.prediction_method ?? "Not available"}</strong>
        </div>
        <div>
          <span>Version</span>
          <strong>{twin.ai.model_version}</strong>
        </div>
        <StatusPill
          label={twin.ai.model_validated ? "VALIDATED" : twin.ai.status}
          tone={twin.ai.model_validated ? "good" : "warn"}
        />
      </section>

      <section className="panel">
        <header>
          <h3>Current environment</h3>
          <StatusPill label={twin.freshness.environment} />
        </header>
        <div className="metric-grid">
          {Object.entries(twin.environment).map(([key, item]) => (
            <article key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{formatValue(item.value, item.unit)}</strong>
              <small>
                {item.source_type.replaceAll("_", " ")}
                {" \u00b7 "}
                {item.source}
              </small>
            </article>
          ))}
          {Object.keys(twin.environment).length === 0 && (
            <p>No environmental feed is matched.</p>
          )}
        </div>
      </section>

      <section className="panel">
        <header>
          <h3>Decision-support factors</h3>
          <StatusPill label={twin.ai.status} tone="warn" />
        </header>
        <ul className="factor-list">
          {twin.ai.factors.map((factor) => (
            <li key={factor}>{factor}</li>
          ))}
        </ul>
      </section>

      <section className="panel provenance-panel">
        <header>
          <h3>Reality & provenance</h3>
          <StatusPill
            label={twin.asset.identity_status}
            tone={twin.asset.identity_status === "VERIFIED" ? "good" : "warn"}
          />
        </header>
        <dl>
          <div>
            <dt>3D fidelity</dt>
            <dd>
              {twin.twin.fidelity_level}
              {" \u00b7 "}
              {twin.twin.model_source}
            </dd>
          </div>
          <div>
            <dt>Model source</dt>
            <dd>
              {twin.twin.source_url ? (
                <a
                  className="model-source-link"
                  href={twin.twin.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Published engineering source {"\u2197"}
                </a>
              ) : (
                "Not available"
              )}
            </dd>
          </div>
          <div>
            <dt>Structural sensors</dt>
            <dd>{twin.sensors_status.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>Inspection</dt>
            <dd>{twin.inspection.quality_flag.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>RUL</dt>
            <dd>
              {twin.ai.remaining_life_years ??
                "Disabled until longitudinal validation"}
            </dd>
          </div>
        </dl>

        {dimensions.length > 0 && (
          <div className="dimension-list">
            <h4>Published model dimensions</h4>
            <dl>
              {dimensions.map(([key, value]) => (
                <div key={key}>
                  <dt>{dimensionLabel(key)}</dt>
                  <dd>{dimensionValue(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>
    </div>
  );
}
'@
Write-Utf8File -Path $panelsPath -Content $panels

$testPath = Join-Path $root "backend\tests\test_prediction_readiness.py"
$tests = @'
from app.services.risk_engine import RiskInput, score_risk


def test_environmental_hazard_is_separate_from_structural_health():
    result = score_risk(
        RiskInput(
            rainfall_mm_24h=120,
            rainfall_mm_7d=280,
            source_confidence=1,
        ),
        current_year=2026,
    )

    assert result.health_score is None
    assert result.risk_score is None
    assert result.hazard_score is not None
    assert result.hazard_score > 0
    assert result.hazard_level in {"LOW", "MEDIUM", "HIGH"}
    assert result.status == "INSUFFICIENT_DATA"
    assert result.model_validated is False


def test_inspection_enables_engineering_decision_support():
    result = score_risk(
        RiskInput(
            built_year=1997,
            design_life_years=100,
            condition="GOOD",
            inspection_score=82,
            rainfall_mm_24h=28.3,
            source_confidence=0.9,
        ),
        current_year=2026,
    )

    assert result.health_score is not None
    assert result.risk_score is not None
    assert result.status == "DECISION_SUPPORT"
    assert result.prediction_method == "transparent_engineering_rules"
    assert result.model_validated is False
'@
Write-Utf8File -Path $testPath -Content $tests

$stylesPath = Join-Path $root "frontend\src\styles.css"
$styles = [System.IO.File]::ReadAllText($stylesPath)
if (-not $styles.Contains(".model-dimension-label")) {
    $styles += @'


.model-dimension-label {
  display: inline-block;
  white-space: nowrap;
  padding: 5px 8px;
  border: 1px solid rgba(103, 232, 249, 0.7);
  border-radius: 6px;
  background: rgba(3, 14, 25, 0.92);
  color: #cffafe;
  font: 600 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  box-shadow: 0 6px 20px rgba(2, 8, 23, 0.45);
  pointer-events: none;
}

.dimension-toggle {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 12;
  padding: 8px 12px;
  border: 1px solid rgba(103, 232, 249, 0.55);
  border-radius: 8px;
  background: rgba(7, 20, 38, 0.9);
  color: #cffafe;
  cursor: pointer;
}

.dimension-toggle:hover {
  border-color: #67e8f9;
  background: rgba(14, 116, 144, 0.3);
}

.score-panel-four {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.prediction-disclosure {
  display: grid;
  grid-template-columns: 2fr 1.4fr 1fr auto;
  align-items: center;
  gap: 18px;
}

.prediction-disclosure > div {
  display: grid;
  gap: 5px;
}

.prediction-disclosure span {
  color: #7dd3fc;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.prediction-disclosure strong {
  color: #e2e8f0;
  font-size: 0.9rem;
}

@media (max-width: 900px) {
  .score-panel-four,
  .prediction-disclosure {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'@
    Write-Utf8File -Path $stylesPath -Content $styles
}

# Repair common UTF-8 text that was previously decoded as Windows-1252.
$badSequences = @{
    (-join @([char]0x00e2, [char]0x20ac, [char]0x201d)) = [char]0x2014
    (-join @([char]0x00c2, [char]0x00b7)) = [char]0x00b7
    (-join @([char]0x00e2, [char]0x2020, [char]0x2019)) = [char]0x2192
    (-join @([char]0x00e2, [char]0x2020, [char]0x2014)) = [char]0x2197
    (-join @([char]0x00e2, [char]0x20ac, [char]0x00a6)) = [char]0x2026
    (-join @([char]0x00c2, [char]0x00b0)) = [char]0x00b0
    (-join @([char]0x00c2, [char]0x00a0)) = " "
}

$sourceFiles = Get-ChildItem (Join-Path $root "frontend\src") -Recurse -File |
    Where-Object { $_.Extension -in ".ts", ".tsx", ".css", ".html" }

foreach ($file in $sourceFiles) {
    $content = [System.IO.File]::ReadAllText($file.FullName)
    $repaired = $content
    foreach ($entry in $badSequences.GetEnumerator()) {
        $repaired = $repaired.Replace([string]$entry.Key, [string]$entry.Value)
    }
    if ($repaired -ne $content) {
        Write-Utf8File -Path $file.FullName -Content $repaired
    }
}

Set-Location $root
Write-Host "Stage 4B files prepared. Review with: git status --short"
