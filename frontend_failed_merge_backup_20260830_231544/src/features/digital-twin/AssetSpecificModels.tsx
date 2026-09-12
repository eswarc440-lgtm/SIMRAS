import { Html } from "@react-three/drei";
import { useMemo } from "react";
import type { ReactNode } from "react";
import { CatmullRomCurve3, Vector3 } from "three";
import type { TwinResponse } from "../../types/twin";
import { ReferenceMatchedDigitalTwin } from "./ReferenceMatchedDigitalTwins";
type Props = {
  twin: TwinResponse;
  colour: string;
  showDimensions: boolean;
};

type Dims = Record<string, unknown>;

function n(d: Dims, keys: string[], fallback: number): number {
  for (const key of keys) {
    const value = Number(d[key]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return fallback;
}

function s(d: Dims, key: string): string {
  return String(d[key] ?? "");
}

function sourceBacked(twin: TwinResponse): boolean {
  const representation = String(
    twin.twin.dimensions["representation"] ?? "",
  ).toLowerCase();

  return (
    twin.twin.fidelity_level !== "L0" &&
    twin.twin.is_asset_specific &&
    (
      representation.includes("source_backed") ||
      representation.includes("source_extracted") ||
      Boolean(twin.twin.source_url)
    )
  );
}

function Badge({
  children,
  position,
}: {
  children: ReactNode;
  position: [number, number, number];
}) {
  return (
    <Html center position={position} distanceFactor={10}>
      <div
        style={{
          minWidth: "260px",
          maxWidth: "360px",
          padding: "9px 12px",
          border: "1px solid rgba(56,189,248,.45)",
          borderRadius: 8,
          background: "rgba(4,13,24,.94)",
          color: "#e2f5ff",
          fontSize: 12,
          lineHeight: 1.5,
          textAlign: "center",
          pointerEvents: "none",
          whiteSpace: "nowrap",
        }}
      >
        {children}
      </div>
    </Html>
  );
}

function Ground() {
  return (
    <mesh
      position={[0, -2.0, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
      receiveShadow
    >
      <planeGeometry args={[34, 24]} />
      <meshStandardMaterial color="#15222c" roughness={1} />
    </mesh>
  );
}

function Water({
  y = -1.92,
  z = 0,
  width = 30,
  depth = 10,
}: {
  y?: number;
  z?: number;
  width?: number;
  depth?: number;
}) {
  return (
    <mesh position={[0, y, z]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[width, depth]} />
      <meshStandardMaterial
        color="#0a648c"
        transparent
        opacity={0.62}
        roughness={0.35}
      />
    </mesh>
  );
}

function DimensionText({ twin }: { twin: TwinResponse }) {
  const d = twin.twin.dimensions;
  const entries = Object.entries(d).filter(([key, value]) => {
    if (value == null) return false;
    if (
      [
        "template",
        "representation",
        "source_basis",
        "source_references",
        "alignment_status",
        "structural_form",
        "dam_type",
      ].includes(key)
    ) return false;

    return typeof value === "number" || typeof value === "string";
  });

  if (!sourceBacked(twin) || entries.length === 0) return null;

  const labels = entries
    .slice(0, 8)
    .map(([key, value]) => {
      const name = key
        .replace(/_m3s$/, " m3/s")
        .replace(/_m$/, " m")
        .replaceAll("_", " ");
      return `${name}: ${String(value)}`;
    })
    .join(" Â· ");

  return (
    <Badge position={[0, 4.9, 0]}>
      <strong>{twin.asset.name}</strong>
      <br />
      {labels}
    </Badge>
  );
}

function GirderBridge({ twin, colour }: Props) {
  const d = twin.twin.dimensions;
  const spans = Math.max(2, Math.min(18, Math.round(n(d, ["span_count"], 5))));
  const width = Math.max(2.2, Math.min(5.0, n(d, ["width_m", "deck_width_m"], 12) / 4));
  const height = Math.max(1.8, Math.min(4.0, n(d, ["pier_height_m", "height_m"], 12) / 4));
  const length = 18;

  return (
    <group>
      <mesh position={[0, 0.7, 0]} castShadow receiveShadow>
        <boxGeometry args={[length, 0.5, width]} />
        <meshStandardMaterial color={colour} roughness={0.62} />
      </mesh>

      {Array.from({ length: spans - 1 }, (_, index) => {
        const x = -length / 2 + ((index + 1) * length) / spans;
        return (
          <mesh key={index} position={[x, -0.7, 0]} castShadow>
            <boxGeometry args={[0.42, height, width * 0.62]} />
            <meshStandardMaterial color="#85929b" roughness={0.88} />
          </mesh>
        );
      })}

      <Water z={0} />
      
    </group>
  );
}

function CurvedFlyover({ twin, colour }: Props) {
  const d = twin.twin.dimensions;
  const lanes = Math.max(2, Math.min(8, Math.round(n(d, ["lane_count"], 4))));
  const width = Math.max(2.8, Math.min(6.4, lanes * 0.78));
  const sourceSpan = n(d, ["typical_span_m", "span_m"], 45);
  const lengthM = n(d, ["length_m"], n(d, ["project_corridor_length_m"], 1500));
  const spanCount = Math.max(
    6,
    Math.min(40, Math.round(lengthM / Math.max(25, sourceSpan))),
  );

  const curve = useMemo(
    () =>
      new CatmullRomCurve3([
        new Vector3(-11, 0.8, -3.6),
        new Vector3(-7.5, 1.0, -1.8),
        new Vector3(-3.5, 1.15, 0.4),
        new Vector3(0.5, 1.2, 1.25),
        new Vector3(4.5, 1.15, 0.5),
        new Vector3(8.5, 1.0, -1.7),
        new Vector3(11, 0.95, -3.0),
      ]),
    [],
  );

  const samples = useMemo(
    () =>
      Array.from({ length: 90 }, (_, index) =>
        curve.getPoint(index / 89),
      ),
    [curve],
  );

  return (
    <group>
      {samples.slice(0, -1).map((point, index) => {
        const next = samples[index + 1];
        const dx = next.x - point.x;
        const dz = next.z - point.z;
        const length = Math.hypot(dx, dz);
        const angle = Math.atan2(dz, dx);

        return (
          <mesh
            key={`deck-${index}`}
            position={[
              (point.x + next.x) / 2,
              (point.y + next.y) / 2,
              (point.z + next.z) / 2,
            ]}
            rotation={[0, -angle, 0]}
            castShadow
            receiveShadow
          >
            <boxGeometry args={[length + 0.05, 0.34, width]} />
            <meshStandardMaterial color="#3d474d" roughness={0.68} />
          </mesh>
        );
      })}

      {Array.from({ length: spanCount }, (_, index) => {
        const t = (index + 0.5) / spanCount;
        const p = curve.getPoint(t);
        return (
          <group key={`pier-${index}`}>
            <mesh position={[p.x, -0.55, p.z]} castShadow>
              <boxGeometry args={[0.42, 2.9, 1.15]} />
              <meshStandardMaterial color="#909ba2" roughness={0.86} />
            </mesh>
          </group>
        );
      })}

      {Array.from({ length: lanes - 1 }, (_, laneIndex) => {
        const offset = ((laneIndex + 1) / lanes - 0.5) * width;
        return samples.slice(0, -1).map((point, index) => {
          const next = samples[index + 1];
          const dx = next.x - point.x;
          const dz = next.z - point.z;
          const segment = Math.hypot(dx, dz);
          const angle = Math.atan2(dz, dx);
          const nx = -Math.sin(angle);
          const nz = Math.cos(angle);

          return (
            <mesh
              key={`lane-${laneIndex}-${index}`}
              position={[
                (point.x + next.x) / 2 + nx * offset,
                1.39,
                (point.z + next.z) / 2 + nz * offset,
              ]}
              rotation={[0, -angle, 0]}
            >
              <boxGeometry args={[segment * 0.72, 0.025, 0.035]} />
              <meshStandardMaterial color="#f4f4f0" />
            </mesh>
          );
        });
      })}

      <mesh position={[0, -1.93, -6.0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[32, 8]} />
        <meshStandardMaterial color="#896c4c" roughness={0.88} />
      </mesh>

      
    </group>
  );
}

function ArchBridge({ twin, colour }: Props) {
  const d = twin.twin.dimensions;
  const spans = Math.max(2, Math.min(32, Math.round(n(d, ["span_count"], 8))));
  const length = 22;
  const spanWidth = length / spans;
  const rise = Math.max(0.45, Math.min(1.3, spanWidth * 0.75));

  const arches = useMemo(
    () =>
      Array.from({ length: spans }, (_, spanIndex) => {
        const startX = -length / 2 + spanIndex * spanWidth;
        return [-0.55, 0.55].map((z) => {
          const pts = Array.from({ length: 12 }, (_, i) => {
            const t = i / 11;
            return new Vector3(
              startX + t * spanWidth,
              0.5 + 4 * rise * t * (1 - t),
              z,
            );
          });
          return new CatmullRomCurve3(pts);
        });
      }),
    [spans, spanWidth, rise],
  );

  return (
    <group>
      <mesh position={[0, 0.38, 0]} castShadow>
        <boxGeometry args={[length, 0.22, 1.45]} />
        <meshStandardMaterial color="#9da9b0" roughness={0.72} />
      </mesh>

      {arches.flatMap((pair, spanIndex) =>
        pair.map((curve, archIndex) => (
          <mesh key={`${spanIndex}-${archIndex}`} castShadow>
            <tubeGeometry args={[curve, 20, 0.035, 6, false]} />
            <meshStandardMaterial color={colour} metalness={0.18} />
          </mesh>
        )),
      )}

      {Array.from({ length: spans + 1 }, (_, index) => {
        const x = -length / 2 + index * spanWidth;
        return (
          <mesh key={index} position={[x, -0.92, 0]} castShadow>
            <boxGeometry args={[0.16, 2.5, 0.86]} />
            <meshStandardMaterial color="#87949d" />
          </mesh>
        );
      })}

      <Water />
      
    </group>
  );
}

function GravityDam({ twin, colour }: Props) {
  const d = twin.twin.dimensions;
  const gates = Math.max(3, Math.min(24, Math.round(n(d, ["gate_count"], 8))));
  const damLengthM = n(d, ["length_m"], 400);
  const damHeightM = n(d, ["height_m"], 45);
  const spillwayM = n(d, ["spillway_length_m"], damLengthM * 0.45);

  const length = 18;
  const height = Math.max(3.4, Math.min(6.0, (damHeightM / damLengthM) * 34));
  const spillway = Math.max(5, Math.min(13, (spillwayM / damLengthM) * length));
  const side = (length - spillway) / 2;
  const bay = spillway / gates;

  return (
    <group>
      <mesh position={[-(spillway / 2 + side / 2), 0, 0]} castShadow>
        <boxGeometry args={[side, height, 2.6]} />
        <meshStandardMaterial color="#969fa4" roughness={0.92} />
      </mesh>

      <mesh position={[spillway / 2 + side / 2, 0, 0]} castShadow>
        <boxGeometry args={[side, height, 2.6]} />
        <meshStandardMaterial color="#969fa4" roughness={0.92} />
      </mesh>

      <mesh position={[0, -0.35, 0]} castShadow>
        <boxGeometry args={[spillway, height * 0.86, 2.45]} />
        <meshStandardMaterial color="#8e999f" roughness={0.9} />
      </mesh>

      {Array.from({ length: gates }, (_, index) => {
        const x = -spillway / 2 + (index + 0.5) * bay;
        return (
          <mesh key={index} position={[x, 0.45, 1.28]}>
            <boxGeometry args={[bay * 0.66, height * 0.3, 0.08]} />
            <meshStandardMaterial color={colour} metalness={0.42} />
          </mesh>
        );
      })}

      <mesh position={[0, height / 2 + 0.15, 0]} castShadow>
        <boxGeometry args={[length, 0.25, 1.7]} />
        <meshStandardMaterial color="#404a50" roughness={0.72} />
      </mesh>

      <Water z={-5.1} depth={7} />
      
    </group>
  );
}

function GatedBarrage({ twin, colour }: Props) {
  const d = twin.twin.dimensions;
  const gates = Math.max(4, Math.min(80, Math.round(n(d, ["gate_count"], 12))));
  const sceneLength = 22;
  const bay = sceneLength / gates;

  return (
    <group>
      <mesh position={[0, 1.55, 0]} castShadow>
        <boxGeometry args={[sceneLength + 0.2, 0.26, 1.55]} />
        <meshStandardMaterial color="#c9d2d7" roughness={0.82} />
      </mesh>

      {Array.from({ length: gates + 1 }, (_, index) => {
        const x = -sceneLength / 2 + index * bay;
        return (
          <mesh key={`pier-${index}`} position={[x, 0.2, 0]} castShadow>
            <boxGeometry args={[Math.max(0.035, bay * 0.18), 2.45, 1.35]} />
            <meshStandardMaterial color="#a7b2b8" roughness={0.88} />
          </mesh>
        );
      })}

      {Array.from({ length: gates }, (_, index) => {
        const x = -sceneLength / 2 + (index + 0.5) * bay;
        return (
          <mesh key={`gate-${index}`} position={[x, 0.25, 0.04]}>
            <boxGeometry args={[Math.max(0.025, bay * 0.7), 1.2, 0.08]} />
            <meshStandardMaterial color={colour} metalness={0.52} />
          </mesh>
        );
      })}

      <Water width={28} depth={10} />
      
    </group>
  );
}

function Airport({ twin }: Props) {
  const d = twin.twin.dimensions;
  const lengthM = n(d, ["runway_length_m", "length_m"], 2400);
  const widthM = n(d, ["runway_width_m", "width_m"], 45);
  const aspect = Math.max(12, Math.min(24, lengthM / 150));
  const width = Math.max(1.2, Math.min(3.2, widthM / 20));

  return (
    <group rotation={[0, -0.25, 0]}>
      <mesh position={[0, -0.05, 0]} receiveShadow>
        <boxGeometry args={[aspect, 0.16, width]} />
        <meshStandardMaterial color="#30373b" roughness={0.84} />
      </mesh>

      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[aspect * 0.92, 0.02, 0.05]} />
        <meshStandardMaterial color="#f5f6ef" />
      </mesh>

      {Array.from({ length: 10 }, (_, index) => {
        const x = -aspect / 2 + 0.8 + index * ((aspect - 1.6) / 9);
        return (
          <mesh key={index} position={[x, 0.06, 0]}>
            <boxGeometry args={[0.32, 0.025, width * 0.5]} />
            <meshStandardMaterial color="#ffffff" />
          </mesh>
        );
      })}

      <mesh position={[0, 0.18, width * 1.7]}>
        <boxGeometry args={[aspect * 0.5, 0.12, width * 0.45]} />
        <meshStandardMaterial color="#666f75" />
      </mesh>

      <mesh position={[aspect * 0.15, 0.8, width * 2.9]} castShadow>
        <boxGeometry args={[4.8, 1.6, 2.0]} />
        <meshStandardMaterial color="#7a8b94" roughness={0.72} />
      </mesh>

      <Ground />
      
    </group>
  );
}

function Port({ twin }: Props) {
  const d = twin.twin.dimensions;
  const berthM = n(d, ["berth_length_m", "quay_length_m", "length_m"], 240);
  const draftM = n(d, ["permissible_draft_m", "draft_m"], 12);
  const quay = Math.max(10, Math.min(22, berthM / 20));

  return (
    <group>
      <mesh position={[0, -0.3, 1.5]} castShadow>
        <boxGeometry args={[quay, 0.8, 4]} />
        <meshStandardMaterial color="#666e72" roughness={0.88} />
      </mesh>

      <Water z={-3.5} width={30} depth={8} />

      <mesh position={[0, 0.15, -2.5]} castShadow>
        <boxGeometry args={[quay * 0.65, 0.72, 2.2]} />
        <meshStandardMaterial color="#35475a" metalness={0.1} />
      </mesh>

      <mesh position={[0, 0.85, -2.5]}>
        <boxGeometry args={[quay * 0.42, 0.7, 1.35]} />
        <meshStandardMaterial color="#82939d" />
      </mesh>

      <Badge position={[0, 4.7, 0]}>
        <strong>{twin.asset.name}</strong>
        <br />
        Berth/quay: {berthM} m Â· permissible draft: {draftM} m
      </Badge>
    </group>
  );
}

function Temple({ twin }: Props) {
  const d = twin.twin.dimensions;
  const gopuramM = n(d, ["gopuram_height_m", "height_m"], 24);
  const scale = Math.max(2.6, Math.min(5.5, gopuramM / 7));

  return (
    <group>
      <mesh position={[0, -1.25, 0]} castShadow>
        <boxGeometry args={[8, 1.2, 6]} />
        <meshStandardMaterial color="#c9ad74" roughness={0.94} />
      </mesh>

      {Array.from({ length: 6 }, (_, index) => {
        const t = index / 5;
        const w = scale * (1 - t * 0.62);
        return (
          <mesh
            key={index}
            position={[0, -0.3 + index * 0.72, -1.9]}
            castShadow
          >
            <boxGeometry args={[w, 0.62, w * 0.45]} />
            <meshStandardMaterial color="#d6b36d" roughness={0.92} />
          </mesh>
        );
      })}

      <mesh position={[0, 0.05, 0.8]} castShadow>
        <boxGeometry args={[3.3, 2.0, 2.6]} />
        <meshStandardMaterial color="#b99a61" roughness={0.92} />
      </mesh>

      <Ground />
      
    </group>
  );
}

function Generic({ twin, colour }: Props) {
  return (
    <group>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[7, 3, 5]} />
        <meshStandardMaterial color={colour} roughness={0.82} />
      </mesh>
      <Ground />
      
    </group>
  );
}

export function AssetSpecificModel(props: Props) {
  const twin = props.twin;
  const d = twin.twin.dimensions;
  const explicit = s(d, "template").toLowerCase();
  const name = twin.asset.name.toLowerCase();
  const type = twin.asset.asset_type.toLowerCase();

  if (type === "airport" || type === "temple") {
    return <ReferenceMatchedDigitalTwin {...props} />;
  }

  const subtype = String(twin.asset.subtype ?? "").toLowerCase();
const template =
    explicit ||
    (
      name.includes("flyover") ||
      subtype.includes("flyover") ||
      subtype.includes("viaduct")
        ? "curved_flyover"
        : name.includes("arch") || subtype.includes("arch")
          ? "arch_bridge"
          : type === "bridge"
            ? "girder_bridge"
            : type === "barrage"
              ? "gated_barrage"
              : type === "dam"
                ? "gravity_dam"
                : type === "airport"
                  ? "airport_runway"
                  : type === "port"
                    ? "port_berth"
                    : type === "temple"
                      ? "temple_complex"
                      : "generic"
    );

  if (template === "curved_flyover") return <CurvedFlyover {...props} />;
  if (template === "arch_bridge") return <ArchBridge {...props} />;
  if (template === "girder_bridge") return <GirderBridge {...props} />;
  if (template === "gated_barrage") return <GatedBarrage {...props} />;
  if (
    template === "gravity_dam" ||
    template === "earthfill_dam" ||
    template === "dam"
  ) {
    return <GravityDam {...props} />;
  }
  if (template === "airport_runway") return <Airport {...props} />;
  if (template === "port_berth") return <Port {...props} />;
  if (template === "temple_complex") return <Temple {...props} />;

  return <Generic {...props} />;
}