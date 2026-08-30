import { Html } from "@react-three/drei";
import { useMemo } from "react";
import type { ReactNode } from "react";
import { CatmullRomCurve3, Vector3 } from "three";
import type { TwinResponse } from "../../types/twin";

interface ModelProps {
  twin: TwinResponse;
  colour: string;
  showDimensions: boolean;
}

function numeric(
  dimensions: Record<string, unknown>,
  keys: string[],
  fallback: number,
): number {
  for (const key of keys) {
    const value = Number(dimensions[key]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  return fallback;
}

function sourceBacked(twin: TwinResponse): boolean {
  const representation = String(
    twin.twin.dimensions["representation"] ?? "",
  ).toLowerCase();

  return Boolean(
    twin.twin.is_asset_specific &&
      twin.twin.source_url &&
      twin.twin.fidelity_level !== "L0" &&
      representation.includes("source_backed"),
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
    <Html center position={position} distanceFactor={11}>
      <div
        style={{
          minWidth: "250px",
          padding: "8px 12px",
          border: "1px solid rgba(56,189,248,.45)",
          borderRadius: "8px",
          background: "rgba(7,17,28,.94)",
          color: "#d9f3ff",
          fontSize: "12px",
          lineHeight: 1.45,
          textAlign: "center",
          pointerEvents: "none",
        }}
      >
        {children}
      </div>
    </Html>
  );
}

function PrakasamBarrage({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  const d = twin.twin.dimensions;
  const gates = Math.max(1, Math.round(numeric(d, ["gate_count"], 70)));
  const lengthM = numeric(d, ["length_m"], 1232.92);
  const gateWidthM = numeric(d, ["gate_width_m"], 12.19);
  const gateHeightM = numeric(d, ["gate_height_m"], 3.66);
  const sceneLength = 20;
  const bay = sceneLength / gates;

  return (
    <group rotation={[0, -0.12, 0]}>
      <mesh position={[0, 1.55, 0]} castShadow>
        <boxGeometry args={[sceneLength + 0.35, 0.28, 1.4]} />
        <meshStandardMaterial color="#cfd8dd" roughness={0.78} />
      </mesh>

      <mesh position={[0, 1.79, 0]} castShadow>
        <boxGeometry args={[sceneLength + 0.25, 0.12, 1.15]} />
        <meshStandardMaterial color="#4f5960" roughness={0.75} />
      </mesh>

      {Array.from({ length: gates + 1 }, (_, index) => {
        const x = -sceneLength / 2 + index * bay;
        return (
          <mesh key={`pier-${index}`} position={[x, 0.30, 0]} castShadow>
            <boxGeometry
              args={[Math.max(0.035, bay * 0.18), 2.15, 1.25]}
            />
            <meshStandardMaterial color="#a9b5bc" roughness={0.86} />
          </mesh>
        );
      })}

      {Array.from({ length: gates }, (_, index) => {
        const x = -sceneLength / 2 + (index + 0.5) * bay;
        return (
          <mesh key={`gate-${index}`} position={[x, 0.25, 0.05]}>
            <boxGeometry
              args={[Math.max(0.03, bay * 0.72), 1.05, 0.10]}
            />
            <meshStandardMaterial
              color={colour}
              metalness={0.55}
              roughness={0.38}
            />
          </mesh>
        );
      })}

      <mesh position={[0, -0.88, -2.35]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[24, 6]} />
        <meshStandardMaterial color="#0b668d" transparent opacity={0.66} />
      </mesh>

      <mesh position={[0, -0.90, 2.1]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[24, 5]} />
        <meshStandardMaterial color="#0b5878" transparent opacity={0.52} />
      </mesh>

      {showDimensions && (
        <Badge position={[0, 3.4, 0]}>
          <strong>Prakasam Barrage · source-backed L1</strong>
          <br />
          {lengthM.toLocaleString()} m · {gates} regulator gates
          <br />
          each {gateWidthM.toFixed(2)} × {gateHeightM.toFixed(2)} m
        </Badge>
      )}
    </group>
  );
}

function GodavariArchBridge({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  const d = twin.twin.dimensions;
  const spanCount = Math.max(
    1,
    Math.round(numeric(d, ["span_count"], 28)),
  );
  const spanM = numeric(d, ["main_span_m", "span_m"], 97.552);
  const sceneLength = 21;
  const spanWidth = sceneLength / spanCount;
  const archRise = Math.max(0.42, spanWidth * 0.95);

  const arches = useMemo(
    () =>
      Array.from({ length: spanCount }, (_, spanIndex) => {
        const startX = -sceneLength / 2 + spanIndex * spanWidth;
        return [-0.46, 0.46].map((z) => {
          const points = Array.from({ length: 13 }, (_, pointIndex) => {
            const t = pointIndex / 12;
            return new Vector3(
              startX + t * spanWidth,
              0.38 + 4 * archRise * t * (1 - t),
              z,
            );
          });
          return new CatmullRomCurve3(points);
        });
      }),
    [spanCount, spanWidth, archRise],
  );

  return (
    <group rotation={[0, -0.10, 0]}>
      <mesh position={[0, 0.22, 0]} castShadow>
        <boxGeometry args={[sceneLength, 0.20, 1.18]} />
        <meshStandardMaterial color="#aeb8bf" roughness={0.62} />
      </mesh>

      {arches.flatMap((spanArches, spanIndex) =>
        spanArches.map((curve, archIndex) => (
          <mesh key={`arch-${spanIndex}-${archIndex}`} castShadow>
            <tubeGeometry
              args={[
                curve,
                18,
                Math.max(0.018, spanWidth * 0.035),
                6,
                false,
              ]}
            />
            <meshStandardMaterial color={colour} roughness={0.48} />
          </mesh>
        )),
      )}

      {Array.from({ length: spanCount }, (_, spanIndex) =>
        [0.23, 0.5, 0.77].flatMap((t) => {
          const x =
            -sceneLength / 2 + spanIndex * spanWidth + t * spanWidth;
          const height = 4 * archRise * t * (1 - t);

          return [-0.46, 0.46].map((z) => (
            <mesh
              key={`hanger-${spanIndex}-${t}-${z}`}
              position={[x, 0.39 + height / 2, z]}
            >
              <cylinderGeometry
                args={[0.008, 0.008, Math.max(0.05, height), 5]}
              />
              <meshStandardMaterial color="#dce5e9" metalness={0.52} />
            </mesh>
          ));
        }),
      )}

      {Array.from({ length: spanCount + 1 }, (_, index) => {
        const x = -sceneLength / 2 + index * spanWidth;
        return (
          <mesh key={`pier-${index}`} position={[x, -0.86, 0]} castShadow>
            <boxGeometry
              args={[Math.max(0.07, spanWidth * 0.14), 2.05, 0.78]}
            />
            <meshStandardMaterial color="#87949d" roughness={0.83} />
          </mesh>
        );
      })}

      <mesh position={[0, -1.86, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[24, 7]} />
        <meshStandardMaterial color="#0c618a" transparent opacity={0.64} />
      </mesh>

      {showDimensions && (
        <Badge position={[0, 3.25, 0]}>
          <strong>Godavari Arch Bridge · source-backed L1</strong>
          <br />
          {spanCount} twin bow-string spans · {spanM.toFixed(3)} m/span
        </Badge>
      )}
    </group>
  );
}

function SrisailamDam({
  twin,
  colour,
  showDimensions,
}: ModelProps) {
  const d = twin.twin.dimensions;
  const lengthM = numeric(d, ["length_m"], 512);
  const heightM = numeric(d, ["height_m"], 143.26);
  const spillwayM = numeric(d, ["spillway_length_m"], 266.39);
  const gates = Math.max(1, Math.round(numeric(d, ["gate_count"], 12)));
  const gateWidthM = numeric(d, ["gate_width_m"], 18.3);
  const gateHeightM = numeric(d, ["gate_height_m"], 16.7);

  const sceneLength = 18;
  const sceneHeight = Math.max(
    4.4,
    Math.min(5.5, sceneLength * heightM / lengthM),
  );
  const spillwayScene =
    sceneLength * Math.min(0.8, spillwayM / lengthM);
  const sideBlock = Math.max(
    0.5,
    (sceneLength - spillwayScene) / 2,
  );
  const bay = spillwayScene / gates;

  const deepBed = numeric(d, ["deep_river_bed_level_m"], 152.4);
  const frl = numeric(d, ["full_reservoir_level_m"], 269.75);
  const currentReservoir = Number(
    twin.environment["reservoir_level"]?.value,
  );

  const waterFraction =
    Number.isFinite(currentReservoir) && frl > deepBed
      ? Math.max(
          0.10,
          Math.min(
            0.98,
            (currentReservoir - deepBed) / (frl - deepBed),
          ),
        )
      : 0.76;

  const waterY =
    -sceneHeight / 2 + waterFraction * sceneHeight;

  const leftX =
    -(spillwayScene / 2 + sideBlock / 2);
  const rightX =
    spillwayScene / 2 + sideBlock / 2;

  return (
    <group rotation={[0, -0.12, 0]} position={[0, 0.55, 0]}>
      {[leftX, rightX].map((x) => (
        <mesh key={x} position={[x, 0, 0]} castShadow>
          <boxGeometry args={[sideBlock, sceneHeight, 2.15]} />
          <meshStandardMaterial color="#959fa5" roughness={0.9} />
        </mesh>
      ))}

      <mesh position={[0, -0.2, 0]} castShadow>
        <boxGeometry
          args={[spillwayScene, sceneHeight * 0.92, 2.05]}
        />
        <meshStandardMaterial color="#8e999f" roughness={0.88} />
      </mesh>

      {Array.from({ length: gates + 1 }, (_, index) => {
        const x = -spillwayScene / 2 + index * bay;
        return (
          <mesh
            key={`srisailam-pier-${index}`}
            position={[x, sceneHeight * 0.10, 1.11]}
            castShadow
          >
            <boxGeometry
              args={[
                Math.max(0.09, bay * 0.15),
                sceneHeight * 0.67,
                0.34,
              ]}
            />
            <meshStandardMaterial color="#d0d5d8" roughness={0.78} />
          </mesh>
        );
      })}

      {Array.from({ length: gates }, (_, index) => {
        const x = -spillwayScene / 2 + (index + 0.5) * bay;
        return (
          <mesh
            key={`srisailam-gate-${index}`}
            position={[x, sceneHeight * 0.09, 1.16]}
          >
            <boxGeometry
              args={[bay * 0.72, sceneHeight * 0.32, 0.08]}
            />
            <meshStandardMaterial
              color={colour}
              metalness={0.48}
              roughness={0.4}
            />
          </mesh>
        );
      })}

      <mesh position={[0, sceneHeight / 2 + 0.12, 0]} castShadow>
        <boxGeometry args={[sceneLength + 0.15, 0.22, 1.45]} />
        <meshStandardMaterial color="#434d53" roughness={0.7} />
      </mesh>

      <mesh
        position={[0, waterY, -4.2]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <planeGeometry args={[24, 7]} />
        <meshStandardMaterial color="#0c6d98" transparent opacity={0.66} />
      </mesh>

      <mesh
        position={[0, -sceneHeight / 2 + 0.05, 3.1]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <planeGeometry args={[22, 4]} />
        <meshStandardMaterial color="#0a526e" transparent opacity={0.48} />
      </mesh>

      {showDimensions && (
        <Badge position={[0, sceneHeight / 2 + 2.0, 0]}>
          <strong>Srisailam gravity dam · source-backed L1</strong>
          <br />
          {lengthM.toFixed(0)} m long · {heightM.toFixed(2)} m high
          <br />
          {gates} radial gates · {gateWidthM.toFixed(1)} ×{" "}
          {gateHeightM.toFixed(1)} m
          {Number.isFinite(currentReservoir) && (
            <>
              <br />
              NWDP reservoir level: {currentReservoir.toFixed(2)} m
            </>
          )}
        </Badge>
      )}
    </group>
  );
}

function IllustrativeBridge({ colour }: { colour: string }) {
  return (
    <group>
      <mesh position={[0, 0.4, 0]} castShadow>
        <boxGeometry args={[9, 0.35, 1.8]} />
        <meshStandardMaterial color={colour} roughness={0.65} />
      </mesh>
      {[-3, -1, 1, 3].map((x) => (
        <mesh key={x} position={[x, -0.75, 0]} castShadow>
          <boxGeometry args={[0.34, 2.2, 1.1]} />
          <meshStandardMaterial color="#89969f" />
        </mesh>
      ))}
    </group>
  );
}

function IllustrativeDam({ colour }: { colour: string }) {
  return (
    <group>
      <mesh castShadow>
        <boxGeometry args={[8, 3.5, 2.0]} />
        <meshStandardMaterial color={colour} roughness={0.85} />
      </mesh>
      <mesh
        position={[0, -1.72, -2.5]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <planeGeometry args={[12, 5]} />
        <meshStandardMaterial color="#0b6488" transparent opacity={0.6} />
      </mesh>
    </group>
  );
}

function IllustrativeBarrage({ colour }: { colour: string }) {
  return (
    <group>
      {Array.from({ length: 10 }, (_, index) => {
        const x = -4.5 + index;
        return (
          <group key={index}>
            <mesh position={[x, 0.5, 0]} castShadow>
              <boxGeometry args={[0.12, 2.2, 1.2]} />
              <meshStandardMaterial color="#aab5bb" />
            </mesh>
            {index < 9 && (
              <mesh position={[x + 0.5, 0.2, 0.05]}>
                <boxGeometry args={[0.68, 1.1, 0.08]} />
                <meshStandardMaterial color={colour} />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}

export function AssetSpecificModel(props: ModelProps) {
  const code = props.twin.asset.asset_code;
  const name = props.twin.asset.name.toLowerCase();
  const type = props.twin.asset.asset_type.toLowerCase();
  const backed = sourceBacked(props.twin);

  if (backed && code === "AP_DAM_00001") {
    return <PrakasamBarrage {...props} />;
  }

  if (
    backed &&
    (code === "AP_BR_00001" || name.includes("godavari arch"))
  ) {
    return <GodavariArchBridge {...props} />;
  }

  if (
    backed &&
    (
      code === "AP_DAM_NWDP_AP01VH0059" ||
      name.includes("srisailam")
    )
  ) {
    return <SrisailamDam {...props} />;
  }

  if (type === "bridge") {
    return <IllustrativeBridge colour={props.colour} />;
  }

  if (type === "barrage") {
    return <IllustrativeBarrage colour={props.colour} />;
  }

  return <IllustrativeDam colour={props.colour} />;
}
