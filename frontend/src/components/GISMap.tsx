import L from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { AssetSummary } from "../types/twin";
import { riskColor } from "../utils";

interface GISMapProps {
  assets: AssetSummary[];
  selected?: AssetSummary;
  onSelect: (asset: AssetSummary) => void;
}

function MapFocus({ selected }: { selected?: AssetSummary }) {
  const map = useMap();
  useEffect(() => {
    if (!selected) return;
    const [longitude, latitude] = selected.geometry.coordinates;
    map.flyTo([latitude, longitude], Math.max(map.getZoom(), 11), { duration: 1.1 });
  }, [map, selected]);
  return null;
}

function markerIcon(asset: AssetSummary) {
  const colour = riskColor(asset.risk_level);
  return L.divIcon({
    className: "asset-marker-shell",
    html: `<span class="asset-marker" style="--marker:${colour}"><i></i></span>`,
    iconSize: [26, 34],
    iconAnchor: [13, 30],
  });
}

export function GISMap({ assets, selected, onSelect }: GISMapProps) {
  return (
    <MapContainer className="gis-map" center={[15.9, 80.2]} zoom={7} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {assets.map((asset) => {
        const [longitude, latitude] = asset.geometry.coordinates;
        return (
          <Marker
            icon={markerIcon(asset)}
            key={asset.asset_code}
            position={[latitude, longitude]}
            eventHandlers={{ click: () => onSelect(asset) }}
          >
            <Popup>
              <strong>{asset.name}</strong><br />
              {asset.asset_type} · {asset.risk_level ?? "Risk unavailable"}
            </Popup>
          </Marker>
        );
      })}
      <MapFocus selected={selected} />
    </MapContainer>
  );
}

