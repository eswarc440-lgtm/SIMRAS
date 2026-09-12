import { Html } from "@react-three/drei";
import type { ReactNode } from "react";
import type { TwinResponse } from "../../types/twin";

type Props = {
  twin: TwinResponse;
  visible: boolean;
};

type Dims = Record<string, unknown>;

function num(d: Dims, keys: string[]): number | null {
  for (const key of keys) {
    const value = Number(d[key]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return null;
}

function fmt(value: number, unit = "m", digits = 2): string {
  return `${value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  })}${unit ? ` ${unit}` : ""}`;
}

function sourceBacked(twin: TwinResponse): boolean {
  const representation = String(
    twin.twin.dimensions["representation"] ?? "",
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

function Label({
  position,
  children,
}: {
  position: [number, number, number];
  children: ReactNode;
}) {
  return (
    <Html center position={position} distanceFactor={10}>
      <div
        style={{
          padding: "5px 9px",
          borderRadius: 6,
          border: "1px solid rgba(77,208,225,.85)",
          background: "rgba(3,17,27,.95)",
          color: "#e7fbff",
          fontSize: 11,
          fontWeight: 700,
          whiteSpace: "nowrap",
          pointerEvents: "none",
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
      <sphereGeometry args={[0.07, 10, 10]} />
      <meshBasicMaterial color="#a7ecf4" />
    </mesh>
  );
}

function HorizontalMeasure({
  y,
  z,
  length = 22,
}: {
  y: number;
  z: number;
  length?: number;
}) {
  return (
    <group>
      <mesh position={[0, y, z]}>
        <boxGeometry args={[length, 0.018, 0.018]} />
        <meshBasicMaterial color="#a7ecf4" />
      </mesh>
      <Dot position={[-length / 2, y, z]} />
      <Dot position={[length / 2, y, z]} />
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
  const h = Math.abs(to - from);
  const y = (from + to) / 2;

  return (
    <group>
      <mesh position={[x, y, z]}>
        <boxGeometry args={[0.018, h, 0.018]} />
        <meshBasicMaterial color="#a7ecf4" />
      </mesh>
      <Dot position={[x, from, z]} />
      <Dot position={[x, to, z]} />
    </group>
  );
}

function DepthMeasure({
  x,
  y,
  from,
  to,
}: {
  x: number;
  y: number;
  from: number;
  to: number;
}) {
  const depth = Math.abs(to - from);
  const z = (from + to) / 2;

  return (
    <group>
      <mesh position={[x, y, z]}>
        <boxGeometry args={[0.018, 0.018, depth]} />
        <meshBasicMaterial color="#a7ecf4" />
      </mesh>
      <Dot position={[x, y, from]} />
      <Dot position={[x, y, to]} />
    </group>
  );
}

export function DimensionAnnotations({ twin, visible }: Props) {
  if (!visible || !sourceBacked(twin)) return null;

  const d = twin.twin.dimensions;
  const type = twin.asset.asset_type.toLowerCase();
  const subtype = String(twin.asset.subtype ?? "").toLowerCase();

  const length = num(d, [
    "length_m",
    "runway_length_m",
    "berth_length_m",
    "quay_length_m",
  ]);

  const width = num(d, [
    "width_m",
    "deck_width_m",
    "runway_width_m",
    "crest_width_m",
    "berth_width_m",
  ]);

  const height = num(d, [
    "height_m",
    "pier_height_m",
    "gopuram_height_m",
  ]);

  const gates = num(d, ["gate_count"]);
  const gateWidth = num(d, ["gate_width_m"]);
  const gateHeight = num(d, ["gate_height_m"]);
  const lanes = num(d, ["lane_count"]);
  const spans = num(d, ["span_count"]);
  const spanLength = num(d, [
    "typical_span_m",
    "main_span_m",
    "span_m",
  ]);

  const isWater =
    type === "dam" ||
    type === "barrage" ||
    subtype.includes("dam") ||
    subtype.includes("barrage");

  const isBridge =
    type === "bridge" ||
    subtype.includes("flyover") ||
    subtype.includes("viaduct");

  return (
    <group>
      {length != null && (
        <>
          <HorizontalMeasure y={5.0} z={0} />
          <Label position={[0, 5.33, 0]}>
            Total length {fmt(length)}
          </Label>
        </>
      )}

      {height != null && (
        <>
          <VerticalMeasure x={11.4} z={0} from={-1.8} to={4.0} />
          <Label position={[12.35, 1.15, 0]}>
            Height {fmt(height)}
          </Label>
        </>
      )}

      {width != null && (
        <>
          <DepthMeasure x={-10.0} y={-0.6} from={-3.0} to={3.0} />
          <Label position={[-10.0, -0.1, -3.7]}>
            Width {fmt(width)}
          </Label>
        </>
      )}

      {isWater && gateWidth != null && (
        <Label position={[-8.2, -0.1, 2.4]}>
          Gate width {fmt(gateWidth)}
        </Label>
      )}

      {isWater && gateHeight != null && (
        <Label position={[8.2, -0.1, 2.4]}>
          Gate height {fmt(gateHeight)}
        </Label>
      )}

      {isWater && gates != null && (
        <Label position={[0, -0.1, 3.0]}>
          {Math.round(gates)} gates
        </Label>
      )}

      {isBridge && lanes != null && (
        <Label position={[0, 3.7, -2.2]}>
          {Math.round(lanes)} lanes
        </Label>
      )}

      {isBridge && spans != null && (
        <Label position={[0, 3.0, 2.3]}>
          {Math.round(spans)} spans
        </Label>
      )}

      {isBridge && spanLength != null && (
        <Label position={[-7.5, 2.45, 2.2]}>
          Typical span {fmt(spanLength)}
        </Label>
      )}
    </group>
  );
}
