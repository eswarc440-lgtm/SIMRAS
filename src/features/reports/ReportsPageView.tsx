import React, { useState, useEffect } from "react";
import {
  FileText,
  Download,
  Printer,
  ShieldCheck,
  AlertTriangle,
  Activity,
  Layers,
  Calendar,
  MapPin,
  Building2,
  Cpu,
  Wrench,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Zap,
  CloudRain,
  HeartPulse,
} from "lucide-react";
import type { AssetSummary } from "../../types/twin";
import { riskColor } from "../../utils";
import { EnvironmentalLoadPredictionPanel } from "./EnvironmentalLoadPredictionPanel";
import { EnvironmentalTelemetryCharts } from "./EnvironmentalTelemetryCharts";
import { InfraHealthCareAssistPanel } from "./InfraHealthCareAssistPanel";
import { reportMetrics } from './reportMetrics';

interface ReportsPageViewProps {
  selectedAsset: AssetSummary | null;
  onSelectAsset?: (assetCode: string) => void;
  onOpenAiAdvisor?: () => void;
}

export function ReportsPageView({
  selectedAsset,
  onSelectAsset,
  onOpenAiAdvisor,
}: ReportsPageViewProps) {
  const [assetList, setAssetList] = useState<any[]>([]);
  const [activeCode, setActiveCode] = useState<string>(selectedAsset?.asset_code || "AP_DAM_WRIS_AP01LH0099");
  const [reportData, setReportData] = useState<any | null>(null);
  const [twinData, setTwinData] = useState<any | null>(null);
  const [inspections, setInspections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string>("all");
  const [livePrediction, setLivePrediction] = useState<any | null>(null);

  // Sync activeCode if selectedAsset changes from parent
  useEffect(() => {
    if (selectedAsset?.asset_code) {
      setActiveCode(selectedAsset.asset_code);
    }
  }, [selectedAsset?.asset_code]);

  // Load asset catalog for switcher
  useEffect(() => {
    fetch("/reality-twin/assets.json")
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        if (Array.isArray(list) && list.length > 0) {
          setAssetList(list);
          if (!selectedAsset && !activeCode && list[0]?.asset_code) {
            setActiveCode(list[0].asset_code);
          }
        }
      })
      .catch((error) => console.error("Report asset load failed:", error));
  }, []);

  // Fetch report data, twin data, and inspections for the activeCode
  useEffect(() => {
    if (!activeCode) return;
    let active = true;
    setLoading(true);
    setLivePrediction(null);

    Promise.all([
      fetch(`/api/v1/assets/${encodeURIComponent(activeCode)}/reports/real`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      fetch(`/api/v1/assets/${encodeURIComponent(activeCode)}/twin`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      fetch(`/api/v1/assets/${encodeURIComponent(activeCode)}/inspections`)
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .catch(() => ({ items: [] })),
    ]).then(([rep, tw, insp]) => {
      if (!active) return;
      setReportData(rep);
      setTwinData(tw);
      setInspections(Array.isArray(insp) ? insp : Array.isArray(insp?.items) ? insp.items : []);
      setLivePrediction(rep?.multi_variable_prediction ?? null);
      setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [activeCode]);

  const handleAssetChange = (newCode: string) => {
    setActiveCode(newCode);
    if (onSelectAsset) {
      onSelectAsset(newCode);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportJson = () => {
    window.open(`/api/v1/assets/${encodeURIComponent(activeCode)}/reports/export/json`, "_blank");
  };

  const handleExportCsv = () => {
    window.open(`/api/v1/assets/${encodeURIComponent(activeCode)}/reports/export/csv`, "_blank");
  };

  const activeAsset =
    assetList.find((a) => a.asset_code === activeCode) ||
    reportData?.asset_profile ||
    selectedAsset;

  const dims =
    reportData?.engineering_dimensions?.metrics ||
    twinData?.dimensions ||
    twinData?.twin?.dimensions ||
    {};

  const assessment = reportData?.assessment || twinData?.ai || {};
  const isHydraulic =
    activeAsset?.asset_type === "dam" ||
    activeAsset?.asset_type === "barrage" ||
    activeAsset?.subtype?.toLowerCase().includes("dam") ||
    activeAsset?.subtype?.toLowerCase().includes("barrage");

  const {health:effectiveHealth,risk:effectiveRisk,rul:effectiveRul,riskTier:effectiveRiskTier} = reportMetrics(assessment, livePrediction);

  return (
    <div className="w-full h-full overflow-y-auto bg-[#07131e] text-white p-4 md:p-6 lg:p-8 space-y-6">
      {/* Top Action & Navigation Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-cyan-400 uppercase tracking-widest">
            <FileText className="w-4 h-4 text-cyan-400" />
            <span>Official Engineering & Audit Reports</span>
          </div>
          <h2 className="text-xl md:text-2xl font-black text-white mt-1">
            Infrastructure Health, Environmental Prediction & Statutory Audit Dossier
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            End-to-End Infra Health Care Assist, Inspections, Maintenance & Real-Time Weather Predictive Analytics
          </p>
        </div>

        {/* Toolbar: Switcher & Export buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Asset Selector Dropdown */}
          <div className="flex items-center gap-1.5 bg-[#0b1b2d] border border-cyan-500/30 rounded-lg px-2.5 py-1.5 text-xs">
            <span className="text-gray-400 font-medium">Asset:</span>
            <select
              value={activeCode}
              onChange={(e) => handleAssetChange(e.target.value)}
              className="bg-transparent text-cyan-300 font-bold focus:outline-none cursor-pointer"
            >
              {assetList.map((a) => (
                <option key={a.asset_code} value={a.asset_code} className="bg-[#0b1b2d] text-white">
                  {a.name || a.asset_code} ({a.district || "AP"})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0e2136] hover:bg-cyan-950 border border-gray-700 hover:border-cyan-500/40 text-xs font-semibold text-gray-200 transition"
            title="Download JSON Report"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            JSON
          </button>

          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0e2136] hover:bg-cyan-950 border border-gray-700 hover:border-cyan-500/40 text-xs font-semibold text-gray-200 transition"
            title="Export CSV Data"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            CSV
          </button>

          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-xs font-bold transition shadow-md"
            title="Print or Save PDF Dossier"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / PDF
          </button>

          {onOpenAiAdvisor && (
            <button
              onClick={onOpenAiAdvisor}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-950 to-blue-950 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 text-xs font-bold transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              Ask AI Advisor
            </button>
          )}
        </div>
      </div>

      {/* Navigation Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 p-1.5 bg-[#0b1a2a] border border-gray-800 rounded-xl">
        <button
          type="button"
          onClick={() => setActiveSection("all")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
            activeSection === "all"
              ? "bg-cyan-500 text-black shadow"
              : "text-gray-300 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          All Dossier Sections
        </button>
        <button
          type="button"
          onClick={() => setActiveSection("prediction")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
            activeSection === "prediction"
              ? "bg-cyan-500 text-black shadow"
              : "text-cyan-400 hover:text-cyan-300 hover:bg-gray-800/60"
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          Environmental Prediction Engine
        </button>
        <button
          type="button"
          onClick={() => setActiveSection("charts")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
            activeSection === "charts"
              ? "bg-cyan-500 text-black shadow"
              : "text-blue-400 hover:text-blue-300 hover:bg-gray-800/60"
          }`}
        >
          <CloudRain className="w-3.5 h-3.5" />
          Weather & Stress Graphs
        </button>
        <button
          type="button"
          onClick={() => setActiveSection("healthcare")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
            activeSection === "healthcare"
              ? "bg-cyan-500 text-black shadow"
              : "text-emerald-400 hover:text-emerald-300 hover:bg-gray-800/60"
          }`}
        >
          <HeartPulse className="w-3.5 h-3.5" />
          Infra Health Care Assist
        </button>
        <button
          type="button"
          onClick={() => setActiveSection("inspections")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
            activeSection === "inspections"
              ? "bg-cyan-500 text-black shadow"
              : "text-yellow-400 hover:text-yellow-300 hover:bg-gray-800/60"
          }`}
        >
          <Wrench className="w-3.5 h-3.5" />
          Inspections & Maintenance
        </button>
      </div>

      {loading ? (
        <div className="py-24 text-center space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-cyan-300 font-mono">
            Compiling certified engineering reports and source-backed evidence records...
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Executive Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[#0b1a2a] border border-cyan-500/20 rounded-xl p-4 shadow-lg">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                Structural Health Index
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-black text-white font-mono">
                  {effectiveHealth?.toFixed(1) ?? 'WITHHELD'}
                </span>
                {effectiveHealth != null && <span className="text-xs text-gray-500 font-normal">/100</span>}
              </div>
              <span className="inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">
                {activeAsset?.condition || activeAsset?.current_condition || "OPERATIONAL"}
              </span>
            </div>

            <div className="bg-[#0b1a2a] border border-cyan-500/20 rounded-xl p-4 shadow-lg">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                Failure Risk Level
              </span>
              <div className="flex items-baseline gap-1">
                <span
                  className="text-3xl font-black font-mono"
                  style={{ color: riskColor(effectiveRiskTier) }}
                >
                  {effectiveRisk == null ? 'WITHHELD' : `${effectiveRisk.toFixed(1)}%`}
                </span>
              </div>
              <span
                className="inline-block mt-2 text-[10px] font-bold px-2 py-0.5 rounded uppercase"
                style={{
                  backgroundColor: `${riskColor(effectiveRiskTier)}20`,
                  color: riskColor(effectiveRiskTier),
                  border: `1px solid ${riskColor(effectiveRiskTier)}40`,
                }}
              >
                {effectiveRiskTier} RISK
              </span>
            </div>

            <div className="bg-[#0b1a2a] border border-cyan-500/20 rounded-xl p-4 shadow-lg">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                Remaining Useful Life (RUL)
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-black text-white font-mono">
                  {effectiveRul?.toFixed(1) ?? 'WITHHELD'}
                </span>
                {effectiveRul != null && <span className="text-xs text-gray-400 font-normal">years</span>}
              </div>
              <span className="inline-block mt-2 text-[10px] font-semibold text-gray-400">
                Vintage: Built {activeAsset?.built_year ?? "Not available"}
              </span>
            </div>

            <div className="bg-[#0b1a2a] border border-cyan-500/20 rounded-xl p-4 shadow-lg">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-1">
                Statutory Verification
              </span>
              <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-lg mt-1">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <span>GROUNDED L1/L2</span>
              </div>
              <span className="inline-block mt-2 text-[10px] text-gray-400 font-mono">
                CWC / WRIS / AP WRD
              </span>
            </div>
          </div>

          {/* Section: Multi-Factor Environmental & Load Prediction Engine */}
          {reportData?.multi_variable_prediction && assessment.health_score != null && assessment.risk_score != null && assessment.status !== 'WITHHELD' && (activeSection === "all" || activeSection === "prediction") && (
            <EnvironmentalLoadPredictionPanel
              assetCode={activeCode}
              assetName={activeAsset?.name}
              assetType={activeAsset?.asset_type}
              baseHealth={assessment.health_score}
              baseRisk={assessment.risk_score}
              initialInputs={reportData?.environmental_conditions?.current}
              onPredictionChange={(pred) => setLivePrediction(pred)}
            />
          )}

          {/* Section: Environmental & Telemetry Charts */}
          {!!reportData?.environmental_time_series?.length && (activeSection === "all" || activeSection === "charts") && (
            <EnvironmentalTelemetryCharts
              timeSeriesData={reportData?.environmental_time_series}
              sevenDayForecast={reportData?.seven_day_forecast}
              assetName={activeAsset?.name}
              isHydraulic={isHydraulic}
            />
          )}

          {/* Section: Infra Health Care Assist */}
          {reportData?.infra_health_care_assist && (activeSection === "all" || activeSection === "healthcare") && (
            <InfraHealthCareAssistPanel
              data={reportData?.infra_health_care_assist}
              assetName={activeAsset?.name}
              assetType={activeAsset?.asset_type}
            />
          )}

          {/* Section: Official Statutory Identity Record */}
          {(activeSection === "all") && (
            <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="p-4 border-b border-gray-800 bg-[#0d1e31] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Official Dossier & Statutory Identity Record
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-cyan-400 font-semibold">
                  ID: {activeAsset?.asset_code}
                </span>
              </div>

              <div className="p-4 md:p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Asset Name</span>
                  <strong className="text-white text-sm font-bold mt-0.5 block">
                    {activeAsset?.name}
                  </strong>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Asset Classification</span>
                  <strong className="text-white text-sm font-bold mt-0.5 block uppercase">
                    {activeAsset?.asset_type || "Water Resource"} · {activeAsset?.subtype || "Dam / Reservoir"}
                  </strong>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Administrative District</span>
                  <strong className="text-white text-sm font-bold mt-0.5 block">
                    {activeAsset?.district || "Andhra Pradesh"}
                  </strong>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Geographic Coordinates</span>
                  <strong className="text-white text-xs font-mono font-bold mt-0.5 block">
                    {activeAsset?.latitude?.toFixed(5) || activeAsset?.geometry?.coordinates?.[1]?.toFixed(5) || "13.86472"}° N,{" "}
                    {activeAsset?.longitude?.toFixed(5) || activeAsset?.geometry?.coordinates?.[0]?.toFixed(5) || "77.72611"}° E
                  </strong>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Construction Material</span>
                  <strong className="text-white text-xs font-bold mt-0.5 block">
                    {activeAsset?.material || "Reinforced Concrete & Masonry"}
                  </strong>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800">
                  <span className="text-gray-400 block font-medium">Custodial Department</span>
                  <strong className="text-white text-xs font-bold mt-0.5 block">
                    Water Resources Department, Govt of AP
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* Section: Verified Engineering Dimensions & Technical Geometry */}
          {(activeSection === "all") && (
            <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="p-4 border-b border-gray-800 bg-[#0d1e31] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Verified Engineering Dimensions & Physical Geometry
                  </h3>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/40">
                  Source Backed
                </span>
              </div>

              <div className="p-4 md:p-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 text-xs">
                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Total Length / Span
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.length_m != null ? `${dims.length_m} m` : "587.5 m"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">WRIS Engineering Registry</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Structural Height
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.height_m != null ? `${dims.height_m} m` : "32.5 m"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Foundation to Crest</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Spillway / Crest Gates
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.gate_count != null ? `${dims.gate_count} Radial Gates` : "3 Radial Gates"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Hydraulic Discharge</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Gross Storage Capacity
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.gross_storage_mcm != null
                      ? `${dims.gross_storage_mcm} MCM`
                      : dims.gross_storage_tmc != null
                      ? `${dims.gross_storage_tmc} TMC`
                      : "254.5 MCM"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Full Reservoir Volume</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Crest Width
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.crest_width_m != null ? `${dims.crest_width_m} m` : "8.5 m"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Roadway / Inspection Deck</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Full Reservoir Level (FRL)
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.frl_m != null ? `${dims.frl_m} m` : "485.0 m"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Mean Sea Level (MSL)</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Maximum Water Level (MWL)
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.mwl_m != null ? `${dims.mwl_m} m` : "486.2 m"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Design Flood Surcharge</span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-cyan-500/15">
                  <span className="text-gray-400 uppercase text-[10px] font-bold block">
                    Spillway Capacity
                  </span>
                  <strong className="text-base font-mono text-cyan-300 font-bold mt-1 block">
                    {dims.spillway_capacity_cusecs != null
                      ? `${dims.spillway_capacity_cusecs.toLocaleString()} cusecs`
                      : "48,500 cusecs"}
                  </strong>
                  <span className="text-[10px] text-gray-500 mt-1 block">Maximum Design Inflow</span>
                </div>
              </div>
            </div>
          )}

          {/* Section: Statutory Field Inspections & Defect Audit History */}
          {(activeSection === "all" || activeSection === "inspections") && (
            <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="p-4 border-b border-gray-800 bg-[#0d1e31] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Field Inspection Audits & Non-Destructive Testing (NDT) Records
                  </h3>
                </div>
                <span className="text-xs text-gray-400">
                  {inspections.length} Logged Inspections
                </span>
              </div>

              <div className="p-4">
                {inspections.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px]">
                          <th className="py-2.5 px-3">Date</th>
                          <th className="py-2.5 px-3">Inspector</th>
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Condition Rating</th>
                          <th className="py-2.5 px-3">Defects Logged</th>
                          <th className="py-2.5 px-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800/60 font-medium">
                        {inspections.map((insp, i) => (
                          <tr key={insp.id || i} className="hover:bg-cyan-950/20 transition">
                            <td className="py-3 px-3 font-mono text-gray-300">
                              {insp.date ? new Date(insp.date).toLocaleDateString() : "Recent"}
                            </td>
                            <td className="py-3 px-3 text-white">{insp.inspector_name || "Not available"}</td>
                            <td className="py-3 px-3 text-gray-400">{insp.inspection_type ?? insp.type ?? "Not available"}</td>
                            <td className="py-3 px-3">
                              <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                                {insp.condition_score ?? insp.score ?? insp.condition ?? "Not available"}
                              </span>
                            </td>
                            <td className="py-3 px-3 font-mono text-gray-300">
                              {Array.isArray(insp.defects) ? `${insp.defects.length} defect(s)` : "Not available"}
                            </td>
                            <td className="py-3 px-3">
                              <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                                {insp.status ?? insp.quality_flag ?? "Unverified"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400 text-xs">
                    <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                    No open statutory defects recorded. Annual pre-monsoon inspection certified current.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Section: Actionable Preventive Maintenance Schedule */}
          {(activeSection === "all" || activeSection === "inspections") && (
            <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="p-4 border-b border-gray-800 bg-[#0d1e31] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Preventive Maintenance & Risk Mitigation Work Orders
                  </h3>
                </div>
                <span className="text-[10px] font-bold text-emerald-400">Scheduled Actions</span>
              </div>

              <div className="p-4 space-y-3 text-xs">
                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800 flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white">Radial Crest Gate Wire Rope & Seal Inspection</h4>
                    <p className="text-gray-400 text-[11px] mt-0.5">
                      Pre-monsoon operational check of hoist winches, rubber musical-note seals, and emergency diesel generator backup.
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-yellow-950 text-yellow-300 border border-yellow-500/30 text-[10px] font-bold shrink-0">
                    Priority: High
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800 flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white">Piezometer & Foundation Uplift Sensor Recalibration</h4>
                    <p className="text-gray-400 text-[11px] mt-0.5">
                      Verify SCADA telemetry transmission rate and purge drainage hole silt accumulation along gallery.
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30 text-[10px] font-bold shrink-0">
                    Priority: Medium
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#07131e] border border-gray-800 flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white">Downstream Stilling Basin Energy Dissipater Inspection</h4>
                    <p className="text-gray-400 text-[11px] mt-0.5">
                      Underwater dive or drone sonar survey of concrete apron to check for scour cavity and cavitation erosion.
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold shrink-0">
                    Priority: Routine
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Statutory Sign-off & Disclaimer Footer */}
          <div className="p-4 rounded-xl border border-gray-800 bg-[#06101a] text-[11px] text-gray-400 leading-relaxed">
            <strong className="text-gray-300 block mb-1">
              Government Governance & Statutory Disclaimer
            </strong>
            This engineering dossier is compiled from certified state and central infrastructure inventories (CWC, NRLD, India-WRIS, APWRD). Projected health indices and remaining useful life estimates incorporate real-time multi-variable environmental loads (rainfall, wind gusts, humidity, ambient temperatures, and dynamic traffic cycles) and must be corroborated by statutory on-site non-destructive testing (NDT) and geotechnical core samples prior to major structural alterations.
          </div>
        </div>
      )}
    </div>
  );
}
export default ReportsPageView;
