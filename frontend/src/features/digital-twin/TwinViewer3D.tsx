import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

function Bridge({ colour }: { colour: string }) {
  return (
    <group>
      <mesh position={[0, 0.2, 0]} castShadow receiveShadow>
        <boxGeometry args={[8, 0.35, 2]} />
        <meshStandardMaterial color={colour} metalness={0.35} roughness={0.55} />
      </mesh>
      {[-3, -1, 1, 3].map((x) => (
        <mesh key={x} position={[x, -1, 0]} castShadow>
          <boxGeometry args={[0.38, 2.3, 1.45]} />
          <meshStandardMaterial color="#8e9cac" />
        </mesh>
      ))}
      {[-1, 1].map((z) => (
        <mesh key={z} position={[0, 0.65, z * 0.78]}>
          <boxGeometry args={[8.2, 0.08, 0.08]} />
          <meshStandardMaterial color="#d4e1ea" />
        </mesh>
      ))}
    </group>
  );
}

function Dam({ colour }: { colour: string }) {
  return (
    <group rotation={[0, -0.25, 0]}>
      <mesh position={[0, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[8, 3, 1.8]} />
        <meshStandardMaterial color={colour} roughness={0.8} />
      </mesh>
      {[-2.4, -0.8, 0.8, 2.4].map((x) => (
        <mesh key={x} position={[x, -0.1, 0.96]}>
          <boxGeometry args={[0.85, 2.2, 0.14]} />
          <meshStandardMaterial color="#152a3c" metalness={0.5} />
        </mesh>
      ))}
      <mesh position={[0, -1.25, 2.25]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[10, 4]} />
        <meshStandardMaterial color="#2e98c6" transparent opacity={0.72} />
      </mesh>
    </group>
  );
}

function GlbModel({ uri }: { uri: string }) {
  const { scene } = useGLTF(uri);
  return <primitive object={scene} scale={1} />;
}

export function TwinViewer3D({ twin }: { twin: TwinResponse }) {
  const colour = riskColor(twin.ai.risk_level);
  const assetType = twin.asset.asset_type;
  return (
    <div className="twin-canvas">
      <Canvas camera={{ position: [9, 6, 9], fov: 42 }} shadows>
        <color attach="background" args={["#07111c"]} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[6, 10, 5]} intensity={2.2} castShadow />
        <gridHelper args={[24, 24, "#1c516b", "#122a3a"]} position={[0, -2.18, 0]} />
        <Suspense fallback={null}>
          {twin.twin.uri ? (
            <GlbModel uri={twin.twin.uri} />
          ) : assetType === "bridge" ? (
            <Bridge colour={colour} />
          ) : (
            <Dam colour={colour} />
          )}
        </Suspense>
        <OrbitControls makeDefault minDistance={5} maxDistance={25} />
      </Canvas>
      <div className="viewer-label">
        <strong>{twin.twin.fidelity_level}</strong>
        <span>{twin.twin.is_asset_specific ? "Asset-specific model" : "Illustrative procedural model"}</span>
      </div>
    </div>
  );
}

