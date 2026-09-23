import React from "react";
import { useSelectedAsset } from "../../context/AssetContext";
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  Compass,
  FileCheck,
  MapPin,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

interface DashboardModuleProps {
  onNavigate: (module: "GIS" | "ENGINEERING" | "TWIN" | "AI" | "EVIDENCE" | "REPORTS") => void;
}

export function DashboardModule({ onNavigate }: DashboardModuleProps) {
  const { assets, selectAsset, setSelectedCode } = useSelectedAsset();

  const total = assets.length;
  const verified = assets.filter((a) => a.identity_status === "VERIFIED").length;
  const highRisk = assets.filter((a) => a.risk_level === "HIGH" || (a.risk_score != null && a.risk_score >= 70)).length;
  const mediumRisk = assets.filter((a) => a.risk_level === "MEDIUM" || (a.risk_score != null && a.risk_score >= 40 && a.risk_score < 70)).length;
  const lowRisk = total - highRisk - mediumRisk;
  const mlCovered = assets.filter((a) => a.risk_score != null || a.twin_quality_score != null).length;
  const mlCoveragePct = total > 0 ? Math.round((mlCovered / total) * 100) : 0;
  const evidenceCovered = verified;
  const evidenceCoveragePct = total > 0 ? Math.round((evidenceCovered / total) * 100) : 0;

  // Breakdown by type
  const typeCounts: Record<string, number> = {};
  assets.forEach((a) => {
    const t = a.asset_type.toLowerCase();
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  });

  const alerts = [
    {
      id: "alt-1",
      title: "Prakasam Barrage: Water Level Observation",
      desc: "Water resources inflow 54,200 cusecs reported during monsoon flush. Discharge monitored at Krishna basin.",
      severity: "MEDIUM",
      assetCode: "AP_DAM_00001",
      time: "24m ago",
    },
    {
      id: "alt-2",
      title: "Polavaram Project: Upstream Coffer Dam Inspection Due",
      desc: "Routine pre-flood structural audit scheduled by AP Water Resources Department.",
      severity: "HIGH",
      assetCode: "AP_DAM_00002",
      time: "1h ago",
    },
    {
      id: "alt-3",
      title: "Godavari Arch Bridge: Acoustic Sensor Normal",
      desc: "Indian Railways structural deflection and vibration sensors within normal design limits.",
      severity: "LOW",
      assetCode: "AP_BR_00001",
      time: "3h ago",
    },
    {
      id: "alt-4",
      title: "Tirupati Airport: Runway Friction Test Completed",
      desc: "Airports Authority of India runway 08/26 surface friction index conforms to DGCA safety norms.",
      severity: "LOW",
      assetCode: "AP_AIR_AAI_TIRUPATI",
      time: "5h ago",
    },
  ];

  return (
    <div className="module-container">
      {/* Top Banner */}
      <div className="section-header">
        <div>
          <h1 className="section-title">Andhra Pradesh State Infrastructure Dashboard</h1>
          <p className="section-subtitle">
            Executive overview across 17 monitored high-value canonical structures · Verified identity, sensor telemetries, and risk intelligence.
          </p>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onNavigate("GIS")}
          >
            <Compass className="size-4" />
            Open GIS Command Center
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 my-6">
        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-sky-500/10 text-sky-400">
            <Building2 className="size-5" />
          </div>
          <div className="kpi-value">{total}</div>
          <div className="kpi-label">Monitored Assets</div>
          <div className="kpi-sub">5 Critical Sectors</div>
        </div>

        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-emerald-500/10 text-emerald-400">
            <CheckCircle2 className="size-5" />
          </div>
          <div className="kpi-value">{verified}</div>
          <div className="kpi-label">Authoritatively Verified</div>
          <div className="kpi-sub">{Math.round((verified / (total || 1)) * 100)}% Cross-checked</div>
        </div>

        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-rose-500/10 text-rose-400">
            <ShieldAlert className="size-5" />
          </div>
          <div className="kpi-value">{highRisk}</div>
          <div className="kpi-label">High-Risk Watchlist</div>
          <div className="kpi-sub">Immediate Action Required</div>
        </div>

        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-amber-500/10 text-amber-400">
            <AlertTriangle className="size-5" />
          </div>
          <div className="kpi-value">{mediumRisk}</div>
          <div className="kpi-label">Medium Surveillance</div>
          <div className="kpi-sub">Sensor Monitored</div>
        </div>

        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-purple-500/10 text-purple-400">
            <Sparkles className="size-5" />
          </div>
          <div className="kpi-value">{mlCoveragePct}%</div>
          <div className="kpi-label">ML Risk Coverage</div>
          <div className="kpi-sub">{mlCovered} of {total} Scored</div>
        </div>

        <div className="kpi-box">
          <div className="kpi-icon-wrap bg-blue-500/10 text-blue-400">
            <FileCheck className="size-5" />
          </div>
          <div className="kpi-value">{evidenceCoveragePct}%</div>
          <div className="kpi-label">Govt Evidence Audit</div>
          <div className="kpi-sub">Official Records Attached</div>
        </div>
      </div>

      {/* Main Grid: Sector Distribution + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Sector Breakdown & Quick Links */}
        <div className="card p-5 space-y-4">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Activity className="size-4 text-sky-400" />
            Monitored Portfolio by Sector
          </h2>
          <div className="space-y-3">
            {[
              { type: "Dams", count: typeCounts["dam"] || 1, desc: "Multipurpose reservoir structures", color: "bg-blue-500" },
              { type: "Barrages", count: typeCounts["barrage"] || 1, desc: "Gated river diversion structures", color: "bg-cyan-500" },
              { type: "Bridges", count: typeCounts["bridge"] || 2, desc: "Rail & Highway river crossings", color: "bg-amber-500" },
              { type: "Airports", count: typeCounts["airport"] || 6, desc: "AAI commercial aerodromes", color: "bg-emerald-500" },
              { type: "Temples", count: typeCounts["temple"] || 7, desc: "State heritage temple structures", color: "bg-purple-500" },
            ].map((sector) => (
              <div key={sector.type} className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-200">{sector.type}</div>
                  <div className="text-xs text-slate-400">{sector.desc}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-slate-100">{sector.count}</span>
                  <div className={`size-2.5 rounded-full ${sector.color}`} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Middle Column: Operational Alerts */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <ShieldAlert className="size-4 text-amber-400" />
              Live Infrastructure Alerts
            </h2>
            <span className="badge badge-amber">{alerts.length} Active</span>
          </div>

          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 cursor-pointer transition"
                onClick={() => {
                  setSelectedCode(alert.assetCode);
                  onNavigate("TWIN");
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      alert.severity === "HIGH"
                        ? "bg-rose-500/20 text-rose-300"
                        : alert.severity === "MEDIUM"
                        ? "bg-amber-500/20 text-amber-300"
                        : "bg-emerald-500/20 text-emerald-300"
                    }`}
                  >
                    {alert.severity}
                  </span>
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="size-3" />
                    {alert.time}
                  </span>
                </div>
                <div className="font-semibold text-sm text-slate-200 mt-1">{alert.title}</div>
                <div className="text-xs text-slate-400 mt-1 line-clamp-2">{alert.desc}</div>
                <div className="mt-2 text-[11px] font-mono text-sky-400 flex items-center gap-1">
                  View Twin →
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: High Priority Infrastructure Portfolio */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <MapPin className="size-4 text-emerald-400" />
              High Priority Structures
            </h2>
            <button
              type="button"
              className="text-xs text-sky-400 hover:underline"
              onClick={() => onNavigate("GIS")}
            >
              View on Map →
            </button>
          </div>

          <div className="space-y-2.5">
            {assets.slice(0, 5).map((asset) => (
              <div
                key={asset.asset_code}
                className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-sky-500/50 cursor-pointer transition flex items-center justify-between"
                onClick={() => {
                  selectAsset(asset);
                  onNavigate("ENGINEERING");
                }}
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm text-slate-200 truncate">{asset.name}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                    <span className="font-mono text-slate-500">{asset.asset_code}</span>
                    <span>·</span>
                    <span className="capitalize">{asset.asset_type}</span>
                    <span>·</span>
                    <span>{asset.district || "AP"}</span>
                  </div>
                </div>
                <div className="text-right ml-3 shrink-0">
                  <span
                    className={`badge ${
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
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
