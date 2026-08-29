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