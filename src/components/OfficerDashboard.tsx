import React, { useEffect, useState } from "react";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  Clock,
  PlusCircle,
  Wrench,
  FileText,
  ArrowRight,
  ClipboardList,
  CheckSquare,
  Bell,
  Calendar,
  Building,
  User,
} from "lucide-react";
import type { AssetSummary } from "../types/twin";
import { StatCard } from "./common/StatCard";
import { StatusBadge } from "./common/StatusBadge";
import { OfficerTab } from "./common/OfficerSidebar";

interface OfficerDashboardProps {
  assets: AssetSummary[];
  onSelectAsset: (asset: AssetSummary) => void;
  onNavigateTab: (tab: OfficerTab) => void;
  currentUser?: {
    name?: string;
    role?: string;
    department?: string;
  } | null;
}

export function OfficerDashboard({
  assets,
  onSelectAsset,
  onNavigateTab,
  currentUser,
}: OfficerDashboardProps) {
  const [inspections, setInspections] = useState<any[]>([]);
  const [maintenance, setMaintenance] = useState<any[]>([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [loading, setLoading] = useState(true);

  const officerName = currentUser?.name || "Er. K. V. Raman";
  const officerRole = currentUser?.role || "Executive Engineer (Civil)";
  const officerDept = currentUser?.department || "Andhra Pradesh Water Resources Department (APWRD)";

  // Format current date/time
  const currentDateTime = new Intl.DateTimeFormat("en-IN", {
    dateStyle: "full",
    timeStyle: "short",
  }).format(new Date());

  // Fetch real counts from backend
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetch("/api/v1/inspections").then((r) => (r.ok ? r.json() : [])),
      fetch("/api/v1/maintenance").then((r) => (r.ok ? r.json() : [])),
      fetch("/api/v1/notifications/unread-count").then((r) => (r.ok ? r.json() : { unread_count: 0 })),
    ])
      .then(([insp, maint, notif]) => {
        if (!isMounted) return;
        setInspections(Array.isArray(insp) ? insp : []);
        setMaintenance(Array.isArray(maint) ? maint : []);
        if (notif?.unread_count != null) {
          setUnreadNotifications(notif.unread_count);
        }
      })
      .catch((e) => console.error(e))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Compute metric cards with real backend counts
  const assignedAssetsCount = assets.length;
  const inspectionsDueCount = inspections.filter((i) => i.status === "SCHEDULED" || i.status === "SUBMITTED").length;
  const overdueInspectionsCount = inspections.filter((i) => i.status === "OVERDUE").length;
  const maintenanceScheduledCount = maintenance.filter((m) => m.status === "PLANNED" || m.status === "SCHEDULED").length;
  const pendingReviewsCount = inspections.filter((i) => i.status === "SUBMITTED").length;
  const highRiskAssets = assets.filter((a) => (a.risk_score ?? 0) >= 50);

  return (
    <div className="space-y-6">
      {/* Top Welcome Bar */}
      <div className="bg-white rounded-lg border border-[#D8E2EA] p-5 sm:p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>{currentDateTime}</span>
            <span>•</span>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Operational Desk Active
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Welcome, {officerName}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
            Role: <span className="font-semibold text-slate-800">{officerRole}</span> • Department:{" "}
            <span className="font-semibold text-slate-800">{officerDept}</span>
          </p>
        </div>

        {/* Prominent Action Button: + Add Infrastructure */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => onNavigateTab("add_asset")}
            className="flex items-center gap-2 py-2.5 px-4 rounded-md bg-[#1268A8] hover:bg-[#0D4E7A] text-white text-xs sm:text-sm font-bold shadow-sm transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ Add Infrastructure</span>
          </button>
        </div>
      </div>

      {/* Metric Cards (Real backend counts!) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        <StatCard
          label="Assigned Assets"
          value={assignedAssetsCount}
          subtext="State Registry"
          icon={Building}
          onClick={() => onNavigateTab("assets")}
        />
        <StatCard
          label="Inspections Due"
          value={inspectionsDueCount}
          subtext="Statutory Audits"
          icon={ClipboardList}
          variant="primary"
          onClick={() => onNavigateTab("inspections")}
        />
        <StatCard
          label="Overdue"
          value={overdueInspectionsCount}
          subtext="Action Required"
          icon={AlertTriangle}
          variant="danger"
          onClick={() => onNavigateTab("inspections")}
        />
        <StatCard
          label="Maintenance Sched."
          value={maintenanceScheduledCount}
          subtext="Active Work Orders"
          icon={Wrench}
          variant="default"
          onClick={() => onNavigateTab("maintenance")}
        />
        <StatCard
          label="Pending Reviews"
          value={pendingReviewsCount}
          subtext="Awaiting Approval"
          icon={CheckSquare}
          variant="warning"
          onClick={() => onNavigateTab("reviews")}
        />
        <StatCard
          label="High Risk Assets"
          value={highRiskAssets.length}
          subtext="Priority Watchlist"
          icon={Shield}
          variant="danger"
          onClick={() => onNavigateTab("gis")}
        />
        <StatCard
          label="Unread Alerts"
          value={unreadNotifications}
          subtext="System Telemetry"
          icon={Bell}
          variant="primary"
          onClick={() => onNavigateTab("notifications")}
        />
      </div>

      {/* Grid Sections: High Risk Infrastructure & Pending Reviews */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: High Risk Infrastructure Watchlist (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                High Risk Infrastructure Watchlist
              </h2>
              <p className="text-xs text-slate-500">
                Assets requiring accelerated structural audits or maintenance intervention
              </p>
            </div>
            <button
              onClick={() => onNavigateTab("gis")}
              className="text-xs font-semibold text-[#1268A8] hover:underline flex items-center gap-1"
            >
              <span>View On GIS</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {highRiskAssets.slice(0, 5).map((asset) => (
              <div
                key={asset.asset_code}
                onClick={() => {
                  onSelectAsset(asset);
                  onNavigateTab("twin");
                }}
                className="py-3 flex items-center justify-between gap-3 hover:bg-slate-50 px-2 rounded-md transition cursor-pointer"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-mono font-bold text-[#1268A8] px-1.5 py-0.2 bg-blue-50 rounded border border-blue-200">
                      {asset.asset_code}
                    </span>
                    <span className="text-[10px] uppercase font-medium text-slate-400">
                      {asset.category || asset.type}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 truncate">{asset.name}</h4>
                  <p className="text-[11px] text-slate-500">{asset.district}</p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Risk</span>
                    <span className="text-sm font-bold text-red-600 font-mono">
                      {(asset.risk_score ?? 60).toFixed(0)}/100
                    </span>
                  </div>
                  <StatusBadge status="HIGH_RISK" size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Pending Reviews & Upcoming Inspections (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Pending Reviews Card */}
          <div className="bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Pending Regulatory Reviews
              </h3>
              <button
                onClick={() => onNavigateTab("reviews")}
                className="text-xs font-semibold text-[#1268A8] hover:underline"
              >
                Open Queue
              </button>
            </div>

            <div className="space-y-2">
              {[
                { title: "Srisailam Dam Post-Flood Sluice Gate Audit", by: "Er. P. Rao", date: "Yesterday", status: "PENDING_REVIEW" },
                { title: "Prakasam Barrage Gate 14 Pier Crack Survey", by: "Er. M. Reddy", date: "2 days ago", status: "PENDING_REVIEW" },
              ].map((rev, idx) => (
                <div key={idx} className="p-2.5 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                  <div className="min-w-0 pr-2">
                    <p className="font-semibold text-slate-900 truncate">{rev.title}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{rev.by} • {rev.date}</p>
                  </div>
                  <StatusBadge status={rev.status} size="sm" />
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Maintenance Card */}
          <div className="bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Upcoming Maintenance
              </h3>
              <button
                onClick={() => onNavigateTab("maintenance")}
                className="text-xs font-semibold text-[#1268A8] hover:underline"
              >
                View Plans
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-md bg-blue-50/50 border border-blue-200">
                <div className="flex justify-between font-semibold text-slate-900 mb-1">
                  <span>Polavaram Spillway Hoist Lubrication</span>
                  <StatusBadge status="SCHEDULED" size="sm" />
                </div>
                <p className="text-[11px] text-slate-500">Scheduled: 2026-04-05 • APWRD Mechanical Div</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
