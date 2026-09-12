import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import type { InfrastructureAsset } from "../../types";

const colorFor: Record<InfrastructureAsset["health"], string> = {
  healthy: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-danger)",
};

/**
 * Leaflet map. Client-only — always render behind a hydration guard.
 * Data arrives as plain assets today and as PostGIS GeoJSON later.
 */
export default function GISMap({
  assets,
  selectedId,
  onSelect,
}: {
  assets: InfrastructureAsset[];
  selectedId?: string | undefined;
  onSelect?: (asset: InfrastructureAsset) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Record<string, L.CircleMarker>>({});

  const center = useMemo<[number, number]>(() => [16.3, 80.7], []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { center, zoom: 7, zoomControl: true, attributionControl: true });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      maxZoom: 19,
    }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = {};
    };
  }, [center]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    const validAssets = assets.filter((a) => Number.isFinite(a.lat) && Number.isFinite(a.lng));
    if (validAssets.length === 0) return;

    const bounds = L.latLngBounds([]);
    validAssets.forEach((a) => {
      const marker = L.circleMarker([a.lat, a.lng], {
        radius: a.id === selectedId ? 11 : 8,
        color: colorFor[a.health],
        weight: 3,
        fillColor: colorFor[a.health],
        fillOpacity: 0.35,
      })
        .addTo(map)
        .bindTooltip(`${a.id} · ${a.name}`, { direction: "top" });
      marker.on("click", () => onSelect?.(a));
      markersRef.current[a.id] = marker;
      bounds.extend([a.lat, a.lng]);
    });

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 12 });
    }
  }, [assets, selectedId, onSelect]);

  return <div ref={containerRef} className="size-full" role="application" aria-label="Infrastructure map" />;
}
