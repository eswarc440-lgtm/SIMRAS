import React, { useState, useMemo } from "react";
import { useSelectedAsset } from "../../context/AssetContext";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import {
  Box,
  Compass,
  FileText,
  Filter,
  Layers,
  MapPin,
  Navigation,
  RotateCcw,
  Search,
  Sparkles,
} from "lucide-react";
import type { AssetSummary } from "../../types/twin";
import { riskColor } from "../../utils";

interface GISCommandModuleProps {
  onNavigate: (module: "ENGINEERING" | "TWIN" | "AI" | "REPORTS") => void;
}

function MapController({
  selected,
  userLocation,
  showDirections,
}: {
  selected?: AssetSummary;
  userLocation?: [number, number];
  showDirections: boolean;
}) {
  const map = useMap();

  React.useEffect(() => {
    if (showDirections && selected && userLocation) {
      const [lng, lat] = selected.geometry.coordinates;
      const bounds = L.latLngBounds([userLocation, [lat, lng]]);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
    } else if (selected) {
      const [lng, lat] = selected.geometry.coordinates;
      map.flyTo([lat, lng], 12, { duration: 1.2 });
    }
  }, [map, selected, userLocation, showDirections]);

  return null;
}

function createMarkerIcon(asset: AssetSummary, isSelected: boolean) {
  const color = riskColor(asset.risk_level);
  return L.divIcon({
    className: "custom-div-icon",
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: ${isSelected ? "34px" : "26px"};
        height: ${isSelected ? "34px" : "26px"};
        background: ${isSelected ? "#ffffff" : color};
        border: 3px solid ${isSelected ? color : "#ffffff"};
        border-radius: 50%;
        box-shadow: 0 0 ${isSelected ? "14px" : "6px"} ${color};
        transform: translate(-50%, -50%);
        transition: all 0.2s ease;
      ">
        <div style="
          width: 8px;
          height: 8px;
          background: ${isSelected ? color : "#ffffff"};
          border-radius: 50%;
        "></div>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function createUserIcon() {
  return L.divIcon({
    className: "user-loc-icon",
    html: `
      <div style="
        width: 22px;
        height: 22px;
        background: #38bdf8;
        border: 3px solid #ffffff;
        border-radius: 50%;
        box-shadow: 0 0 12px #38bdf8;
        transform: translate(-50%, -50%);
      "></div>
    `,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

// Haversine distance in km
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371; // Earth radius km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

export function GISCommandModule({ onNavigate }: GISCommandModuleProps) {
  const { assets, selected, selectAsset } = useSelectedAsset();

  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState("ALL");
  const [selectedDistrict, setSelectedDistrict] = useState("ALL");
  const [selectedRisk, setSelectedRisk] = useState("ALL");
  const [userLocation, setUserLocation] = useState<[number, number] | undefined>(undefined);
  const [showDirections, setShowDirections] = useState(false);

  // Extract unique districts
  const districts = useMemo(() => {
    const set = new Set<string>();
    assets.forEach((a) => {
      if (a.district) set.add(a.district);
    });
    return Array.from(set).sort();
  }, [assets]);

  // Filtered Assets
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchSearch =
        search === "" ||
        asset.name.toLowerCase().includes(search.toLowerCase()) ||
        asset.asset_code.toLowerCase().includes(search.toLowerCase()) ||
        (asset.district && asset.district.toLowerCase().includes(search.toLowerCase()));

      const matchType =
        selectedType === "ALL" || asset.asset_type.toLowerCase() === selectedType.toLowerCase();

      const matchDistrict = selectedDistrict === "ALL" || asset.district === selectedDistrict;

      const matchRisk =
        selectedRisk === "ALL" ||
        (selectedRisk === "HIGH" && (asset.risk_level === "HIGH" || (asset.risk_score != null && asset.risk_score >= 70))) ||
        (selectedRisk === "MEDIUM" && (asset.risk_level === "MEDIUM" || (asset.risk_score != null && asset.risk_score >= 40 && asset.risk_score < 70))) ||
        (selectedRisk === "LOW" && (asset.risk_level === "LOW" || (asset.risk_score != null && asset.risk_score < 40)));

      return matchSearch && matchType && matchDistrict && matchRisk;
    });
  }, [assets, search, selectedType, selectedDistrict, selectedRisk]);

  // Directions distance calculation
  const directionsInfo = useMemo(() => {
    if (!userLocation || !selected) return null;
    const [destLng, destLat] = selected.geometry.coordinates;
    const distKm = calculateDistance(userLocation[0], userLocation[1], destLat, destLng);
    const estMinutes = Math.round((distKm / 60) * 60); // Assuming 60 km/h avg
    return { distKm, estMinutes };
  }, [userLocation, selected]);

  const toggleUserLocation = () => {
    if (userLocation) {
      setUserLocation(undefined);
      setShowDirections(false);
    } else {
      // Default to AP State Secretariat, Velagapudi / Vijayawada
      setUserLocation([16.5398, 80.5284]);
    }
  };

  return (
    <div className="module-container">
      {/* Search & Filter Command Bar */}
      <div className="gis-command-bar">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            className="search-input pl-9"
            placeholder="Search asset name, code, district..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Category Filter */}
        <select
          className="select-input"
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
        >
          <option value="ALL">All Categories (5 Sectors)</option>
          <option value="dam">Dams</option>
          <option value="barrage">Barrages</option>
          <option value="bridge">Bridges</option>
          <option value="airport">Airports</option>
          <option value="temple">Temples</option>
        </select>

        {/* District Filter */}
        <select
          className="select-input"
          value={selectedDistrict}
          onChange={(e) => setSelectedDistrict(e.target.value)}
        >
          <option value="ALL">All Districts</option>
          {districts.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        {/* Risk Filter */}
        <select
          className="select-input"
          value={selectedRisk}
          onChange={(e) => setSelectedRisk(e.target.value)}
        >
          <option value="ALL">All Risk Levels</option>
          <option value="HIGH">High Risk (≥ 70)</option>
          <option value="MEDIUM">Medium Risk (40–69)</option>
          <option value="LOW">Low Risk (&lt; 40)</option>
        </select>

        {/* User Location Button */}
        <button
          type="button"
          className={`btn ${userLocation ? "btn-secondary" : "btn-outline"} text-xs shrink-0`}
          onClick={toggleUserLocation}
          title="Toggle current location simulator (AP State Secretariat)"
        >
          <Navigation className="size-3.5" />
          {userLocation ? "GPS Active" : "Simulate GPS"}
        </button>

        {userLocation && selected && (
          <button
            type="button"
            className={`btn ${showDirections ? "btn-primary" : "btn-outline"} text-xs shrink-0`}
            onClick={() => setShowDirections(!showDirections)}
          >
            <Compass className="size-3.5" />
            {showDirections ? "Hide Route" : "Get Directions"}
          </button>
        )}

        <button
          type="button"
          className="btn btn-outline text-xs shrink-0"
          onClick={() => {
            setSearch("");
            setSelectedType("ALL");
            setSelectedDistrict("ALL");
            setSelectedRisk("ALL");
            setShowDirections(false);
          }}
          title="Reset all filters"
        >
          <RotateCcw className="size-3.5" />
          Reset
        </button>
      </div>

      {/* Main Map & Sidebar Stage */}
      <div className="gis-stage-container">
        {/* Left Side: Interactive Asset List */}
        <aside className="gis-sidebar">
          <div className="sidebar-header">
            <span className="font-semibold text-slate-200">Matching Assets ({filteredAssets.length})</span>
            <span className="text-xs text-slate-400">Click to focus & update entire app</span>
          </div>

          <div className="sidebar-asset-list">
            {filteredAssets.map((asset) => {
              const isSelected = selected?.asset_code === asset.asset_code;
              return (
                <div
                  key={asset.asset_code}
                  className={`gis-asset-card ${isSelected ? "selected" : ""}`}
                  onClick={() => selectAsset(asset)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="gis-card-name truncate">{asset.name}</div>
                      <div className="gis-card-meta">
                        <span>{asset.asset_code}</span>
                        <span>·</span>
                        <span className="capitalize">{asset.asset_type}</span>
                        <span>·</span>
                        <span>{asset.district || "AP"}</span>
                      </div>
                    </div>
                    <span
                      className={`badge shrink-0 ${
                        asset.risk_level === "HIGH"
                          ? "badge-rose"
                          : asset.risk_level === "MEDIUM"
                          ? "badge-amber"
                          : "badge-emerald"
                      }`}
                    >
                      {asset.risk_score != null ? `${asset.risk_score.toFixed(1)} Risk` : "LOW"}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-1.5">
                    <span>Status: <strong className="text-slate-300">{asset.identity_status}</strong></span>
                    <span className="text-sky-400 font-medium">Select Asset →</span>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* Center / Right: Leaflet Map View */}
        <div className="gis-map-wrapper">
          <MapContainer
            center={[16.5062, 80.648]}
            zoom={8}
            scrollWheelZoom={true}
            className="leaflet-full-container"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <MapController
              selected={selected}
              userLocation={userLocation}
              showDirections={showDirections}
            />

            {/* Asset Markers */}
            {filteredAssets.map((asset) => {
              const [lng, lat] = asset.geometry.coordinates;
              const isSelected = selected?.asset_code === asset.asset_code;
              return (
                <Marker
                  key={asset.asset_code}
                  position={[lat, lng]}
                  icon={createMarkerIcon(asset, isSelected)}
                  eventHandlers={{
                    click: () => selectAsset(asset),
                  }}
                >
                  <Popup>
                    <div className="p-1 space-y-2 text-slate-900 max-w-[240px]">
                      <div>
                        <div className="font-bold text-sm text-slate-900">{asset.name}</div>
                        <div className="text-xs text-slate-600 font-mono">{asset.asset_code}</div>
                        <div className="text-xs text-slate-600 capitalize">
                          {asset.asset_type} · {asset.district || "Andhra Pradesh"}
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs py-1 border-y border-slate-200">
                        <span>Risk Score:</span>
                        <strong>{asset.risk_score != null ? `${asset.risk_score.toFixed(1)}` : "Low"}</strong>
                      </div>

                      <div className="flex items-center justify-between text-xs pb-1">
                        <span>Identity:</span>
                        <span className="font-medium text-emerald-700">{asset.identity_status}</span>
                      </div>

                      <div className="flex flex-col gap-1 pt-1">
                        <button
                          type="button"
                          className="w-full text-xs py-1 px-2 bg-slate-900 text-white rounded font-medium hover:bg-slate-800"
                          onClick={() => {
                            selectAsset(asset);
                            onNavigate("TWIN");
                          }}
                        >
                          Open Digital Twin 3D →
                        </button>
                        <button
                          type="button"
                          className="w-full text-xs py-1 px-2 bg-slate-100 text-slate-800 rounded font-medium hover:bg-slate-200 border"
                          onClick={() => {
                            selectAsset(asset);
                            onNavigate("ENGINEERING");
                          }}
                        >
                          View Engineering Specs →
                        </button>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

            {/* User GPS Marker */}
            {userLocation && (
              <Marker position={userLocation} icon={createUserIcon()}>
                <Popup>
                  <div className="text-xs font-semibold p-1">
                    📍 Simulated Location: AP Secretariat (Velagapudi)
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Directions Polyline */}
            {showDirections && userLocation && selected && (
              <Polyline
                positions={[
                  userLocation,
                  [selected.geometry.coordinates[1], selected.geometry.coordinates[0]],
                ]}
                color="#38bdf8"
                weight={4}
                dashArray="6, 8"
              />
            )}
          </MapContainer>

          {/* Map Legend Overlay */}
          <div className="gis-map-legend">
            <span className="font-semibold text-slate-300 mr-2 text-xs">Risk Legend:</span>
            <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-emerald-500" /> Low</span>
            <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-amber-500" /> Medium</span>
            <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-rose-500" /> High</span>
          </div>

          {/* Directions Floating Banner */}
          {showDirections && directionsInfo && selected && (
            <div className="gis-directions-banner">
              <Navigation className="size-5 text-sky-400 shrink-0" />
              <div>
                <div className="text-xs font-semibold text-slate-200">
                  Route to {selected.name}
                </div>
                <div className="text-[11px] text-slate-400">
                  Est. Distance: <strong className="text-sky-400">{directionsInfo.distKm} km</strong> · Approx Drive Time:{" "}
                  <strong className="text-slate-200">{directionsInfo.estMinutes} mins</strong> via state corridor
                </div>
              </div>
            </div>
          )}

          {/* Bottom Fast Navigation Bar for Selected Asset */}
          {selected && (
            <div className="gis-selected-strip">
              <div className="min-w-0">
                <div className="text-xs text-slate-400">Selected Monitored Asset:</div>
                <div className="text-sm font-semibold text-slate-100 truncate">
                  {selected.name} <span className="font-mono text-xs text-sky-400">({selected.asset_code})</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => onNavigate("ENGINEERING")}
                >
                  <Layers className="size-3.5" />
                  Engineering
                </button>
                <button
                  type="button"
                  className="btn btn-primary text-xs"
                  onClick={() => onNavigate("TWIN")}
                >
                  <Box className="size-3.5" />
                  Digital Twin 3D
                </button>
                <button
                  type="button"
                  className="btn btn-outline text-xs"
                  onClick={() => onNavigate("AI")}
                >
                  <Sparkles className="size-3.5" />
                  AI Assessment
                </button>
                <button
                  type="button"
                  className="btn btn-outline text-xs"
                  onClick={() => onNavigate("REPORTS")}
                >
                  <FileText className="size-3.5" />
                  Report
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
