import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { GISAsset } from "../../pages/gis/GISPage";

function markerColor(asset: GISAsset) {
  if (asset.riskLevel) {
    const level = asset.riskLevel.toLowerCase();
    if (level.includes("high") || level.includes("critical")) return "#ef4444";
    if (level.includes("medium") || level.includes("moderate")) return "#f59e0b";
    if (level.includes("low")) return "#10b981";
  }

  if (asset.riskScore === null) return "#64748b";
  if (asset.riskScore >= 70) return "#ef4444";
  if (asset.riskScore >= 40) return "#f59e0b";
  return "#10b981";
}

export default function GISMap({
  assets,
  selectedId,
  onSelect,
}: {
  assets: GISAsset[];
  selectedId?: string;
  onSelect?: (asset: GISAsset) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);

  const apCenter = useMemo<[number, number]>(() => [15.9129, 79.74], []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: apCenter,
      zoom: 7,
      minZoom: 5,
      maxZoom: 19,
      zoomControl: true,
      attributionControl: true,
      preferCanvas: true,
    });

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
      crossOrigin: true,
    }).addTo(map);

    markerLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    window.setTimeout(() => map.invalidateSize(), 100);

    return () => {
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
    };
  }, [apCenter]);

  useEffect(() => {
    const map = mapRef.current;
    const layer = markerLayerRef.current;

    if (!map || !layer) return;

    layer.clearLayers();

    const bounds = L.latLngBounds([]);

    for (const asset of assets) {
      if (!Number.isFinite(asset.lat) || !Number.isFinite(asset.lng)) continue;

      const selected = asset.id === selectedId;
      const color = markerColor(asset);

      const marker = L.circleMarker([asset.lat, asset.lng], {
        renderer: L.canvas(),
        radius: selected ? 9 : 6,
        color: selected ? "#0f172a" : color,
        weight: selected ? 3 : 2,
        fillColor: color,
        fillOpacity: selected ? 0.95 : 0.7,
      });

      marker.bindTooltip(
        `<strong>${asset.name}</strong><br/>${asset.assetCode}<br/>${asset.assetType}`,
        { direction: "top", opacity: 0.95 },
      );

      marker.on("click", () => onSelect?.(asset));
      marker.addTo(layer);
      bounds.extend([asset.lat, asset.lng]);
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [32, 32],
        maxZoom: assets.length === 1 ? 15 : 10,
      });
    } else {
      map.setView(apCenter, 7);
    }

    window.setTimeout(() => map.invalidateSize(), 50);
  }, [apCenter, assets, onSelect, selectedId]);

  return (
    <div
      ref={containerRef}
      className="size-full"
      role="application"
      aria-label="Andhra Pradesh infrastructure GIS map"
    />
  );
}
