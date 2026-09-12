// @ts-nocheck
/**
 * Digital Twin Viewer Component
 *
 * Renders 3D infrastructure assets using Three.js and React Three Fiber
 * Loads GLB/GLTF models for visualization
 */
import { Suspense, useEffect, useState, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { AlertCircle, Loader } from "lucide-react";
import { createProceduralModel } from "./ProceduralModels";
import type { DigitalTwinViewerProps } from "../../types";
/**
 * Model component that loads and displays the GLB/GLTF file or procedural model
 */
function ModelDisplay({
  modelUrl,
  assetType,
  onLoaded,
  onError,
}: {
  modelUrl?: string | null;
  assetType?: string | null;
  onLoaded?: () => void;
  onError?: (error: Error) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const [model, setModel] = useState<THREE.Group | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modelSource, setModelSource] = useState<"gltf" | "procedural" | null>(null);

  useEffect(() => {
    // Try to load GLTF model if URL provided
    if (modelUrl) {
      const loader = new GLTFLoader();
      const abortController = new AbortController();

      loader.load(
        modelUrl,
        (gltf) => {
          if (!abortController.signal.aborted) {
            const clonedScene = gltf.scene.clone();
            setModel(clonedScene);
            setModelSource("gltf");
            onLoaded?.();

            console.log("GLTF Model loaded:", modelUrl);
            console.log("Scenes:", gltf.scenes.length);
            console.log("Animations:", gltf.animations.length);
          }
        },
        (progress) => {
          console.log(
            `Loading GLTF model: ${Math.round((progress.loaded / progress.total) * 100)}%`
          );
        },
        (err) => {
          if (!abortController.signal.aborted) {
            const errorMsg = `Failed to load GLTF model: ${err.message || err}`;
            console.warn(errorMsg);
            // Fall back to procedural model
            if (assetType) {
              try {
                const proceduralModel = createProceduralModel(assetType);
                setModel(proceduralModel);
                setModelSource("procedural");
                onLoaded?.();
                console.log(`Fallback to procedural model for type: ${assetType}`);
              } catch (procErr) {
                setError(errorMsg);
                onError?.(new Error(errorMsg));
                console.error("Procedural model creation error:", procErr);
              }
            } else {
              setError(errorMsg);
              onError?.(new Error(errorMsg));
            }
          }
        }
      );

      return () => {
        abortController.abort();
      };
    } else if (assetType) {
      // No GLTF URL, create procedural model directly
      try {
        const proceduralModel = createProceduralModel(assetType);
        setModel(proceduralModel);
        setModelSource("procedural");
        onLoaded?.();
        console.log(`Created procedural model for type: ${assetType}`);
      } catch (err) {
        const errorMsg = `Failed to create procedural model: ${err}`;
        setError(errorMsg);
        onError?.(new Error(errorMsg));
        console.error("Procedural model error:", err);
      }
    }
  }, [modelUrl, assetType, onLoaded, onError]);

  useFrame(() => {
    if (groupRef.current && model) {
      groupRef.current.rotation.y += 0.001; // Gentle auto-rotation
    }
  });

  if (error) {
    return (
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color="red" wireframe />
      </mesh>
    );
  }

  if (!model) {
    return (
      <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="blue" wireframe />
      </mesh>
    );
  }

  return (
    <group ref={groupRef}>
      {model}
      {modelSource === "procedural" && (
        <group>
          <mesh position={[0, -1.5, 0]}>
            <boxGeometry args={[4, 0.1, 4]} />
            <meshStandardMaterial color="#333333" />
          </mesh>
        </group>
      )}
    </group>
  );
}

/**
 * Loading fallback component
 */
function LoadingFallback() {
  return (
    <mesh>
      <sphereGeometry args={[0.5, 16, 16]} />
      <meshStandardMaterial color="#ccc" wireframe />
    </mesh>
  );
}

/**
 * Scene setup component
 */
function SceneSetup() {
  const { scene } = useThree();

  useEffect(() => {
    // Set background
    scene.background = new THREE.Color(0x1a1a2e);
  }, [scene]);

  return null;
}

/**
 * Grid helper - draws a simple grid
 */
function GridHelper() {
  const gridRef = useRef<THREE.LineSegments>(null);
  const size = 10;
  const step = 0.5;
  const color = new THREE.Color(0x555555);

  useEffect(() => {
    const geometry = new THREE.BufferGeometry();
    const positions: number[] = [];

    for (let i = -size; i <= size; i += step) {
      // Horizontal lines
      positions.push(-size, 0, i, size, 0, i);
      // Vertical lines
      positions.push(i, 0, -size, i, 0, size);
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    return () => geometry.dispose();
  }, []);

  return (
    <lineSegments ref={gridRef} position={[0, -1.5, 0]}>
      <bufferGeometry />
      <lineBasicMaterial color={0x555555} />
    </lineSegments>
  );
}

/**
 * Camera controller - handles auto-rotation and zoom
 */
function CameraController() {
  const { camera } = useThree();
  const autoRotateAngle = useRef(0);

  useFrame(() => {
    // Auto-rotate around Y axis
    autoRotateAngle.current += 0.002;
    const radius = 3;
    camera.position.x = Math.cos(autoRotateAngle.current) * radius;
    camera.position.z = Math.sin(autoRotateAngle.current) * radius;
    camera.lookAt(0, 0, 0);
  });

  return null;
}

/**
 * Main Digital Twin Viewer Component
 *
 * Props:
 * - assetId: Asset identifier (for context)
 * - modelUrl: URL to GLB/GLTF model file (optional)
 * - asset: Asset information (optional, for display)
 * - assetType: Infrastructure asset type for procedural model generation
 * - onError: Callback for errors
 * - onLoaded: Callback when model loaded
 */
export function DigitalTwinViewer({
  assetId,
  modelUrl,
  asset,
  onError,
  onLoaded,
}: DigitalTwinViewerProps) {
  const [modelLoaded, setModelLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const handleModelError = (error: Error) => {
    setLoadError(error.message);
    onError?.(error);
  };

  const handleModelLoaded = () => {
    setModelLoaded(true);
    onLoaded?.();
  };

  // Get asset type from asset object
  const assetType = asset?.type || (asset as any)?.asset_type;

  // If no model URL and no asset type, show placeholder
  if (!modelUrl && !assetType) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-b from-slate-900 to-slate-800 text-white">
<AlertCircle className="w-16 h-16 mb-4 text-yellow-500" />
        <h3 className="text-xl font-semibold mb-2">3D Model Not Available</h3>
        <p className="text-sm text-gray-400">
          No 3D model is available for asset {assetId}
        </p>
        {asset && (
          <p className="text-xs text-gray-500 mt-2">{asset.name}</p>
        )}
      </div>
    );
  }

  // If error occurred, show error state
  if (loadError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-b from-red-900 to-red-800 text-white">
        <AlertCircle className="w-16 h-16 mb-4 text-red-300" />
        <h3 className="text-xl font-semibold mb-2">Failed to Load Model</h3>
        <p className="text-sm text-gray-100 text-center max-w-xs">
          {loadError}
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }} onCreated={(state) => {
        state.scene.background = new THREE.Color(0x1a1a2e);
      }}>
        <Suspense fallback={<LoadingFallback />}>
          <ModelDisplay
            modelUrl={modelUrl}
            assetType={assetType}
            onLoaded={handleModelLoaded}
            onError={handleModelError}
          />
        </Suspense>

        {/* Lighting */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={1} />
        <directionalLight position={[-5, -5, 5]} intensity={0.5} />

        {/* Simple grid using lines */}
        <GridHelper />

        {/* Controls replacement - manual rotation */}
        <CameraController />
      </Canvas>

      {/* Loading indicator */}
      {!modelLoaded && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 pointer-events-none">
          <div className="flex items-center gap-2 bg-black/60 px-4 py-2 rounded">
            <Loader className="w-4 h-4 animate-spin text-white" />
            <span className="text-white text-sm">Loading 3D model...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default DigitalTwinViewer;



