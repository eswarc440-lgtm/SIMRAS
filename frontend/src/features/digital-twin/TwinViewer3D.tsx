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