import "@cesium/widgets/Source/widgets.css";

import {
  Cartesian2,
  Cartesian3,
  Color,
  HeadingPitchRange,
  HeadingPitchRoll,
  HeightReference,
  Ion,
  LabelGraphics,
  LabelStyle,
  Math as CesiumMath,
  ModelGraphics,
  OpenStreetMapImageryProvider,
  PointGraphics,
  Terrain,
  Transforms,
  VerticalOrigin,
  Viewer,
  createOsmBuildingsAsync,
} from "cesium";

import { useEffect, useRef } from "react";

import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

function numericDimension(
  twin: TwinResponse,
  key: string,
): number | undefined {
  const value =
    twin.twin.dimensions[key];

  return typeof value === "number"
    ? value
    : undefined;
}

export function CesiumTwinViewer({
  twin,
}: {
  twin: TwinResponse;
}) {
  const container =
    useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) {
      return;
    }

    let viewer: Viewer | undefined;
    let cancelled = false;

    async function initialise() {
      const token =
        import.meta.env
          .VITE_CESIUM_ION_TOKEN
          ?.trim();

      if (token) {
        Ion.defaultAccessToken = token;
      }

      viewer = new Viewer(
        container.current as HTMLDivElement,
        {
          animation: false,
          timeline: false,
          geocoder: false,
          homeButton: true,
          sceneModePicker: true,
          baseLayerPicker: false,
          navigationHelpButton: false,
          infoBox: false,
          selectionIndicator: true,

          ...(token
            ? {
                terrain:
                  Terrain.fromWorldTerrain(),
              }
            : {
                baseLayer: false,
              }),
        },
      );

      if (!token) {
        viewer.imageryLayers
          .addImageryProvider(
            new OpenStreetMapImageryProvider({
              url:
                "https://tile.openstreetmap.org/",
              credit:
                "© OpenStreetMap contributors",
            }),
          );
      } else {
        try {
          const buildings =
            await createOsmBuildingsAsync();

          if (
            !cancelled &&
            viewer &&
            !viewer.isDestroyed()
          ) {
            viewer.scene.primitives.add(
              buildings,
            );
          }
        } catch (error) {
          console.warn(
            "Cesium OSM Buildings could not be loaded",
            error,
          );
        }
      }

      if (
        cancelled ||
        !viewer ||
        viewer.isDestroyed()
      ) {
        return;
      }

      const [longitude, latitude] =
        twin.asset.geometry.coordinates;

      const elevation =
        twin.twin.elevation_m ?? 0;

      const position =
        Cartesian3.fromDegrees(
          longitude,
          latitude,
          elevation,
        );

      const colour =
        Color.fromCssColorString(
          riskColor(
            twin.ai.risk_level,
          ),
        );

      const orientation =
        twin.twin.heading_deg == null
          ? undefined
          : Transforms.headingPitchRollQuaternion(
              position,
              new HeadingPitchRoll(
                CesiumMath.toRadians(
                  twin.twin.heading_deg,
                ),
                0,
                0,
              ),
            );

      const assetEntity =
        viewer.entities.add({
          id:
            twin.asset.asset_code,

          name:
            twin.asset.name,

          position,

          orientation,

          point:
            twin.twin.uri
              ? undefined
              : new PointGraphics({
                  pixelSize: 28,
                  color: colour,
                  outlineColor:
                    Color.WHITE,
                  outlineWidth: 4,
                  disableDepthTestDistance:
                    Number.POSITIVE_INFINITY,
                  heightReference:
                    HeightReference.CLAMP_TO_GROUND,
                }),

          model:
            twin.twin.uri
              ? new ModelGraphics({
                  uri:
                    twin.twin.uri,
                  minimumPixelSize: 96,
                  maximumScale: 300,
                })
              : undefined,

          label:
            new LabelGraphics({
              text:
                `${twin.asset.name}\n` +
                `${twin.twin.fidelity_level} · ${twin.twin.model_source}\n` +
                `Risk ${twin.ai.risk_score?.toFixed(1) ?? "—"}% · ${twin.ai.risk_level ?? "UNKNOWN"}`,

              font:
                "14px sans-serif",

              fillColor:
                Color.WHITE,

              outlineColor:
                Color.BLACK,

              outlineWidth: 3,

              style:
                LabelStyle.FILL_AND_OUTLINE,

              verticalOrigin:
                VerticalOrigin.BOTTOM,

              pixelOffset:
                new Cartesian2(
                  0,
                  -24,
                ),

              showBackground:
                true,

              backgroundColor:
                Color.fromCssColorString(
                  "#071426",
                ).withAlpha(0.84),
            }),
        });

      const structureLength =
        numericDimension(
          twin,
          "length_m",
        ) ?? 800;

      const range =
        Math.max(
          800,
          Math.min(
            5200,
            structureLength * 1.35,
          ),
        );

      await viewer.flyTo(
        assetEntity,
        {
          duration: 1.6,

          offset:
            new HeadingPitchRange(
              CesiumMath.toRadians(
                25,
              ),
              CesiumMath.toRadians(
                -38,
              ),
              range,
            ),
        },
      );

      viewer.selectedEntity =
        assetEntity;
    }

    void initialise();

    return () => {
      cancelled = true;

      if (
        viewer &&
        !viewer.isDestroyed()
      ) {
        viewer.destroy();
      }
    };
  }, [twin]);

  return (
    <div className="geospatial-viewer-shell">
      <div
        className="cesium-viewer"
        ref={container}
      />

      <div className="geospatial-viewer-note">
        <strong>
          Real geographic position
        </strong>

        <span>
          Cesium terrain and OSM
          buildings are used when a
          Cesium ion token is configured.
          OpenStreetMap imagery is used
          as the fallback.
        </span>
      </div>
    </div>
  );
}

