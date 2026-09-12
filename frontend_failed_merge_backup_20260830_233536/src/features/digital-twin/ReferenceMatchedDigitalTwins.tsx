
import { Html, Line } from "@react-three/drei";
import type { ReactNode } from "react";
import type { TwinResponse } from "../../types/twin";

type Props = {
  twin: TwinResponse;
  colour: string;
  showDimensions: boolean;
};

type Dims = Record<string, unknown>;
type P3 = [number, number, number];

const CYAN = "#39dcff";
const GLASS = "#497c8d";
const STONE = "#bbb3a2";
const WHITE = "#dedbd2";
const GOLD = "#d6a42c";

function n(d: Dims, key: string): number | null {
  const value = Number(d[key]);
  return Number.isFinite(value) ? value : null;
}

function s(d: Dims, key: string): string {
  return String(d[key] ?? "");
}

function Label({
  children,
  position,
  accent = CYAN,
}: {
  children: ReactNode;
  position: P3;
  accent?: string;
}) {
  return (
    <Html center position={position} distanceFactor={10}>
      <div
        style={{
          padding: "7px 9px",
          borderRadius: 6,
          border: `1px solid ${accent}`,
          background: "rgba(3,14,22,.95)",
          color: "#eefaff",
          fontSize: 10,
          fontWeight: 700,
          lineHeight: 1.35,
          whiteSpace: "nowrap",
          pointerEvents: "none",
          boxShadow: "0 7px 20px rgba(0,0,0,.35)",
        }}
      >
        {children}
      </div>
    </Html>
  );
}

function Measure({
  a,
  b,
  children,
}: {
  a: P3;
  b: P3;
  children: ReactNode;
}) {
  const p: P3 = [
    (a[0] + b[0]) / 2,
    (a[1] + b[1]) / 2 + 0.25,
    (a[2] + b[2]) / 2,
  ];

  return (
    <group>
      <Line points={[a, b]} color={CYAN} lineWidth={1.2} />
      <mesh position={a}>
        <sphereGeometry args={[0.07, 10, 10]} />
        <meshBasicMaterial color={CYAN} />
      </mesh>
      <mesh position={b}>
        <sphereGeometry args={[0.07, 10, 10]} />
        <meshBasicMaterial color={CYAN} />
      </mesh>
      <Label position={p}>{children}</Label>
    </group>
  );
}

function Ground({
  hill = false,
  size = 44,
}: {
  hill?: boolean;
  size?: number;
}) {
  return (
    <group>
      <mesh
        position={[0, -2.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[size, size * 0.72]} />
        <meshStandardMaterial
          color={hill ? "#172517" : "#111d23"}
          roughness={1}
        />
      </mesh>

      {hill && (
        <>
          <mesh
            position={[0, -3.0, 5.2]}
            scale={[1.35, 0.28, 0.75]}
          >
            <sphereGeometry args={[11, 28, 16]} />
            <meshStandardMaterial color="#294126" roughness={1} />
          </mesh>
          <mesh
            position={[-8, -3.1, 4.8]}
            scale={[0.8, 0.2, 0.6]}
          >
            <sphereGeometry args={[8, 24, 14]} />
            <meshStandardMaterial color="#36502d" roughness={1} />
          </mesh>
        </>
      )}
    </group>
  );
}

function Tree({
  position,
  scale = 1,
}: {
  position: P3;
  scale?: number;
}) {
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 0.45, 0]}>
        <cylinderGeometry args={[0.06, 0.09, 0.9, 8]} />
        <meshStandardMaterial color="#73543b" />
      </mesh>
      <mesh position={[0, 1.15, 0]}>
        <sphereGeometry args={[0.5, 12, 9]} />
        <meshStandardMaterial color="#33572f" />
      </mesh>
    </group>
  );
}

function TreeRow({
  start,
  count,
  step,
  scale = 0.5,
}: {
  start: P3;
  count: number;
  step: P3;
  scale?: number;
}) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <Tree
          key={i}
          scale={scale}
          position={[
            start[0] + i * step[0],
            start[1] + i * step[1],
            start[2] + i * step[2],
          ]}
        />
      ))}
    </>
  );
}

/* ============================= AIRPORT ============================= */

