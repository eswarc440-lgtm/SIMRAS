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

export function TwinViewer3D({ twin }: { twin: TwinResponse }) {
  const [showDimensions, setShowDimensions] = useState(true);
  const backed = sourceBacked(twin);

  return (
    <div className="twin-canvas">
      <Canvas
        key={`${twin.asset.asset_code}-${twin.twin.version}`}
        camera={{ position: [13, 8, 17], fov: 42 }}
        shadows
      >
        <color attach="background" args={["#07111c"]} />
        <ambientLight intensity={0.82} />

        <directionalLight
          position={[10, 14, 8]}
          intensity={2.35}
          castShadow
        />

        <gridHelper
          args={[34, 34, "#1c516b", "#122a3a"]}
          position={[0, -2.01, 0]}
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
          enableDamping
          minDistance={4}
          maxDistance={52}
        />
      </Canvas>

      <div className="viewer-label">
        <strong>{twin.twin.fidelity_level}</strong>

        <span>
          {twin.twin.uri
            ? "Measured/published model Â· check provenance"
            : backed
              ? "Source-driven asset-specific parametric twin Â· dimensions shown from linked records"
              : "Illustrative type twin Â· dimensions are not claimed as measured"}
        </span>
      </div>

      {backed && (
        <button
          className="dimension-toggle"
          type="button"
          aria-pressed={showDimensions}
          onClick={() => setShowDimensions((value) => !value)}
        >
          {showDimensions ? "Hide dimensions" : "Show dimensions"}
        </button>
      )}
    </div>
  );
}