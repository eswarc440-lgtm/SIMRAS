import { Html } from "@react-three/drei";
import type { ReactNode } from "react";
import type { TwinResponse } from "../../types/twin";

type Props = {
  twin: TwinResponse;
  colour: string;
  showDimensions: boolean;
};

type Dims = Record<string, unknown>;

function num(d: Dims, key: string): number | null {
  const value = Number(d[key]);
  return Number.isFinite(value) ? value : null;
}

function txt(d: Dims, key: string): string {
  return String(d[key] ?? "");
}

function Badge({
  children,
  position,
  gold = false,
}: {
  children: ReactNode;
  position: [number, number, number];
  gold?: boolean;
}) {
  return (
    <Html center position={position} distanceFactor={10}>
      <div
        style={{
          padding: "6px 9px",
          borderRadius: 6,
          border: `1px solid ${
            gold
              ? "rgba(245,190,70,.8)"
              : "rgba(78,205,255,.78)"
          }`,
          background: "rgba(3,14,22,.95)",
          color: "#eefaff",
          fontSize: 10,
          fontWeight: 700,
          lineHeight: 1.35,
          whiteSpace: "nowrap",
          pointerEvents: "none",
        }}
      >
        {children}
      </div>
    </Html>
  );
}

function Ground({ hill = false }: { hill?: boolean }) {
  return (
    <group>
      {hill && (
        <mesh
          position={[0, -2.25, 0]}
          scale={[1.35, 0.25, 1]}
        >
          <sphereGeometry args={[9, 28, 16]} />
          <meshStandardMaterial
            color="#655c3f"
            roughness={1}
          />
        </mesh>
      )}

      <mesh
        position={[0, -2, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[38, 28]} />
        <meshStandardMaterial
          color={hill ? "#4d5b3d" : "#17252c"}
          roughness={1}
        />
      </mesh>
    </group>
  );
}

function TieredTower({
  storeys,
  height,
  width,
  position,
  colour,
}: {
  storeys: number;
  height: number;
  width: number;
  position: [number, number, number];
  colour: string;
}) {
  const count = Math.max(2, Math.min(12, storeys));
  const h = height / count;

  return (
    <group position={position}>
      {Array.from({ length: count }, (_, i) => {
        const taper = 1 - (i / count) * 0.62;

        return (
          <mesh
            key={i}
            position={[0, i * h + h / 2, 0]}
            castShadow
          >
            <boxGeometry
              args={[
                width * taper,
                h * 0.9,
                width * 0.65 * taper,
              ]}
            />
            <meshStandardMaterial
              color={colour}
              roughness={0.92}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function Runway({
  lengthM,
  widthM,
  sceneLength,
  y = -1.82,
}: {
  lengthM: number;
  widthM: number;
  sceneLength: number;
  y?: number;
}) {
  const sceneWidth = Math.max(
    0.22,
    (widthM / lengthM) * sceneLength,
  );

  return (
    <group>
      <mesh position={[0, y, 0]} receiveShadow>
        <boxGeometry
          args={[sceneLength, 0.12, sceneWidth]}
        />
        <meshStandardMaterial
          color="#30363a"
          roughness={0.86}
        />
      </mesh>

      <mesh position={[0, y + 0.07, 0]}>
        <boxGeometry
          args={[sceneLength * 0.86, 0.018, 0.025]}
        />
        <meshStandardMaterial color="#ffffff" />
      </mesh>
    </group>
  );
}

function AirportComplex({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;

  const rL = num(d, "runway_length_m") ?? 2000;
  const rW = num(d, "runway_width_m") ?? 30;
  const sL = num(d, "runway_strip_length_m");
  const sW = num(d, "runway_strip_width_m");
  const heading =
    num(d, "runway_true_bearing_deg") ??
    num(d, "runway_axis_deg") ??
    90;

  const terminalArea = num(d, "terminal_area_sqm");
  const landArea = num(d, "land_area_acres");

  const apronL = num(d, "apron_length_m");
  const apronW = num(d, "apron_width_m");

  const secondaryL = num(
    d,
    "secondary_runway_length_m",
  );
  const secondaryW = num(
    d,
    "secondary_runway_width_m",
  );
  const secondaryBearing = num(
    d,
    "secondary_runway_true_bearing_deg",
  );

  const taxiL = num(d, "taxiway_c_length_m");
  const taxiW = num(d, "taxiway_c_width_m");
  const isoL = num(d, "isolation_bay_length_m");
  const isoW = num(d, "isolation_bay_width_m");

  const sceneL = 22;
  const scale = sceneL / rL;

  const stripSceneL =
    sL != null ? Math.min(25, sL * scale) : 23;

  const stripSceneW =
    sW != null
      ? Math.max(1.2, Math.min(5.8, sW * scale))
      : 2;

  // When only terminal AREA is published, this preserves area
  // approximately but does NOT claim an exact source footprint.
  const areaScene =
    terminalArea != null
      ? Math.max(2.5, Math.min(11, terminalArea / 2400))
      : 3;

  const terminalL = Math.sqrt(areaScene * 2.6);
  const terminalD = areaScene / terminalL;

  return (
    <group
      rotation={[
        0,
        -((heading - 90) * Math.PI) / 180,
        0,
      ]}
    >
      <Ground />

      <mesh position={[0, -1.91, 0]}>
        <boxGeometry
          args={[stripSceneL, 0.045, stripSceneW]}
        />
        <meshStandardMaterial
          color="#405540"
          roughness={1}
        />
      </mesh>

      <Runway
        lengthM={rL}
        widthM={rW}
        sceneLength={sceneL}
      />

      {secondaryL != null &&
        secondaryW != null &&
        secondaryBearing != null && (
          <group
            rotation={[
              0,
              -(
                (secondaryBearing - heading) *
                Math.PI
              ) / 180,
              0,
            ]}
          >
            <Runway
              lengthM={secondaryL}
              widthM={secondaryW}
              sceneLength={
                sceneL * (secondaryL / rL)
              }
              y={-1.79}
            />
          </group>
        )}

      <mesh
        position={[
          2.0,
          -1.78,
          stripSceneW * 0.9,
        ]}
      >
        <boxGeometry
          args={[
            apronL != null
              ? Math.max(2.2, apronL * scale)
              : 5.2,
            0.08,
            apronW != null
              ? Math.max(1.0, apronW * scale)
              : 1.4,
          ]}
        />
        <meshStandardMaterial color="#737b80" />
      </mesh>

      {taxiL != null && taxiW != null && (
        <mesh
          position={[5.0, -1.76, 1.25]}
          rotation={[0, 0.42, 0]}
        >
          <boxGeometry
            args={[
              Math.max(1.2, taxiL * scale),
              0.07,
              Math.max(0.15, taxiW * scale),
            ]}
          />
          <meshStandardMaterial color="#555e63" />
        </mesh>
      )}

      {isoL != null && isoW != null && (
        <mesh position={[8.0, -1.74, 2.4]}>
          <boxGeometry
            args={[
              Math.max(0.8, isoL * scale),
              0.08,
              Math.max(0.6, isoW * scale),
            ]}
          />
          <meshStandardMaterial color="#747c80" />
        </mesh>
      )}

      <mesh
        position={[
          0.3,
          -1.05,
          stripSceneW * 1.45 + 1.4,
        ]}
        castShadow
      >
        <boxGeometry
          args={[
            terminalL,
            1.4,
            terminalD,
          ]}
        />
        <meshStandardMaterial
          color="#7f969f"
          roughness={0.72}
        />
      </mesh>

      <mesh
        position={[
          terminalL * 0.35,
          0.0,
          stripSceneW * 1.45 + 2.4,
        ]}
      >
        <cylinderGeometry
          args={[0.25, 0.45, 3.2, 12]}
        />
        <meshStandardMaterial color="#8499a2" />
      </mesh>

      {showDimensions && (
        <>
          <Badge position={[0, 1.2, -1.7]}>
            RWY {txt(d, "runway_designation")}{" "}
            {rL.toLocaleString()} m × {rW} m
          </Badge>

          {sL != null && sW != null && (
            <Badge position={[-6.5, 0.2, -2.8]}>
              Strip {sL.toLocaleString()} m ×{" "}
              {sW} m
            </Badge>
          )}

          <Badge position={[6.3, 0.3, -2.7]}>
            Axis {heading.toFixed(2)}°
          </Badge>

          {terminalArea != null && (
            <Badge
              position={[
                0.3,
                1.5,
                stripSceneW * 1.45 + 1.4,
              ]}
              gold
            >
              Terminal{" "}
              {terminalArea.toLocaleString()} m² ·
              area-scaled massing
            </Badge>
          )}

          {landArea != null && (
            <Badge position={[-6.0, 3.0, 3.5]}>
              Airport land{" "}
              {landArea.toLocaleString()} acres ·
              boundary not inferred
            </Badge>
          )}

          {secondaryL != null &&
            secondaryW != null && (
              <Badge position={[6.2, 2.8, 3.0]}>
                Secondary RWY{" "}
                {txt(
                  d,
                  "secondary_runway_designation",
                )}{" "}
                {secondaryL} m × {secondaryW} m
              </Badge>
            )}
        </>
      )}
    </group>
  );
}

function Envelope({
  lengthM,
  widthM,
  wallHeightM = 6,
}: {
  lengthM: number;
  widthM: number;
  wallHeightM?: number;
}) {
  const scale = 18 / Math.max(lengthM, widthM);
  const l = lengthM * scale;
  const w = widthM * scale;
  const h = Math.max(
    0.45,
    Math.min(1.3, wallHeightM * scale * 2.1),
  );

  return (
    <group position={[0, -1.6, 0]}>
      <mesh position={[0, 0, -w / 2]}>
        <boxGeometry args={[l, h, 0.16]} />
        <meshStandardMaterial color="#91846b" />
      </mesh>
      <mesh position={[0, 0, w / 2]}>
        <boxGeometry args={[l, h, 0.16]} />
        <meshStandardMaterial color="#91846b" />
      </mesh>
      <mesh position={[-l / 2, 0, 0]}>
        <boxGeometry args={[0.16, h, w]} />
        <meshStandardMaterial color="#91846b" />
      </mesh>
      <mesh position={[l / 2, 0, 0]}>
        <boxGeometry args={[0.16, h, w]} />
        <meshStandardMaterial color="#91846b" />
      </mesh>
    </group>
  );
}

function Tirumala({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const l = num(d, "main_platform_length_m") ?? 126.492;
  const w = num(d, "main_platform_width_m") ?? 80.1624;

  return (
    <group>
      <Ground hill />
      <Envelope lengthM={l} widthM={w} />

      <mesh position={[0, -1.0, 0]} castShadow>
        <boxGeometry args={[7.4, 1.2, 5.4]} />
        <meshStandardMaterial color="#9a8357" />
      </mesh>

      <TieredTower
        storeys={3}
        height={4.3}
        width={3.3}
        position={[0, -0.7, 0]}
        colour="#c79e45"
      />

      <TieredTower
        storeys={5}
        height={3.6}
        width={2.7}
        position={[0, -1.5, -5.5]}
        colour="#c9a773"
      />

      {showDimensions && (
        <>
          <Badge position={[0, 5.0, 0]} gold>
            Main platform {l.toFixed(1)} m ×{" "}
            {w.toFixed(1)} m
          </Badge>
          <Badge position={[5.4, 2.8, 0]} gold>
            Ananda Nilaya{" "}
            {num(
              d,
              "ananda_nilaya_total_height_m",
            )?.toFixed(2)}{" "}
            m
          </Badge>
          <Badge position={[-5.3, 2.8, 0]}>
            Complex{" "}
            {num(d, "complex_land_area_acres")} acres
          </Badge>
        </>
      )}
    </group>
  );
}

function Srikalahasti({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;

  return (
    <group>
      <Ground hill />
      <mesh position={[1.6, -1.0, 0]}>
        <boxGeometry args={[9, 1.6, 6]} />
        <meshStandardMaterial color="#99896a" />
      </mesh>
      <TieredTower
        storeys={7}
        height={7.4}
        width={4.2}
        position={[-5.2, -1.8, 0]}
        colour="#d0b178"
      />
      {showDimensions && (
        <>
          <Badge position={[-5.2, 6.3, 0]} gold>
            Main gopuram{" "}
            {num(d, "main_gopuram_height_m")} m /
            120 ft
          </Badge>
          <Badge position={[4.5, 3.0, 0]}>
            West-facing · Swarnamukhi context
          </Badge>
        </>
      )}
    </group>
  );
}

function KanakaDurga({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;

  return (
    <group>
      <Ground hill />
      <mesh position={[1.6, -0.9, 0]}>
        <boxGeometry args={[7.5, 1.9, 5.4]} />
        <meshStandardMaterial color="#b39a65" />
      </mesh>
      <TieredTower
        storeys={9}
        height={6.5}
        width={3.8}
        position={[-4.4, -1.75, -0.4]}
        colour="#d5b56e"
      />
      {showDimensions && (
        <>
          <Badge position={[-4.4, 5.4, 0]} gold>
            Rajagopuram{" "}
            {num(
              d,
              "rajagopuram_height_m",
            )?.toFixed(2)}{" "}
            m · 9 storeys
          </Badge>
          <Badge position={[4.0, 3.0, 0]}>
            Indrakeeladri hill · Dravidian
          </Badge>
        </>
      )}
    </group>
  );
}

function SrisailamTemple({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const l = num(d, "enclosure_length_m") ?? 201.168;
  const w = num(d, "enclosure_width_m") ?? 155.448;
  const wall = num(d, "wall_height_max_m") ?? 7.9248;

  return (
    <group>
      <Ground />
      <Envelope
        lengthM={l}
        widthM={w}
        wallHeightM={wall}
      />
      <mesh position={[0, -1.0, 0]}>
        <boxGeometry args={[6.6, 2.1, 5.2]} />
        <meshStandardMaterial color="#85807a" />
      </mesh>
      <TieredTower
        storeys={4}
        height={3.0}
        width={2.7}
        position={[0, -1.4, -4.8]}
        colour="#b49a75"
      />
      {showDimensions && (
        <>
          <Badge position={[0, 4.5, 0]} gold>
            Historical enclosure {l.toFixed(1)} m ×{" "}
            {w.toFixed(1)} m
          </Badge>
          <Badge position={[5.8, 2.4, 0]}>
            Historical walls{" "}
            {num(d, "wall_height_min_m")?.toFixed(1)}
            –{wall.toFixed(1)} m
          </Badge>
          <Badge position={[-5.8, 2.4, 0]}>
            Historical source · NOT current survey
          </Badge>
        </>
      )}
    </group>
  );
}

function DescribedTemple({
  twin,
  showDimensions,
}: Props) {
  const d = twin.twin.dimensions;
  const template = txt(d, "template");

  const isSimhachalam =
    template === "temple_simhachalam";
  const isAnnavaram =
    template === "temple_annavaram";
  const isDwaraka =
    template === "temple_dwaraka_tirumala";

  const storeys = isDwaraka
    ? 5
    : isAnnavaram
      ? 2
      : 5;

  return (
    <group>
      <Ground hill />

      <mesh position={[1.2, -1.0, 0]}>
        <boxGeometry args={[7.0, 2.0, 5.5]} />
        <meshStandardMaterial
          color={isSimhachalam ? "#505654" : "#b19a6d"}
        />
      </mesh>

      <TieredTower
        storeys={storeys}
        height={isDwaraka ? 5.2 : 4.3}
        width={3.2}
        position={[-4.0, -1.5, 0]}
        colour={
          isSimhachalam ? "#5d625f" : "#cfb079"
        }
      />

      {isSimhachalam &&
        Array.from({ length: 16 }, (_, i) => (
          <mesh
            key={i}
            position={[
              (i % 4 - 1.5) * 0.55,
              -1.2,
              -4.6 +
                Math.floor(i / 4) * 0.55,
            ]}
          >
            <cylinderGeometry
              args={[0.07, 0.08, 1.3, 8]}
            />
            <meshStandardMaterial color="#454b49" />
          </mesh>
        ))}

      {showDimensions && (
        <>
          <Badge position={[0, 5.0, 0]}>
            {isSimhachalam
              ? "Official form: square shrine · high tower · 16-pillared mandapam"
              : isAnnavaram
                ? "Official form: two-storey shrine · Ratnagiri hill"
                : "Official/historic form: five-storey main gopuram · hill temple"}
          </Badge>

          {isSimhachalam && (
            <Badge position={[5.4, 2.6, 0]}>
              Site elevation{" "}
              {num(d, "site_elevation_m_asl")} m ASL
            </Badge>
          )}

          {isAnnavaram && (
            <Badge position={[5.4, 2.6, 0]}>
              Deity approx.{" "}
              {num(d, "deity_height_m")} m
            </Badge>
          )}

          {isDwaraka && (
            <Badge position={[5.4, 2.6, 0]}>
              Temple site approx.{" "}
              {num(
                d,
                "temple_site_height_m",
              )?.toFixed(1)}{" "}
              m above base
            </Badge>
          )}

          <Badge position={[-5.3, 2.6, 0]}>
            Building envelope not published · scale illustrative
          </Badge>
        </>
      )}
    </group>
  );
}

export function RealAirportTempleModel(
  props: Props,
) {
  const d = props.twin.twin.dimensions;
  const type =
    props.twin.asset.asset_type.toLowerCase();
  const template = txt(d, "template");

  if (type === "airport") {
    return <AirportComplex {...props} />;
  }

  if (template === "temple_tirumala") {
    return <Tirumala {...props} />;
  }
  if (template === "temple_srikalahasti") {
    return <Srikalahasti {...props} />;
  }
  if (template === "temple_kanaka_durga") {
    return <KanakaDurga {...props} />;
  }
  if (template === "temple_srisailam") {
    return <SrisailamTemple {...props} />;
  }

  return <DescribedTemple {...props} />;
}