function Runway({
  lengthM,
  widthM,
  sceneLength = 25,
  y = -1.82,
}: {
  lengthM: number;
  widthM: number;
  sceneLength?: number;
  y?: number;
}) {
  const width = Math.max(
    0.3,
    (widthM / lengthM) * sceneLength,
  );

  return (
    <group>
      <mesh position={[0, y, 0]} receiveShadow>
        <boxGeometry args={[sceneLength, 0.1, width]} />
        <meshStandardMaterial color="#30363a" roughness={0.95} />
      </mesh>

      <mesh position={[0, y + 0.06, 0]}>
        <boxGeometry args={[sceneLength * 0.84, 0.015, 0.025]} />
        <meshBasicMaterial color="#f4f4f0" />
      </mesh>

      {[-1, 1].map((side) => (
        <group key={side}>
          {Array.from({ length: 7 }, (_, i) => (
            <mesh
              key={i}
              position={[
                side * (sceneLength / 2 - 0.5),
                y + 0.065,
                (i - 3) * (width / 8),
              ]}
            >
              <boxGeometry args={[0.4, 0.015, width / 18]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

function Taxiway({
  position,
  length,
  width = 0.55,
  rotation = 0,
}: {
  position: P3;
  length: number;
  width?: number;
  rotation?: number;
}) {
  return (
    <mesh
      position={position}
      rotation={[0, rotation, 0]}
      receiveShadow
    >
      <boxGeometry args={[length, 0.07, width]} />
      <meshStandardMaterial color="#555d61" roughness={0.95} />
    </mesh>
  );
}

function Airplane({
  position,
  rotation = 0,
}: {
  position: P3;
  rotation?: number;
}) {
  return (
    <group
      position={position}
      rotation={[0, rotation, 0]}
      scale={0.9}
    >
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.08, 0.11, 1.35, 12]} />
        <meshStandardMaterial color="#eef2f3" />
      </mesh>
      <mesh>
        <boxGeometry args={[0.65, 0.04, 1.4]} />
        <meshStandardMaterial color="#dce4e7" />
      </mesh>
      <mesh position={[-0.52, 0.04, 0]}>
        <boxGeometry args={[0.3, 0.04, 0.6]} />
        <meshStandardMaterial color="#dce4e7" />
      </mesh>
    </group>
  );
}

function Tower({ position }: { position: P3 }) {
  return (
    <group position={position}>
      <mesh position={[0, 1.1, 0]}>
        <cylinderGeometry args={[0.2, 0.42, 2.2, 12]} />
        <meshStandardMaterial color="#c7cfd1" />
      </mesh>
      <mesh position={[0, 2.28, 0]}>
        <cylinderGeometry args={[0.52, 0.42, 0.45, 10]} />
        <meshStandardMaterial color="#4e7381" />
      </mesh>
    </group>
  );
}

function Parking({
  position,
  width = 6,
  depth = 3,
}: {
  position: P3;
  width?: number;
  depth?: number;
}) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[width, 0.07, depth]} />
        <meshStandardMaterial color="#30383d" />
      </mesh>
      {Array.from({ length: 8 }, (_, i) => (
        <mesh
          key={i}
          position={[
            -width / 2 + 0.7 + (i % 4) * 1.3,
            0.14,
            -depth / 2 + 0.7 + Math.floor(i / 4) * 1.3,
          ]}
        >
          <boxGeometry args={[0.5, 0.18, 0.28]} />
          <meshStandardMaterial
            color={i % 3 === 0 ? "#879398" : "#c0c8ca"}
          />
        </mesh>
      ))}
    </group>
  );
}

function TirupatiTerminal({ position }: { position: P3 }) {
  const segments = 11;

  return (
    <group position={position}>
      {Array.from({ length: segments }, (_, i) => {
        const t = i / (segments - 1);
        const x = (t - 0.5) * 8.8;
        const z = Math.cos((t - 0.5) * Math.PI) * 0.72;
        const yaw = -(t - 0.5) * 0.26;

        return (
          <group
            key={i}
            position={[x, 0, z]}
            rotation={[0, yaw, 0]}
          >
            <mesh position={[0, 0.85, 0]}>
              <boxGeometry args={[0.95, 1.7, 1.65]} />
              <meshStandardMaterial
                color={GLASS}
                roughness={0.25}
                metalness={0.18}
              />
            </mesh>
            <mesh position={[0, 1.78, 0]}>
              <boxGeometry args={[1.05, 0.14, 1.9]} />
              <meshStandardMaterial color="#d6dad9" />
            </mesh>
          </group>
        );
      })}

      <mesh position={[0, 2.0, 0.2]}>
        <boxGeometry args={[5.8, 0.22, 2.5]} />
        <meshStandardMaterial color="#c4cccd" />
      </mesh>

      {[-2.1, -0.7, 0.7, 2.1].map((x) => (
        <mesh key={x} position={[x, 2.28, 0.2]}>
          <capsuleGeometry args={[0.25, 1.1, 5, 10]} />
          <meshStandardMaterial color="#929ea2" />
        </mesh>
      ))}
    </group>
  );
}

function VizagTerminal({ position }: { position: P3 }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.75, 0]}>
        <boxGeometry args={[8.4, 1.5, 3.3]} />
        <meshStandardMaterial
          color={GLASS}
          roughness={0.3}
          metalness={0.16}
        />
      </mesh>

      {Array.from({ length: 7 }, (_, i) => (
        <mesh
          key={i}
          position={[-3.3 + i * 1.1, 1.6, 0]}
          scale={[1, 0.32, 1]}
        >
          <sphereGeometry args={[0.86, 16, 10]} />
          <meshStandardMaterial color="#e2e1dd" />
        </mesh>
      ))}
    </group>
  );
}

function VijayawadaTerminal({ position }: { position: P3 }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.7, 0]}>
        <boxGeometry args={[6.8, 1.4, 2.5]} />
        <meshStandardMaterial color={GLASS} />
      </mesh>

      <mesh
        position={[-3.0, 0.65, -0.7]}
        rotation={[0, 0.2, 0]}
      >
        <boxGeometry args={[3.5, 1.25, 1.5]} />
        <meshStandardMaterial color="#7796a1" />
      </mesh>

      <mesh
        position={[3.0, 0.65, -0.7]}
        rotation={[0, -0.2, 0]}
      >
        <boxGeometry args={[3.5, 1.25, 1.5]} />
        <meshStandardMaterial color="#7796a1" />
      </mesh>

      <mesh position={[0, 1.55, 0]}>
        <boxGeometry args={[7.4, 0.17, 2.9]} />
        <meshStandardMaterial color="#d5d9d8" />
      </mesh>
    </group>
  );
}

