import { Html } from "@react-three/drei";
import type { ReactNode } from "react";
import type { TwinResponse } from "../../types/twin";

type Props = {
  twin: TwinResponse;
  visible: boolean;
};

type Dims = Record<string, unknown>;

function numberValue(d: Dims, keys: string[]): number | null {
  for (const key of keys) {
    const value = Number(d[key]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return null;
}

function sourceBacked(twin: TwinResponse): boolean {
  const representation = String(
    twin.twin.dimensions?.["representation"] ?? "",
  ).toLowerCase();

  return (
    twin.twin.fidelity_level !== "L0" &&
    twin.twin.is_asset_specific &&
    (
      Boolean(twin.twin.source_url) ||
      representation.includes("source_backed") ||
      representation.includes("source_extracted")
    )
  );
}

function fmt(value: number, unit = "m", digits = 2) {
  return `${value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  })}${unit ? ` ${unit}` : ""}`;
}

function Badge({
  position,
  children,
}: {
  position: [number, number, number];
  children: ReactNode;
}) {
  return (
    <Html center position={position} distanceFactor={9}>
      <div
        style={{
          padding: "5px 9px",
          borderRadius: 6,
          border: "1px solid rgba(88,211,235,.78)",
          background: "rgba(2,18,29,.95)",
          color: "#e8fbff",
          fontSize: 11,
          fontWeight: 700,
          lineHeight: 1.25,
          whiteSpace: "nowrap",
          pointerEvents: "none",
          boxShadow: "0 5px 18px rgba(0,0,0,.35)",
          letterSpacing: ".01em",
        }}
      >
        {children}
      </div>
    </Html>
  );
}

function Dot({ position }: { position: [number, number, number] }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.075, 12, 12]} />
      <meshBasicMaterial color="#a9eef6" />
    </mesh>
  );
}

function HorizontalMeasure({
  y,
  z,
  sceneLength = 22,
}: {
  y: number;
  z: number;
  sceneLength?: number;
}) {
  return (
    <group>
      <mesh position={[0, y, z]}>
        <boxGeometry args={[sceneLength, 0.022, 0.022]} />
        <meshBasicMaterial color="#a9eef6" />
      </mesh>
      <Dot position={[-sceneLength / 2, y, z]} />
      <Dot position={[sceneLength / 2, y, z]} />
    </group>
  );
}

function VerticalMeasure({
  x,
  z,
  from,
  to,
}: {
  x: number;
  z: number;
  from: number;
  to: number;
}) {
  const height = Math.abs(to - from);
  const y = (from + to) / 2;

  return (
    <group>
      <mesh position={[x, y, z]}>
        <boxGeometry args={[0.022, height, 0.022]} />
        <meshBasicMaterial color="#a9eef6" />
      </mesh>
      <Dot position={[x, from, z]} />
      <Dot position={[x, to, z]} />
    </group>
  );
}

export function DimensionAnnotations({ twin, visible }: Props) {
  if (!visible || !sourceBacked(twin)) return null;

  const d = twin.twin.dimensions as Dims;
  const type = String(twin.asset.asset_type ?? "").toLowerCase();

  const length = numberValue(d, [
    "total_length_m",
    "length_m",
    "crest_length_m",
    "structure_length_m",
    "project_corridor_length_m",
    "runway_length_m",
  ]);

  const width = numberValue(d, [
    "gate_width_m",
    "spillway_gate_width_m",
    "deck_width_m",
    "width_m",
    "runway_width_m",
    "crest_width_m",
  ]);

  const height = numberValue(d, [
    "gate_height_m",
    "spillway_gate_height_m",
    "height_m",
    "dam_height_m",
    "max_height_m",
    "pier_height_m",
    "main_gopuram_height_m",
  ]);

  const count = numberValue(d, [
    "gate_count",
    "spillway_gate_count",
    "gates",
    "span_count",
    "lane_count",
    "runway_count",
    "gopuram_tiers",
  ]);

  if (length == null && width == null && height == null && count == null) {
    return null;
  }

  const isBarrage = type === "barrage";
  const isBridge = type === "bridge";
  const isAirport = type === "airport";
  const isTemple = type === "temple";
  
  const sceneLength = isBarrage
    ? Math.max(16, Math.min(34, 15 + Math.log10(numberValue(d, ["total_length_m", "length_m", "crest_length_m"]) ?? 1000) * 4.2))
    : isBridge
      ? 15.5 + Math.max(2, Math.min(18, Math.round(numberValue(d, ["span_count"]) ?? 5))) * 0.75
      : isAirport
        ? Math.max(12, Math.min(24, (numberValue(d, ["runway_length_m", "length_m"]) ?? 2400) / 150))
        : isTemple
          ? 18
          : 18;
  const sceneHeight = type === "dam"
    ? Math.max(3.4, Math.min(6, ((numberValue(d, ["height_m", "dam_height_m"]) ?? 45) / (numberValue(d, ["length_m", "total_length_m"]) ?? 400)) * 34))
    : isAirport
      ? 1.6
      : isBridge
        ? 3.2
        : isTemple
          ? Math.max(10, Math.min(24, (numberValue(d, ["main_gopuram_height_m", "height_m"]) ?? 25) * 0.85))
          : 3.2;
  
  const countLabel = isBarrage
    ? "gates"
    : isBridge
      ? "spans"
      : isAirport
        ? "runways"
        : isTemple
          ? "tiers"
          : "elements";

  return (
    <group>
      {length != null && (
        <>
          <HorizontalMeasure y={sceneHeight + 0.9} z={0.1} sceneLength={sceneLength} />
          <Badge position={[0, sceneHeight + 1.25, 0.1]}>
            {isAirport ? "Runway length" : isTemple ? "Structure length" : "Total length"} {fmt(length)}
          </Badge>
        </>
      )}

      {width != null && (
        <Badge position={[-sceneLength / 2, 0.55, 2.85]}>
          {isBarrage ? "Gate width" : isBridge ? "Deck width" : isAirport ? "Runway width" : isTemple ? "Width" : "Width"}{" "}
          {fmt(width)}
        </Badge>
      )}

      {count != null && (
        <Badge position={[0, sceneHeight * 0.25, 2.95]}>
          {Math.round(count)} {countLabel}
        </Badge>
      )}

      {height != null && (
        <>
          <VerticalMeasure x={sceneLength / 2 + 0.8} z={0.45} from={-1.35} to={sceneHeight - 0.35} />
          <Badge position={[sceneLength / 2 + 2, sceneHeight * 0.25, 0.45]}>
            {isBarrage ? "Gate height" : isAirport ? "Structure height" : isTemple ? "Gopuram height" : "Height"} {fmt(height)}
          </Badge>
        </>
      )}
    </group>
  );
}
