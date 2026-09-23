import L from "leaflet";
import { useEffect } from "react";
import {
  GeoJSON,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import type { GeoJsonObject } from "geojson";
import type {
  AssetSummary,
  MapFeatureCollection,
  MapFeatureProperties,
} from "../types/twin";
import { riskColor } from "../utils";

interface GISMapProps {
  assets: AssetSummary[];
  mapFeatures: MapFeatureCollection;
  selected?: AssetSummary;
  onSelect: (asset: AssetSummary) => void;
}

function MapFocus({ selected }: { selected?: AssetSummary }) {
  const map = useMap();

  useEffect(() => {
    if (!selected) return;

    const [longitude, latitude] = selected.geometry.coordinates;
    map.flyTo(
      [latitude, longitude],
      Math.max(map.getZoom(), 11),
      { duration: 1.1 },
    );
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

function statewideColour(featureType?: string) {
  switch (featureType) {
    case "airport":
      return "#38bdf8";
    case "barrage":
      return "#a78bfa";
    case "temple":
      return "#f59e0b";
    case "bridge":
      return "#22c55e";
    case "road":
      return "#94a3b8";
    default:
      return "#2dd4bf";
  }
}

function bindFeaturePopup(
  properties: MapFeatureProperties,
  layer: L.Layer,
) {
  const container = document.createElement("div");
  const title = document.createElement("strong");
  const details = document.createElement("div");
  const source = document.createElement("small");

  title.textContent = properties.name || "Unnamed map feature";
  details.textContent = [
    properties.feature_type,
    properties.subtype,
    properties.identity_status,
  ]
    .filter(Boolean)
    .join(" · ");
  source.textContent = `Source: ${properties.source_name}`;

  container.append(title, document.createElement("br"));
  container.append(details, source);
  layer.bindPopup(container);
}

export function GISMap({
  assets,
  mapFeatures,
  selected,
  onSelect,
}: GISMapProps) {
  return (
    <MapContainer
      className="gis-map"
      center={[15.9, 80.2]}
      zoom={7}
      minZoom={6}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {mapFeatures.features.length > 0 && (
        <GeoJSON
          key={`${mapFeatures.total}-${mapFeatures.features[0]?.properties.feature_type ?? "all"}`}
          data={mapFeatures as unknown as GeoJsonObject}
          style={(feature) => ({
            color: statewideColour(
              (feature?.properties as MapFeatureProperties | undefined)
                ?.feature_type,
            ),
            weight: 3,
            opacity: 0.85,
            fillOpacity: 0.25,
          })}
          pointToLayer={(feature, latlng) =>
            L.circleMarker(latlng, {
              radius: 7,
              color: "#071426",
              weight: 2,
              fillColor: statewideColour(
                (feature.properties as MapFeatureProperties).feature_type,
              ),
              fillOpacity: 0.95,
            })
          }
          onEachFeature={(feature, layer) =>
            bindFeaturePopup(
              feature.properties as MapFeatureProperties,
              layer,
            )
          }
        />
      )}

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
              <div style={{ minWidth: 200, padding: "4px 2px", fontFamily: "Inter, sans-serif" }}>
                <strong style={{ fontSize: 14, color: "#0f172a", display: "block", marginBottom: 2 }}>{asset.name}</strong>
                <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
                  <code>{asset.asset_code}</code> · <span style={{ textTransform: "capitalize" }}>{asset.asset_type}</span>
                </div>
                <div style={{ fontSize: 12, lineHeight: 1.5, marginBottom: 8, borderTop: "1px solid #e2e8f0", paddingTop: 4 }}>
                  <div><strong>District:</strong> {asset.district || "Andhra Pradesh"}</div>
                  <div><strong>Health:</strong> {asset.health_score !== null && asset.health_score !== undefined ? `${asset.health_score}/100` : "NOT VERIFIED"}</div>
                  <div><strong>Risk:</strong> <span style={{ color: riskColor(asset.risk_level), fontWeight: 700 }}>{asset.risk_level || "UNKNOWN"}</span> {asset.risk_score !== null && asset.risk_score !== undefined ? `(${asset.risk_score}/100)` : ""}</div>
                </div>
                <button
                  type="button"
                  style={{
                    width: "100%",
                    background: "#0284c7",
                    color: "#fff",
                    border: "none",
                    borderRadius: 4,
                    padding: "6px 10px",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                  onClick={() => onSelect(asset)}
                >
                  View Details & Twin →
                </button>
              </div>
            </Popup>
          </Marker>
        );
      })}

      <MapFocus selected={selected} />
    </MapContainer>
  );
}