function RegionalTerminal({
  position,
  kind,
}: {
  position: P3;
  kind: "rajahmundry" | "kadapa" | "kurnool";
}) {
  const width =
    kind === "rajahmundry"
      ? 6.3
      : kind === "kurnool"
        ? 4.8
        : 4.2;

  return (
    <group position={position}>
      <mesh position={[0, 0.55, 0]}>
        <boxGeometry args={[width, 1.1, 2.2]} />
        <meshStandardMaterial
          color={kind === "kadapa" ? "#a9b3b6" : GLASS}
          roughness={0.4}
        />
      </mesh>
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[width + 0.4, 0.16, 2.55]} />
        <meshStandardMaterial color="#cbd0ce" />
      </mesh>
      {kind === "rajahmundry" && (
        <mesh position={[0, 1.43, 0]}>
          <boxGeometry args={[2.9, 0.22, 2.0]} />
          <meshStandardMaterial color="#aab7ba" />
        </mesh>
      )}
    </group>
  );
}

function AirportTerminal({
  template,
  position,
}: {
  template: string;
  position: P3;
}) {
  if (template.includes("tirupati")) {
    return <TirupatiTerminal position={position} />;
  }

  if (template.includes("visakhapatnam")) {
    return <VizagTerminal position={position} />;
  }

  if (template.includes("vijayawada")) {
    return <VijayawadaTerminal position={position} />;
  }

  if (template.includes("rajahmundry")) {
    return (
      <RegionalTerminal
        position={position}
        kind="rajahmundry"
      />
    );
  }

  if (template.includes("kurnool")) {
    return (
      <RegionalTerminal
        position={position}
        kind="kurnool"
      />
    );
  }

  return (
    <RegionalTerminal
      position={position}
      kind="kadapa"
    />
  );
}

function AirportTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const template =
    s(d, "template").toLowerCase() ||
    twin.asset.name.toLowerCase();

  const runwayLength = n(d, "runway_length_m") ?? 2000;
  const runwayWidth = n(d, "runway_width_m") ?? 30;
  const stripLength = n(d, "runway_strip_length_m");
  const stripWidth = n(d, "runway_strip_width_m");

  const heading =
    n(d, "runway_true_bearing_deg") ??
    n(d, "runway_axis_deg") ??
    90;

  const secondaryLength =
    n(d, "secondary_runway_length_m");
  const secondaryWidth =
    n(d, "secondary_runway_width_m");
  const secondaryBearing =
    n(d, "secondary_runway_true_bearing_deg");

  const terminalArea = n(d, "terminal_area_sqm");
  const landArea = n(d, "land_area_acres");

  const sceneLength = 25;
  const scale = sceneLength / runwayLength;

  const stripSceneWidth =
    stripWidth != null
      ? Math.max(1.4, Math.min(5.4, stripWidth * scale))
      : 2.2;

  const terminalZ = stripSceneWidth * 0.95 + 4.0;

  const orientation =
    -((heading - 90) * Math.PI) / 180;

  const isVizag = template.includes("visakhapatnam");
  const isVijayawada = template.includes("vijayawada");
  const isRajah = template.includes("rajahmundry");

  return (
    <group rotation={[0, orientation, 0]}>
      <Ground size={48} />

      <mesh position={[0, -1.94, 0]}>
        <boxGeometry
          args={[
            stripLength != null
              ? Math.min(27, stripLength * scale)
              : 26,
            0.05,
            stripSceneWidth,
          ]}
        />
        <meshStandardMaterial color="#31472f" roughness={1} />
      </mesh>

      <Runway
        lengthM={runwayLength}
        widthM={runwayWidth}
        sceneLength={sceneLength}
      />

      {secondaryLength != null &&
        secondaryWidth != null &&
        secondaryBearing != null && (
          <group
            rotation={[
              0,
              -((secondaryBearing - heading) * Math.PI) / 180,
              0,
            ]}
          >
            <Runway
              lengthM={secondaryLength}
              widthM={secondaryWidth}
              sceneLength={
                sceneLength *
                (secondaryLength / runwayLength)
              }
              y={-1.78}
            />
          </group>
        )}

      {Array.from(
        {
          length: isVijayawada ? 3 : isVizag ? 2 : 1,
        },
        (_, i) => (
          <mesh
            key={i}
            position={[
              -4 + i * 5.1,
              -1.76,
              stripSceneWidth * 0.9 + 1.2,
            ]}
          >
            <boxGeometry
              args={[
                isVizag ? 5.2 : 4.5,
                0.08,
                isVizag ? 2.5 : 2.15,
              ]}
            />
            <meshStandardMaterial color="#747b7e" />
          </mesh>
        ),
      )}

      <Taxiway
        position={[-5.4, -1.72, 1.35]}
        length={6}
        rotation={0.55}
      />
      <Taxiway
        position={[4.5, -1.72, 1.35]}
        length={6}
        rotation={-0.55}
      />

      {isRajah && (
        <>
          <Taxiway
            position={[6.1, -1.7, 2.4]}
            length={Math.max(
              1.4,
              (n(d, "taxiway_c_length_m") ?? 257.5) *
                scale,
            )}
            width={Math.max(
              0.18,
              (n(d, "taxiway_c_width_m") ?? 23) * scale,
            )}
            rotation={0.42}
          />
          <mesh position={[8.3, -1.67, 3.0]}>
            <boxGeometry args={[1.3, 0.09, 1.0]} />
            <meshStandardMaterial color="#777e80" />
          </mesh>
        </>
      )}

      <AirportTerminal
        template={template}
        position={[0, -1.55, terminalZ]}
      />

      <Tower position={[5.4, -1.95, terminalZ + 1]} />

      <Parking
        position={[-4.0, -1.78, terminalZ + 4.3]}
        width={6.2}
        depth={2.8}
      />
      <Parking
        position={[4.0, -1.78, terminalZ + 4.3]}
        width={5.2}
        depth={2.8}
      />

      <Taxiway
        position={[0, -1.73, terminalZ + 6.1]}
        length={14}
        width={0.85}
      />

      {[-5, -2.5, 0, 2.5, 5].map((x, i) => (
        <Airplane
          key={x}
          position={[
            x,
            -1.3,
            stripSceneWidth * 0.9 + 1.25,
          ]}
          rotation={i % 2 ? -0.1 : 0.1}
        />
      ))}

      <TreeRow
        start={[-10, -2, terminalZ + 6.8]}
        count={15}
        step={[1.35, 0, 0]}
        scale={0.42}
      />

      {showDimensions && (
        <>
          <Measure
            a={[-12.5, 1.1, -1.7]}
            b={[12.5, 1.1, -1.7]}
          >
            <div>RUNWAY {s(d, "runway_designation")}</div>
            <div style={{ color: CYAN }}>
              {runwayLength.toLocaleString()} m ×{" "}
              {runwayWidth} m
            </div>
          </Measure>

          {stripLength != null &&
            stripWidth != null && (
              <Label position={[-7.4, 0.3, -3.1]}>
                <div>RUNWAY STRIP</div>
                <div style={{ color: CYAN }}>
                  {stripLength.toLocaleString()} m ×{" "}
                  {stripWidth} m
                </div>
              </Label>
            )}

          <Label position={[8.0, 0.3, -2.6]}>
            <div>TRUE AXIS</div>
            <div style={{ color: CYAN }}>
              {heading.toFixed(2)}°
            </div>
          </Label>

          {terminalArea != null && (
            <Label
              position={[0, 3.1, terminalZ]}
              accent="#f2c04c"
            >
              <div>TERMINAL</div>
              <div style={{ color: "#f2c04c" }}>
                {terminalArea.toLocaleString()} m²
              </div>
              <small>area-backed massing</small>
            </Label>
          )}

          {landArea != null && (
            <Label
              position={[-8.0, 3.7, terminalZ + 4.5]}
            >
              <div>AIRPORT LAND</div>
              <div style={{ color: CYAN }}>
                {landArea.toLocaleString()} acres
              </div>
              <small>boundary not inferred</small>
            </Label>
          )}

          {secondaryLength != null &&
            secondaryWidth != null && (
              <Label
                position={[8.0, 3.3, terminalZ + 2.5]}
              >
                <div>
                  SECONDARY RWY{" "}
                  {s(d, "secondary_runway_designation")}
                </div>
                <div style={{ color: CYAN }}>
                  {secondaryLength.toLocaleString()} m ×{" "}
                  {secondaryWidth} m
                </div>
              </Label>
            )}

          <Label position={[0, 5.1, terminalZ + 5.9]}>
            <div>{twin.asset.name}</div>
            <small>
              reference-matched 3D · source-backed dimensions
            </small>
          </Label>
        </>
      )}
    </group>
  );
}

