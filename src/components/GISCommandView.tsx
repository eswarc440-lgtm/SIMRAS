import React, { useState, useMemo } from "react";
import {
  Search,
  Filter,
  MapPin,
  Layers,
  Check,
  ChevronRight,
  Shield,
  Activity,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  X,
} from "lucide-react";
import type { AssetSummary, MapFeatureCollection } from "../types/twin";
import { GISMap } from "./GISMap";
import { normalizeCoordinates } from "../lib/coordinates";
import { StatusBadge } from "./common/StatusBadge";

interface GISCommandViewProps {
  assets: AssetSummary[];
  mapFeatures: MapFeatureCollection;
  selectedAsset?: AssetSummary;
  onSelectAsset: (asset: AssetSummary) => void;
  onOpenAssetDetails: (asset: AssetSummary) => void;
}

type CategoryKey = "ALL" | "DAM" | "BARRAGE" | "BRIDGE" | "AIRPORT" | "TEMPLE";
type RiskFilterKey = "ALL" | "HEALTHY" | "MODERATE" | "HIGH";

export function GISCommandView({
  assets,
  mapFeatures,
  selectedAsset,
  onSelectAsset,
  onOpenAssetDetails,
}: GISCommandViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<CategoryKey>("ALL");
  const [selectedRisk, setSelectedRisk] = useState<RiskFilterKey>("ALL");
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);

  // Filter assets
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = asset.name.toLowerCase().includes(q);
        const matchCode = asset.asset_code.toLowerCase().includes(q);
        const matchDistrict = (asset.district || "").toLowerCase().includes(q);
        if (!matchName && !matchCode && !matchDistrict) return false;
      }

      // Category filter
      if (selectedCategory !== "ALL") {
        const cat = (asset.asset_type || asset.category || asset.type || "").toUpperCase();
        if (!cat.includes(selectedCategory)) return false;
      }

      // Risk filter
      if (selectedRisk !== "ALL") {
        const risk = asset.risk_score ?? 0;
        if (selectedRisk === "HEALTHY" && risk >= 30) return false;
        if (selectedRisk === "MODERATE" && (risk < 30 || risk >= 60)) return false;
        if (selectedRisk === "HIGH" && risk < 60) return false;
      }

      return true;
    });
  }, [assets, searchQuery, selectedCategory, selectedRisk]);

  const categories: { key: CategoryKey; label: string; count: number }[] = [
    { key: "ALL", label: "All Infrastructure", count: assets.length },
    {
      key: "DAM",
      label: "Dams",
      count: assets.filter((a) => (a.asset_type || a.category || a.type || "").toUpperCase().includes("DAM")).length,
    },
    {
      key: "BARRAGE",
      label: "Barrages",
      count: assets.filter((a) => (a.asset_type || a.category || a.type || "").toUpperCase().includes("BARRAGE")).length,
    },
    {
      key: "BRIDGE",
      label: "Bridges",
      count: assets.filter((a) => (a.asset_type || a.category || a.type || "").toUpperCase().includes("BRIDGE")).length,
    },
    {
      key: "AIRPORT",
      label: "Airports",
      count: assets.filter((a) => (a.asset_type || a.category || a.type || "").toUpperCase().includes("AIRPORT")).length,
    },
    {
      key: "TEMPLE",
      label: "Temples",
      count: assets.filter((a) => (a.asset_type || a.category || a.type || "").toUpperCase().includes("TEMPLE")).length,
    },
  ];

  const riskFilters: { key: RiskFilterKey; label: string; color: string }[] = [
    { key: "ALL", label: "All Risk Levels", color: "bg-slate-400" },
    { key: "HEALTHY", label: "Healthy (<30)", color: "bg-emerald-500" },
    { key: "MODERATE", label: "Moderate Risk (30-59)", color: "bg-amber-500" },
    { key: "HIGH", label: "High Risk (≥60)", color: "bg-red-500" },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-7.5rem)] bg-[#F4F7FA]">
      {/* Top GIS Title Bar */}
      <div className="bg-white border-b border-[#D8E2EA] px-4 sm:px-6 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-md bg-blue-50 text-[#1268A8] border border-blue-100">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm sm:text-base font-bold text-slate-900 leading-tight">
              GIS Command & Spatial Infrastructure Registry
            </h1>
            <p className="text-[11px] text-slate-500 hidden sm:block">
              Georeferenced monitoring of 26 districts • Andhra Pradesh Disaster Management System
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMobileSidebar(!showMobileSidebar)}
            className="md:hidden flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 rounded-md border border-slate-200"
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Filters ({filteredAssets.length})</span>
          </button>

          <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            <span className="font-bold text-[#1268A8]">{filteredAssets.length}</span> of{" "}
            <span>{assets.length} Assets Displayed</span>
          </span>
        </div>
      </div>

      {/* Main Split Layout: Left Control Sidebar + Main Map Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar */}
        <div
          className={`w-80 md:w-96 bg-white border-r border-[#D8E2EA] flex flex-col shrink-0 z-20 transition-all duration-200 md:static absolute inset-y-0 left-0 shadow-lg md:shadow-none ${
            showMobileSidebar ? "translate-x-0" : "-translate-x-full md:translate-x-0"
          }`}
        >
          {/* Mobile close button */}
          <div className="md:hidden p-3 border-b border-slate-100 flex items-center justify-between bg-slate-50">
            <span className="text-xs font-bold text-slate-800">Filter Infrastructure</span>
            <button
              onClick={() => setShowMobileSidebar(false)}
              className="p-1 text-slate-500 hover:text-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Search Box */}
          <div className="p-3.5 border-b border-[#D8E2EA] bg-slate-50/50">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search infrastructure, district, or code..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-[#D8E2EA] rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#1268A8] focus:border-[#1268A8]"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  âœ•
                </button>
              )}
            </div>
          </div>

          {/* Category & Layer Filter Checkboxes */}
          <div className="p-3.5 border-b border-[#D8E2EA]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Infrastructure Categories
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {categories.map((cat) => {
                const isSelected = selectedCategory === cat.key;
                return (
                  <button
                    key={cat.key}
                    onClick={() => setSelectedCategory(cat.key)}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition border text-left ${
                      isSelected
                        ? "bg-blue-50 border-[#1268A8] text-[#1268A8] font-semibold"
                        : "bg-white border-[#D8E2EA] text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <span className="truncate">{cat.label}</span>
                    <span
                      className={`text-[10px] font-mono px-1 rounded ml-1 ${
                        isSelected ? "bg-[#1268A8] text-white" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {cat.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Risk Level Filter */}
          <div className="p-3.5 border-b border-[#D8E2EA]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Structural Risk Filter
            </span>
            <div className="space-y-1">
              {riskFilters.map((rf) => {
                const isSelected = selectedRisk === rf.key;
                return (
                  <button
                    key={rf.key}
                    onClick={() => setSelectedRisk(rf.key)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition border text-left ${
                      isSelected
                        ? "bg-slate-100 border-slate-400 font-semibold text-slate-900"
                        : "bg-white border-[#D8E2EA] text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${rf.color}`} />
                      <span>{rf.label}</span>
                    </div>
                    {isSelected && <Check className="w-3.5 h-3.5 text-[#1268A8]" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Filtered Asset List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {filteredAssets.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No infrastructure matches your filter criteria.
              </div>
            ) : (
              filteredAssets.map((asset) => {
                const isSelected = selectedAsset?.asset_code === asset.asset_code;
                const riskVal = asset.risk_score ?? 0;
                return (
                  <div
                    key={asset.asset_code}
                    onClick={() => onSelectAsset(asset)}
                    className={`p-3 cursor-pointer transition flex items-start justify-between gap-2 text-left ${
                      isSelected
                        ? "bg-blue-50/80 border-l-4 border-l-[#1268A8]"
                        : "hover:bg-slate-50 border-l-4 border-l-transparent"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[10px] font-mono font-bold text-[#1268A8] bg-white px-1.5 py-0.2 rounded border border-blue-200">
                          {asset.asset_code}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase tracking-tight font-medium">
                          {asset.asset_type || asset.category || asset.type}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 truncate">{asset.name}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{asset.district}</p>
                      {!normalizeCoordinates(asset) && (
                        <p className="text-[10px] font-semibold text-amber-700 mt-0.5">
                          Location not available
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col items-end shrink-0 gap-1.5">
                      <StatusBadge
                        status={
                          riskVal >= 60 ? "HIGH_RISK" : riskVal >= 30 ? "MEDIUM_RISK" : "HEALTHY"
                        }
                        size="sm"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenAssetDetails(asset);
                        }}
                        className="text-[10px] font-semibold text-[#1268A8] hover:underline inline-flex items-center gap-0.5"
                        title="View full Digital Twin & details"
                      >
                        <span>Details</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Map Stage */}
        <div className="flex-1 relative bg-slate-200 min-w-0">
          <GISMap
            assets={filteredAssets}
            mapFeatures={mapFeatures}
            selected={selectedAsset}
            onSelect={onSelectAsset}
            onOpenDetails={onOpenAssetDetails}
          />

          {/* Floating Selected Asset Card on Map (Light Government Card) */}
          {selectedAsset && (
            <div className="absolute top-4 right-4 z-[500] w-80 max-w-[calc(100%-2rem)] bg-white/95 backdrop-blur-md rounded-lg border border-[#D8E2EA] p-4 shadow-xl animate-in fade-in slide-in-from-top-2">
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[10px] font-mono font-bold text-[#1268A8] px-2 py-0.5 bg-blue-50 rounded border border-blue-200">
                  {selectedAsset.asset_code}
                </span>
                <StatusBadge
                  status={
                    (selectedAsset.risk_score ?? 0) >= 60
                      ? "HIGH_RISK"
                      : (selectedAsset.risk_score ?? 0) >= 30
                      ? "MEDIUM_RISK"
                      : "HEALTHY"
                  }
                  size="sm"
                />
              </div>

              <h3 className="text-sm font-bold text-slate-900">{selectedAsset.name}</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {selectedAsset.district} • <span className="capitalize">{selectedAsset.asset_type || selectedAsset.category || selectedAsset.type}</span>
              </p>
              {!normalizeCoordinates(selectedAsset) && (
                <p className="text-[11px] font-semibold text-amber-700 mt-1">
                  Location not available
                </p>
              )}

              <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-slate-100 text-center">
                <div className="bg-slate-50 p-2 rounded border border-slate-100">
                  <span className="text-[9px] uppercase font-semibold text-slate-400 block">
                    Health Score
                  </span>
                  <span className="text-base font-bold text-slate-800">
                    {(selectedAsset.health_score ?? (100 - (selectedAsset.risk_score ?? 0))).toFixed(0)}
                    <span className="text-[10px] text-slate-400">/100</span>
                  </span>
                </div>
                <div className="bg-slate-50 p-2 rounded border border-slate-100">
                  <span className="text-[9px] uppercase font-semibold text-slate-400 block">
                    Risk Score
                  </span>
                  <span
                    className={`text-base font-bold ${
                      (selectedAsset.risk_score ?? 0) >= 60
                        ? "text-red-600"
                        : (selectedAsset.risk_score ?? 0) >= 30
                        ? "text-amber-600"
                        : "text-emerald-600"
                    }`}
                  >
                    {(selectedAsset.risk_score ?? 0).toFixed(0)}
                  </span>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <button
                  onClick={() => onOpenAssetDetails(selectedAsset)}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md bg-[#1268A8] hover:bg-[#0D4E7A] text-white text-xs font-semibold shadow-sm transition"
                >
                  <span>View Full Digital Twin</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Map Legend (Bottom Right, Light Government Style) */}
          <div className="absolute bottom-4 left-4 z-[500] bg-white/95 backdrop-blur-md rounded-md border border-[#D8E2EA] px-3 py-2 shadow-md hidden sm:flex items-center gap-4 text-[11px] text-slate-600">
            <span className="font-semibold text-slate-800">Risk Legend:</span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>Healthy</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>Moderate</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>Critical</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}


