import "cesium/Build/Cesium/Widgets/widgets.css";
import {
  Cartesian3,
  Color,
  Ion,
  ModelGraphics,
  PointGraphics,
  Viewer,
} from "cesium";
import { useEffect, useRef } from "react";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

export function CesiumTwinViewer({ twin }: { twin: TwinResponse }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const token = import.meta.env.VITE_CESIUM_ION_TOKEN;
    if (token) Ion.defaultAccessToken = token;
    const viewer = new Viewer(container.current, {
      animation: false,
      timeline: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      baseLayerPicker: false,
      navigationHelpButton: false,
      baseLayer: false,
      infoBox: false,
      selectionIndicator: false,
    });

    const [longitude, latitude] = twin.asset.geometry.coordinates;
    const position = Cartesian3.fromDegrees(longitude, latitude, twin.twin.elevation_m ?? 0);
    const colour = Color.fromCssColorString(riskColor(twin.ai.risk_level));
    viewer.entities.add({
      id: twin.asset.asset_code,
      name: twin.asset.name,
      position,
      point: twin.twin.uri
        ? undefined
        : new PointGraphics({ pixelSize: 18, color: colour, outlineColor: Color.WHITE, outlineWidth: 2 }),
      model: twin.twin.uri
        ? new ModelGraphics({ uri: twin.twin.uri, minimumPixelSize: 96, color: colour })
        : undefined,
    });
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(longitude, latitude, 3800),
      duration: 1.5,
    });

    return () => viewer.destroy();
  }, [twin]);

  return <div className="cesium-viewer" ref={container} />;
}