/* ============================= TEMPLE ============================= */

function Walls({
  length = 18,
  width = 12,
  height = 1,
  colour = "#9b9588",
}: {
  length?: number;
  width?: number;
  height?: number;
  colour?: string;
}) {
  return (
    <group position={[0, -1.55, 0]}>
      <mesh position={[0, 0, -width / 2]}>
        <boxGeometry args={[length, height, 0.24]} />
        <meshStandardMaterial color={colour} />
      </mesh>
      <mesh position={[0, 0, width / 2]}>
        <boxGeometry args={[length, height, 0.24]} />
        <meshStandardMaterial color={colour} />
      </mesh>
      <mesh position={[-length / 2, 0, 0]}>
        <boxGeometry args={[0.24, height, width]} />
        <meshStandardMaterial color={colour} />
      </mesh>
      <mesh position={[length / 2, 0, 0]}>
        <boxGeometry args={[0.24, height, width]} />
        <meshStandardMaterial color={colour} />
      </mesh>
    </group>
  );
}

function Gopuram({
  position,
  height,
  width,
  tiers,
  colour = WHITE,
  gold = false,
}: {
  position: P3;
  height: number;
  width: number;
  tiers: number;
  colour?: string;
  gold?: boolean;
}) {
  const count = Math.max(3, Math.min(12, tiers));
  const tierH = height / count;

  return (
    <group position={position}>
      <mesh position={[0, 0.35, 0]}>
        <boxGeometry args={[width * 1.08, 0.7, width * 0.72]} />
        <meshStandardMaterial color={colour} />
      </mesh>

      {Array.from({ length: count }, (_, i) => {
        const taper = 1 - (i / count) * 0.63;
        const y = 0.7 + i * tierH + tierH / 2;

        return (
          <group key={i}>
            <mesh position={[0, y, 0]} castShadow>
              <boxGeometry
                args={[
                  width * taper,
                  tierH * 0.85,
                  width * 0.65 * taper,
                ]}
              />
              <meshStandardMaterial
                color={gold ? GOLD : colour}
                roughness={gold ? 0.42 : 0.92}
                metalness={gold ? 0.45 : 0.02}
              />
            </mesh>

            {[-0.35, 0, 0.35].map((dx) => (
              <mesh
                key={dx}
                position={[
                  dx * width * taper,
                  y,
                  width * 0.34 * taper,
                ]}
              >
                <cylinderGeometry
                  args={[
                    width * 0.035,
                    width * 0.05,
                    tierH * 0.45,
                    7,
                  ]}
                />
                <meshStandardMaterial
                  color={gold ? "#e2b23b" : "#ece9e0"}
                />
              </mesh>
            ))}
          </group>
        );
      })}

      {Array.from({ length: 5 }, (_, i) => (
        <mesh
          key={i}
          position={[
            (i - 2) * width * 0.14,
            height + 0.9,
            0,
          ]}
        >
          <sphereGeometry args={[width * 0.06, 9, 7]} />
          <meshStandardMaterial
            color={gold ? "#ffd34b" : "#d4a33f"}
            metalness={0.35}
          />
        </mesh>
      ))}
    </group>
  );
}

function Mandapam({
  position,
  width,
  depth,
  pillars,
  colour = STONE,
}: {
  position: P3;
  width: number;
  depth: number;
  pillars: number;
  colour?: string;
}) {
  return (
    <group position={position}>
      <mesh position={[0, 1.35, 0]}>
        <boxGeometry args={[width, 0.28, depth]} />
        <meshStandardMaterial color={colour} />
      </mesh>

      {Array.from({ length: pillars }, (_, i) => {
        const cols = Math.ceil(pillars / 2);
        const side = i < cols ? -1 : 1;
        const j = i % cols;

        return (
          <mesh
            key={i}
            position={[
              -width / 2 +
                0.4 +
                j * ((width - 0.8) / Math.max(1, cols - 1)),
              0.55,
              side * (depth / 2 - 0.35),
            ]}
          >
            <cylinderGeometry args={[0.09, 0.11, 1.5, 8]} />
            <meshStandardMaterial color={colour} />
          </mesh>
        );
      })}
    </group>
  );
}

