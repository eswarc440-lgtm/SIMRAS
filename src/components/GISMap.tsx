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
import { normalizeCoordinates } from "../lib/coordinates";
import { riskColor } from "../utils";

interface GISMapProps {
  assets: AssetSummary[];
  mapFeatures: MapFeatureCollection;
  selected?: AssetSummary;
  onSelect: (asset: AssetSummary) => void;
  onOpenDetails?: (asset: AssetSummary) => void;
}

function MapFocus({ selected }: { selected?: AssetSummary }) {
  const map = useMap();

  useEffect(() => {
    if (!selected) return;

    const location = normalizeCoordinates(selected);
    if (!location) return;
    map.flyTo(
      location.leaflet,
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
  onOpenDetails,
}: GISMapProps) {
  return (
    <MapContainer
      className="gis-map h-full w-full"
      style={{ height: "100%", width: "100%" }}
      center={[15.9, 80.2]}
      zoom={7}
      minZoom={6}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {(mapFeatures?.features?.length ?? 0) > 0 && (
        <GeoJSON
          key={`${mapFeatures?.total ?? 0}-${mapFeatures?.features?.[0]?.properties?.feature_type ?? "all"}`}
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
              color: "#0C4775",
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

      {(assets ?? []).map((asset) => {
        const location = normalizeCoordinates(asset);
        if (!location) return null;
        const riskVal = asset.risk_score ?? (asset.risk_level === "CRITICAL" ? 85 : asset.risk_level === "HIGH" ? 65 : asset.risk_level === "MEDIUM" ? 38 : 15);
        const healthVal = asset.health_score ?? Math.max(0, 100 - riskVal);

        return (
          <Marker
            icon={markerIcon(asset)}
            key={asset.asset_code}
            position={location.leaflet}
            eventHandlers={{ click: () => onSelect(asset) }}
          >
            <Popup className="gov-map-popup">
              <div className="p-1 min-w-[200px] text-slate-800 font-sans">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-mono font-bold text-[#0875BE] bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                    {asset.asset_code}
                  </span>
                  <span className="text-[10px] uppercase font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                    {asset.asset_type || asset.category || asset.type}
                  </span>
                </div>
                <h4 className="font-bold text-sm text-[#0C4775] leading-snug">
                  {asset.name}
                </h4>
                <p className="text-[11px] text-slate-500 mb-2">
                  District: <strong className="text-slate-700">{asset.district || "Andhra Pradesh"}</strong>
                </p>

                <div className="grid grid-cols-2 gap-2 p-1.5 bg-[#F5F8FB] rounded border border-[#D9E3EC] mb-2 text-center">
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 block">Health</span>
                    <span className="text-xs font-bold text-[#0875BE]">{healthVal.toFixed(0)}/100</span>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-400 block">Risk</span>
                    <span className={`text-xs font-bold ${riskVal >= 60 ? "text-[#D94343]" : riskVal >= 30 ? "text-[#F2A623]" : "text-[#20A36A]"}`}>
                      {riskVal.toFixed(0)}/100
                    </span>
                  </div>
                </div>

                {onOpenDetails && (
                  <button
                    type="button"
                    onClick={() => onOpenDetails(asset)}
                    className="w-full text-center text-xs font-bold text-white bg-[#0875BE] hover:bg-[#0C4775] py-1.5 px-2 rounded transition shadow-sm"
                  >
                    View Details →
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        );
      })}

      <MapFocus selected={selected} />
    </MapContainer>
  );
}


