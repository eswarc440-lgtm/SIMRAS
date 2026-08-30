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

export function TwinViewer3D({ twin }: { twin: TwinResponse }) {
  const [showDimensions, setShowDimensions] = useState(true);
  const backed = sourceBacked(twin);
  const hasGlb = Boolean(twin.twin.uri);

  return (
    <div className="twin-canvas">
      <Canvas
        key={`${twin.asset.asset_code}-${twin.twin.version}`}
        camera={{ position: [12, 7, 15], fov: 42 }}
        shadows
      >
        <color attach="background" args={["#07111c"]} />
        <ambientLight intensity={0.8} />
        <directionalLight
          position={[8, 12, 7]}
          intensity={2.4}
          castShadow
        />

        <gridHelper
          args={[30, 30, "#1c516b", "#122a3a"]}
          position={[0, -1.95, 0]}
        />

        <Suspense fallback={null}>
          {twin.twin.uri ? (
            <GlbModel uri={twin.twin.uri} />
          ) : (
            <AssetSpecificModel
              twin={twin}
              colour={riskColor(twin.ai.risk_level)}
              showDimensions={showDimensions}
            />
          )}
        </Suspense>

        <OrbitControls
          makeDefault
          minDistance={4}
          maxDistance={45}
          enableDamping
        />
      </Canvas>

      <div className="viewer-label">
        <strong>{twin.twin.fidelity_level}</strong>

        <span>
          {hasGlb
            ? "Asset-specific 3D model · check source and accuracy below"
            : backed
              ? "Source-backed dimensional twin · not survey/BIM/LiDAR geometry"
              : "Illustrative type model · geometry is not measured or verified"}
        </span>
      </div>

      {backed && !hasGlb && (
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
