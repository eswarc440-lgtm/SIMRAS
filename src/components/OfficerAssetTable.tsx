import React, { useState, useMemo } from "react";
import {
  Search,
  Filter,
  Building,
  PlusCircle,
  Eye,
  FileText,
  Wrench,
  ClipboardList,
  ChevronDown,
  ArrowUpDown,
  Download,
} from "lucide-react";
import type { AssetSummary } from "../types/twin";
import { StatusBadge } from "./common/StatusBadge";

interface OfficerAssetTableProps {
  assets: AssetSummary[];
  onSelectAsset: (asset: AssetSummary) => void;
  onNavigateToTwin: (asset: AssetSummary) => void;
  onNavigateToReport: (assetCode: string) => void;
  onNavigateToInspections: (assetCode: string) => void;
  onNavigateToMaintenance: (assetCode: string) => void;
  onAddNewAsset: () => void;
}

export function OfficerAssetTable({
  assets,
  onSelectAsset,
  onNavigateToTwin,
  onNavigateToReport,
  onNavigateToInspections,
  onNavigateToMaintenance,
  onAddNewAsset,
}: OfficerAssetTableProps) {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [districtFilter, setDistrictFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState<"name" | "risk" | "health" | "district">("risk");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const districts = useMemo(() => {
    const set = new Set<string>();
    assets.forEach((a) => {
      if (a.district) set.add(a.district);
    });
    return Array.from(set).sort();
  }, [assets]);

  const filteredAssets = useMemo(() => {
    return assets
      .filter((a) => {
        if (search.trim()) {
          const q = search.toLowerCase();
          const matchName = a.name.toLowerCase().includes(q);
          const matchCode = a.asset_code.toLowerCase().includes(q);
          const matchDist = (a.district || "").toLowerCase().includes(q);
          if (!matchName && !matchCode && !matchDist) return false;
        }

        if (categoryFilter !== "ALL") {
          const cat = (a.category || a.type || "").toUpperCase();
          if (!cat.includes(categoryFilter)) return false;
        }

        if (districtFilter !== "ALL" && a.district !== districtFilter) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        let valA: any = a.name;
        let valB: any = b.name;

        if (sortBy === "risk") {
          valA = a.risk_score ?? 0;
          valB = b.risk_score ?? 0;
        } else if (sortBy === "health") {
          valA = a.health_score ?? (100 - (a.risk_score ?? 0));
          valB = b.health_score ?? (100 - (b.risk_score ?? 0));
        } else if (sortBy === "district") {
          valA = a.district || "";
          valB = b.district || "";
        }

        if (valA < valB) return sortOrder === "asc" ? -1 : 1;
        if (valA > valB) return sortOrder === "asc" ? 1 : -1;
        return 0;
      });
  }, [assets, search, categoryFilter, districtFilter, sortBy, sortOrder]);

  const toggleSort = (col: "name" | "risk" | "health" | "district") => {
    if (sortBy === col) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      setSortOrder("desc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Table Title & Actions */}
      <div className="bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            State Infrastructure Inventory & Asset Registry
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage physical asset registers, statutory engineering parameters, and inspection assignments
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onAddNewAsset}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#1268A8] hover:bg-[#0D4E7A] text-white text-xs font-bold shadow-sm transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ Add Infrastructure</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-lg border border-[#D8E2EA] p-3.5 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          {/* Search */}
          <div className="relative min-w-[240px] flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by code, asset name, or district..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-[#D8E2EA] rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:ring-1 focus:ring-[#1268A8]"
            />
          </div>

          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="text-xs font-medium bg-white border border-[#D8E2EA] rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Categories</option>
            <option value="DAM">Dams</option>
            <option value="BARRAGE">Barrages</option>
            <option value="BRIDGE">Bridges</option>
            <option value="AIRPORT">Airports</option>
            <option value="TEMPLE">Temples</option>
          </select>

          {/* District filter */}
          <select
            value={districtFilter}
            onChange={(e) => setDistrictFilter(e.target.value)}
            className="text-xs font-medium bg-white border border-[#D8E2EA] rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Districts ({districts.length})</option>
            {districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Showing <span className="font-bold text-slate-800">{filteredAssets.length}</span> of{" "}
          <span className="font-bold text-slate-800">{assets.length}</span> assets
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-lg border border-[#D8E2EA] shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-[#D8E2EA] text-[11px] uppercase font-bold text-slate-500">
              <tr>
                <th
                  onClick={() => toggleSort("name")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100 transition"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Asset Code & Name</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="px-4 py-3">Category</th>
                <th
                  onClick={() => toggleSort("district")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100 transition"
                >
                  <div className="flex items-center gap-1.5">
                    <span>District</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th
                  onClick={() => toggleSort("health")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100 transition text-center"
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>Health Score</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th
                  onClick={() => toggleSort("risk")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100 transition text-center"
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>Risk Score</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-right">Operational Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredAssets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-400">
                    No infrastructure assets matched your search criteria.
                  </td>
                </tr>
              ) : (
                filteredAssets.map((asset) => {
                  const risk = asset.risk_score ?? 0;
                  const health = asset.health_score ?? Math.max(0, 100 - risk);

                  return (
                    <tr
                      key={asset.asset_code}
                      className="hover:bg-slate-50 transition cursor-pointer"
                      onClick={() => onSelectAsset(asset)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="font-mono text-[10px] font-bold text-[#1268A8]">
                            {asset.asset_code}
                          </span>
                          <span className="font-bold text-slate-900 text-xs mt-0.5">
                            {asset.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-block uppercase text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                          {asset.category || asset.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-700">
                        {asset.district || "—"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-mono font-bold text-[#1268A8]">
                          {health.toFixed(0)}
                          <span className="text-[10px] text-slate-400">/100</span>
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`font-mono font-bold ${
                            risk >= 60
                              ? "text-red-600"
                              : risk >= 30
                              ? "text-amber-600"
                              : "text-emerald-600"
                          }`}
                        >
                          {risk.toFixed(0)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge
                          status={risk >= 60 ? "HIGH_RISK" : risk >= 30 ? "MEDIUM_RISK" : "HEALTHY"}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div
                          className="flex items-center justify-end gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => onNavigateToTwin(asset)}
                            title="Open 3D Digital Twin"
                            className="p-1.5 rounded text-slate-600 hover:text-[#1268A8] hover:bg-blue-50 transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onNavigateToReport(asset.asset_code)}
                            title="View Engineering Report"
                            className="p-1.5 rounded text-slate-600 hover:text-[#1268A8] hover:bg-blue-50 transition"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onNavigateToInspections(asset.asset_code)}
                            title="Schedule or View Inspections"
                            className="p-1.5 rounded text-slate-600 hover:text-[#1268A8] hover:bg-blue-50 transition"
                          >
                            <ClipboardList className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onNavigateToMaintenance(asset.asset_code)}
                            title="Maintenance Work Orders"
                            className="p-1.5 rounded text-slate-600 hover:text-[#1268A8] hover:bg-blue-50 transition"
                          >
                            <Wrench className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
