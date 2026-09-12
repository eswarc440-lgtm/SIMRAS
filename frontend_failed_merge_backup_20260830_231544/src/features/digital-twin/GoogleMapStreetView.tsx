import "maplibre-gl/dist/maplibre-gl.css";

import * as maplibregl from "maplibre-gl";
import type { Map as MapLibreMap } from "maplibre-gl";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import type { TwinResponse } from "../../types/twin";

export function GoogleMapStreetView({
  twin,
}: {
  twin: TwinResponse;
}) {
  const container =
    useRef<HTMLDivElement>(null);

  const mapRef =
    useRef<MapLibreMap | null>(null);

  const [status, setStatus] =
    useState(
      "Loading OpenStreetMap infrastructure view...",
    );

  useEffect(() => {
    if (!container.current) {
      return;
    }

    const [
      longitude,
      latitude,
    ] =
      twin.asset.geometry.coordinates;

    if (
      !Number.isFinite(longitude) ||
      !Number.isFinite(latitude)
    ) {
      setStatus(
        "Asset coordinates are unavailable.",
      );
      return;
    }

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map =
      new maplibregl.Map({
        container:
          container.current,

        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: [
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
              ],
              tileSize: 256,
              attribution:
                "? OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm-base",
              type: "raster",
              source: "osm",
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        } as any,

        center: [
          longitude,
          latitude,
        ],

        zoom: 17,

        pitch: 0,

        bearing:
          typeof twin.twin
            .heading_deg === "number"
            ? twin.twin.heading_deg
            : 0,

        attributionControl: {},
      });

    mapRef.current = map;

    map.addControl(
      new maplibregl.NavigationControl({
        visualizePitch: true,
      }),
      "top-right",
    );

    map.addControl(
      new maplibregl.FullscreenControl(),
      "top-right",
    );

    map.addControl(
      new maplibregl.ScaleControl({
        maxWidth: 160,
        unit: "metric",
      }),
      "bottom-right",
    );

    const popup =
      new maplibregl.Popup({
        offset: 28,
      }).setHTML(`
        <div style="
          color:#111827;
          min-width:220px;
          font-family:Arial,sans-serif;
        ">
          <strong>
            ${twin.asset.name}
          </strong>

          <div style="
            margin-top:6px;
            font-size:12px;
          ">
            ${twin.asset.asset_code}
          </div>

          <div style="
            margin-top:4px;
            font-size:12px;
          ">
            ${latitude.toFixed(6)},
            ${longitude.toFixed(6)}
          </div>

          <div style="
            margin-top:4px;
            font-size:12px;
          ">
            Identity:
            ${twin.asset.identity_status}
          </div>
        </div>
      `);

    const marker =
      new maplibregl.Marker({
        color: "#22d3ee",
        scale: 1.2,
      })
        .setLngLat([
          longitude,
          latitude,
        ])
        .setPopup(popup)
        .addTo(map);

    map.on(
      "load",
      () => {
        setStatus(
          "OpenStreetMap 2D view active â€” click the marker for asset details.",
        );

        marker.togglePopup();

        map.easeTo({
          center: [
            longitude,
            latitude,
          ],
          zoom: 17.5,
          duration: 1200,
        });
      },
    );

    map.on(
      "error",
      (event: any) => {
        console.warn(
          "SIMRAS MapLibre:",
          event.error,
        );
      },
    );

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [twin]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        background: "#071426",
        overflow: "hidden",
      }}
    >
      <div
        ref={container}
        style={{
          width: "100%",
          height: "680px",
        }}
      />

      <div
        style={{
          position: "absolute",
          left: "18px",
          bottom: "18px",
          zIndex: 5,
          maxWidth: "500px",
          padding: "12px 16px",
          borderRadius: "10px",
          background:
            "rgba(4,18,28,.92)",
          color: "white",
          pointerEvents: "none",
        }}
      >
        <strong>
          Real-world 2D infrastructure map
        </strong>

        <div
          style={{
            marginTop: "5px",
            fontSize: "13px",
            opacity: 0.82,
          }}
        >
          {status}
        </div>

        <div
          style={{
            marginTop: "5px",
            fontSize: "12px",
            opacity: 0.62,
          }}
        >
          {twin.asset.name}
          {" Â· "}
          OpenStreetMap / OpenFreeMap
        </div>
      </div>
    </div>
  );
}