function Shrine({
  position,
  colour = STONE,
  goldRoof = false,
}: {
  position: P3;
  colour?: string;
  goldRoof?: boolean;
}) {
  return (
    <group position={position}>
      <mesh position={[0, 0.55, 0]}>
        <boxGeometry args={[3.6, 1.1, 3.1]} />
        <meshStandardMaterial color={colour} />
      </mesh>
      <Gopuram
        position={[0, 0.9, 0]}
        height={3.1}
        width={2.5}
        tiers={4}
        colour={goldRoof ? GOLD : colour}
        gold={goldRoof}
      />
    </group>
  );
}

function TempleRoads() {
  return (
    <>
      <mesh position={[0, -1.82, 9.3]}>
        <boxGeometry args={[24, 0.07, 1.0]} />
        <meshStandardMaterial color="#303638" />
      </mesh>
      <TreeRow
        start={[-10, -2, 10.2]}
        count={14}
        step={[1.5, 0, 0]}
        scale={0.48}
      />
    </>
  );
}

function TirumalaTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const platformL = n(d, "main_platform_length_m");
  const platformW = n(d, "main_platform_width_m");
  const vimanaH = n(d, "ananda_nilaya_total_height_m");
  const acres = n(d, "complex_land_area_acres");

  return (
    <group>
      <Ground hill />
      <TempleRoads />
      <Walls
        length={20}
        width={14}
        height={1.25}
        colour="#aaa295"
      />

      <Gopuram
        position={[0, -1.45, 7]}
        height={6.3}
        width={4.1}
        tiers={7}
      />
      <Gopuram
        position={[7, -1.45, -4.8]}
        height={5.4}
        width={3.6}
        tiers={6}
      />

      <Shrine
        position={[0, -1.4, -0.5]}
        colour="#c8c2b5"
        goldRoof
      />

      <Mandapam
        position={[-5, -1.55, -0.2]}
        width={5.4}
        depth={3.4}
        pillars={10}
        colour="#c5bfb2"
      />

      <Mandapam
        position={[5.2, -1.55, 1.8]}
        width={4.6}
        depth={3}
        pillars={8}
        colour="#c9c3b7"
      />

      <mesh position={[0, -1.35, 5.1]}>
        <boxGeometry args={[8.5, 0.25, 1.7]} />
        <meshStandardMaterial color="#3f7481" />
      </mesh>

      {showDimensions && (
        <>
          {platformL != null && platformW != null && (
            <Measure
              a={[-10, 1.15, 8.6]}
              b={[10, 1.15, 8.6]}
            >
              <div>MAIN PLATFORM</div>
              <div style={{ color: CYAN }}>
                {platformL.toFixed(1)} m ×{" "}
                {platformW.toFixed(1)} m
              </div>
            </Measure>
          )}

          {vimanaH != null && (
            <Measure
              a={[2.8, -1.2, -0.5]}
              b={[2.8, 4.7, -0.5]}
            >
              <div>ANANDA NILAYAM</div>
              <div style={{ color: "#f2c04c" }}>
                {vimanaH.toFixed(2)} m
              </div>
            </Measure>
          )}

          {acres != null && (
            <Label position={[-7.5, 4.6, -5.5]}>
              <div>TEMPLE COMPLEX</div>
              <div style={{ color: CYAN }}>
                {acres.toLocaleString()} acres
              </div>
            </Label>
          )}

          <Label position={[0, 6.7, 3]}>
            <div>{twin.asset.name}</div>
            <small>
              white gopurams · golden Ananda Nilayam · hill
            </small>
          </Label>
        </>
      )}
    </group>
  );
}

function SrikalahastiTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const height = n(d, "main_gopuram_height_m");

  return (
    <group>
      <Ground hill />
      <TempleRoads />
      <Walls
        length={20}
        width={12}
        height={1.1}
        colour="#aaa69d"
      />

      <Gopuram
        position={[-5.8, -1.45, 6]}
        height={10}
        width={5.4}
        tiers={10}
      />

      <Shrine
        position={[2.5, -1.4, -0.8]}
        colour="#8b877f"
      />

      <Mandapam
        position={[4.6, -1.5, 3.2]}
        width={5.4}
        depth={3.5}
        pillars={10}
        colour="#a39e94"
      />

      <mesh position={[1, 0.4, 2]}>
        <cylinderGeometry args={[0.08, 0.12, 4, 10]} />
        <meshStandardMaterial color="#c99c30" metalness={0.4} />
      </mesh>

      {showDimensions && (
        <>
          {height != null && (
            <Measure
              a={[-2.6, -1.1, 6]}
              b={[-2.6, 8.8, 6]}
            >
              <div>MAIN GOPURAM</div>
              <div style={{ color: CYAN }}>
                {height.toFixed(1)} m
              </div>
            </Measure>
          )}

          <Label position={[4.8, 5, -3]}>
            <div>WEST-FACING TEMPLE</div>
            <small>Swarnamukhi + hill context</small>
          </Label>
        </>
      )}
    </group>
  );
}

function KanakaDurgaTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const height = n(d, "rajagopuram_height_m");
  const storeys = n(d, "rajagopuram_storeys") ?? 9;

  return (
    <group>
      <Ground hill />

      <mesh
        position={[0, -2.7, 0]}
        scale={[1, 0.3, 0.75]}
      >
        <sphereGeometry args={[10, 28, 16]} />
        <meshStandardMaterial color="#504b36" />
      </mesh>

      <mesh position={[2.3, -0.9, 0]}>
        <boxGeometry args={[8, 2, 5.4]} />
        <meshStandardMaterial color="#b69b65" />
      </mesh>

      <Gopuram
        position={[-4.3, -1.35, 1.4]}
        height={8.3}
        width={4.5}
        tiers={Math.round(storeys)}
        colour="#d2b16e"
      />

      <Shrine
        position={[2.2, -0.4, -0.5]}
        colour="#b99b63"
      />

      {showDimensions && (
        <>
          {height != null && (
            <Measure
              a={[-1.7, -1.1, 1.4]}
              b={[-1.7, 7.3, 1.4]}
            >
              <div>RAJAGOPURAM</div>
              <div style={{ color: CYAN }}>
                {height.toFixed(2)} m ·{" "}
                {Math.round(storeys)} storeys
              </div>
            </Measure>
          )}

          <Label position={[4.3, 4.6, 2]}>
            <div>INDRAKEELADRI HILL</div>
            <small>Dravidian temple form</small>
          </Label>
        </>
      )}
    </group>
  );
}

function SrisailamTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const realL = n(d, "enclosure_length_m");
  const realW = n(d, "enclosure_width_m");
  const wallMin = n(d, "wall_height_min_m");
  const wallMax = n(d, "wall_height_max_m");

  const ratio =
    realL != null && realW != null
      ? realW / realL
      : 0.77;

  const sceneL = 21;
  const sceneW = sceneL * ratio;

  return (
    <group>
      <Ground />

      <Walls
        length={sceneL}
        width={sceneW}
        height={1.4}
        colour="#77736b"
      />

      <Gopuram
        position={[0, -1.45, sceneW / 2]}
        height={5.2}
        width={3.8}
        tiers={6}
        colour="#8e887d"
      />

      <Shrine
        position={[0, -1.2, 0]}
        colour="#77736b"
      />

      <Mandapam
        position={[-5, -1.45, 0.6]}
        width={4.6}
        depth={3.5}
        pillars={8}
        colour="#7d786f"
      />

      <Mandapam
        position={[5, -1.45, 0.6]}
        width={4.6}
        depth={3.5}
        pillars={8}
        colour="#7d786f"
      />

      {showDimensions && (
        <>
          {realL != null && realW != null && (
            <Measure
              a={[-sceneL / 2, 1.3, sceneW / 2 + 1.2]}
              b={[sceneL / 2, 1.3, sceneW / 2 + 1.2]}
            >
              <div>HISTORICAL ENCLOSURE</div>
              <div style={{ color: CYAN }}>
                {realL.toFixed(1)} m ×{" "}
                {realW.toFixed(1)} m
              </div>
            </Measure>
          )}

          {wallMin != null && wallMax != null && (
            <Label position={[7, 3.2, -4]}>
              <div>HISTORICAL WALL HEIGHT</div>
              <div style={{ color: CYAN }}>
                {wallMin.toFixed(1)}–{wallMax.toFixed(1)} m
              </div>
              <small>not current survey geometry</small>
            </Label>
          )}
        </>
      )}
    </group>
  );
}

function SimhachalamTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const elevation = n(d, "site_elevation_m_asl");

  return (
    <group>
      <Ground hill />

      <Walls
        length={15}
        width={11}
        height={1}
        colour="#545653"
      />

      <Shrine
        position={[0, -1.3, -0.5]}
        colour="#4f5351"
      />

      <Gopuram
        position={[0, -1.45, 5.5]}
        height={5.4}
        width={3.8}
        tiers={6}
        colour="#595c59"
      />

      <Mandapam
        position={[0, -1.5, -5]}
        width={5.4}
        depth={4.2}
        pillars={16}
        colour="#4d504e"
      />

      {showDimensions && (
        <>
          <Label position={[0, 6, 0]}>
            <div>SQUARE SHRINE · HIGH TOWER</div>
            <small>dark granite · 16-pillared mandapam</small>
          </Label>

          {elevation != null && (
            <Label position={[6.5, 3, 2]}>
              <div>SITE ELEVATION</div>
              <div style={{ color: CYAN }}>
                {elevation.toFixed(0)} m ASL
              </div>
            </Label>
          )}

          <Label position={[-6.5, 3, 2]}>
            <div>ENVELOPE NOT PUBLISHED</div>
            <small>form matched · scale illustrative</small>
          </Label>
        </>
      )}
    </group>
  );
}

function AnnavaramTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const deityHeight = n(d, "deity_height_m");

  return (
    <group>
      <Ground hill />

      <mesh position={[0, -1.2, 0]}>
        <cylinderGeometry args={[4.3, 4.7, 1.6, 24]} />
        <meshStandardMaterial color="#b79e69" />
      </mesh>

      <mesh position={[0, 0.25, 0]}>
        <cylinderGeometry args={[3.3, 3.8, 1.4, 24]} />
        <meshStandardMaterial color="#c5aa71" />
      </mesh>

      <Gopuram
        position={[0, 0.5, 0]}
        height={3.6}
        width={2.8}
        tiers={4}
        colour="#d0b278"
      />

      <Gopuram
        position={[0, -1.45, 5.7]}
        height={4.5}
        width={3.3}
        tiers={5}
        colour="#c4a56c"
      />

      {showDimensions && (
        <>
          <Label position={[0, 5.7, 0]}>
            <div>TWO-STOREY SHRINE</div>
            <small>Ratnagiri hill context</small>
          </Label>

          {deityHeight != null && (
            <Label position={[5, 2.7, 0]}>
              <div>DEITY HEIGHT</div>
              <div style={{ color: CYAN }}>
                ~{deityHeight.toFixed(1)} m
              </div>
            </Label>
          )}

          <Label position={[-5.3, 2.7, 0]}>
            <div>ENVELOPE NOT PUBLISHED</div>
            <small>form matched · scale illustrative</small>
          </Label>
        </>
      )}
    </group>
  );
}

function DwarakaTwin({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const siteHeight = n(d, "temple_site_height_m");
  const storeys = n(d, "main_gopuram_storeys") ?? 5;

  return (
    <group>
      <Ground hill />

      <mesh position={[2, -0.8, 0]}>
        <boxGeometry args={[8.2, 2.3, 5.8]} />
        <meshStandardMaterial color="#b29a6b" />
      </mesh>

      <Gopuram
        position={[-4.4, -1.45, 1]}
        height={6.2}
        width={4}
        tiers={Math.round(storeys)}
        colour="#cdae73"
      />

      <Mandapam
        position={[3.4, -1.3, -4]}
        width={5}
        depth={3.6}
        pillars={10}
        colour="#a98e62"
      />

      {showDimensions && (
        <>
          <Label position={[-4.4, 5.7, 1]}>
            <div>MAIN GOPURAM</div>
            <div style={{ color: CYAN }}>
              {Math.round(storeys)} storeys
            </div>
          </Label>

          {siteHeight != null && (
            <Label position={[5.2, 3, 1]}>
              <div>HILL-SITE HEIGHT</div>
              <div style={{ color: CYAN }}>
                ~{siteHeight.toFixed(1)} m
              </div>
            </Label>
          )}

          <Label position={[0, 6.6, -2]}>
            <small>
              hill temple · multiple mantapams · exact
              envelope unavailable
            </small>
          </Label>
        </>
      )}
    </group>
  );
}

function TempleTwin(props: Props) {
  const d = props.twin.twin.dimensions;
  const template =
    s(d, "template").toLowerCase() ||
    props.twin.asset.name.toLowerCase();

  if (
    template.includes("tirumala") &&
    !template.includes("dwaraka")
  ) {
    return <TirumalaTwin {...props} />;
  }

  if (
    template.includes("srikalahasti") ||
    template.includes("kalahasti")
  ) {
    return <SrikalahastiTwin {...props} />;
  }

  if (
    template.includes("kanaka") ||
    template.includes("durga")
  ) {
    return <KanakaDurgaTwin {...props} />;
  }

  if (
    template.includes("srisailam") ||
    template.includes("mallikarjuna")
  ) {
    return <SrisailamTwin {...props} />;
  }

  if (template.includes("simhachalam")) {
    return <SimhachalamTwin {...props} />;
  }

  if (template.includes("annavaram")) {
    return <AnnavaramTwin {...props} />;
  }

  if (template.includes("dwaraka")) {
    return <DwarakaTwin {...props} />;
  }

  return <SimhachalamTwin {...props} />;
}

export function ReferenceMatchedDigitalTwin(
  props: Props,
) {
  const type =
    props.twin.asset.asset_type.toLowerCase();

  if (type === "airport") {
    return <AirportTwin {...props} />;
  }

  return <TempleTwin {...props} />;
}
