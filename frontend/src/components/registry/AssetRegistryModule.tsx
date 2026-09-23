import React, { useState, useMemo } from "react";
import { useSelectedAsset } from "../../context/AssetContext";
import {
  Building2,
  CheckCircle2,
  ExternalLink,
  Filter,
  Layers,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { AssetSummary } from "../../types/twin";

interface AssetRegistryModuleProps {
  onNavigate: (module: "ENGINEERING" | "TWIN" | "AI" | "EVIDENCE" | "REPORTS") => void;
}

export function AssetRegistryModule({ onNavigate }: AssetRegistryModuleProps) {
  const { assets, selected, selectAsset } = useSelectedAsset();

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [identityFilter, setIdentityFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");

  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchSearch =
        search === "" ||
        asset.name.toLowerCase().includes(search.toLowerCase()) ||
        asset.asset_code.toLowerCase().includes(search.toLowerCase()) ||
        (asset.district && asset.district.toLowerCase().includes(search.toLowerCase()));

      const matchType =
        typeFilter === "ALL" || asset.asset_type.toLowerCase() === typeFilter.toLowerCase();

      const matchIdentity =
        identityFilter === "ALL" || asset.identity_status === identityFilter;

      const matchRisk =
        riskFilter === "ALL" ||
        (riskFilter === "HIGH" && (asset.risk_level === "HIGH" || (asset.risk_score != null && asset.risk_score >= 70))) ||
        (riskFilter === "MEDIUM" && (asset.risk_level === "MEDIUM" || (asset.risk_score != null && asset.risk_score >= 40 && asset.risk_score < 70))) ||
        (riskFilter === "LOW" && (asset.risk_level === "LOW" || (asset.risk_score != null && asset.risk_score < 40)));

      return matchSearch && matchType && matchIdentity && matchRisk;
    });
  }, [assets, search, typeFilter, identityFilter, riskFilter]);

  return (
    <div className="module-container">
      {/* Header */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Official Andhra Pradesh Asset Registry</h1>
          <p className="section-subtitle">
            Authoritative inventory of monitored state dams, barrages, bridges, commercial aerodromes, and heritage temples.
          </p>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Showing {filteredAssets.length} of {assets.length} canonical records
        </div>
      </div>

      {/* Filter Row */}
      <div className="card p-4 my-4 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[240px] relative">
          <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            className="search-input pl-9"
            placeholder="Search by asset name, code, or district..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="select-input"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="ALL">All Categories</option>
          <option value="dam">Dams</option>
          <option value="barrage">Barrages</option>
          <option value="bridge">Bridges</option>
          <option value="airport">Airports</option>
          <option value="temple">Temples</option>
        </select>

        <select
          className="select-input"
          value={identityFilter}
          onChange={(e) => setIdentityFilter(e.target.value)}
        >
          <option value="ALL">All Identity Statuses</option>
          <option value="VERIFIED">Verified Only</option>
          <option value="NEEDS_VERIFICATION">Needs Verification</option>
        </select>

        <select
          className="select-input"
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
        >
          <option value="ALL">All Risk Levels</option>
          <option value="HIGH">High Risk</option>
          <option value="MEDIUM">Medium Risk</option>
          <option value="LOW">Low Risk</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/90 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Asset Code & Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">District / Location</th>
                <th className="py-3 px-4">Coordinates (Lng, Lat)</th>
                <th className="py-3 px-4">Identity Status</th>
                <th className="py-3 px-4">Risk Evaluation</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredAssets.map((asset) => {
                const isSelected = selected?.asset_code === asset.asset_code;
                const [lng, lat] = asset.geometry.coordinates;

                return (
                  <tr
                    key={asset.asset_code}
                    className={`hover:bg-slate-900/60 transition ${isSelected ? "bg-sky-950/30 border-l-2 border-l-sky-500" : ""}`}
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-200">{asset.name}</div>
                      <div className="font-mono text-xs text-slate-500">{asset.asset_code}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="capitalize text-slate-300 font-medium">{asset.asset_type}</span>
                      {asset.subtype && <span className="text-xs text-slate-500 block">{asset.subtype}</span>}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {asset.district || "Andhra Pradesh"}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                      {lng.toFixed(4)}, {lat.toFixed(4)}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded ${
                          asset.identity_status === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        <ShieldCheck className="size-3" />
                        {asset.identity_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`badge ${
                          asset.risk_level === "HIGH"
                            ? "badge-rose"
                            : asset.risk_level === "MEDIUM"
                            ? "badge-amber"
                            : "badge-emerald"
                        }`}
                      >
                        {asset.risk_score != null ? `${asset.risk_score.toFixed(1)} Risk` : "LOW RISK"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          className={`btn ${isSelected ? "btn-primary" : "btn-outline"} text-xs py-1 px-2.5`}
                          onClick={() => selectAsset(asset)}
                          title="Select as active asset across all modules"
                        >
                          {isSelected ? "Active Asset" : "Select"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary text-xs py-1 px-2"
                          onClick={() => {
                            selectAsset(asset);
                            onNavigate("TWIN");
                          }}
                          title="Open in Digital Twin 3D"
                        >
                          Twin
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline text-xs py-1 px-2"
                          onClick={() => {
                            selectAsset(asset);
                            onNavigate("ENGINEERING");
                          }}
                          title="View Engineering Specifications"
                        >
                          Specs
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
