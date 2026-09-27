import React, { useState } from "react";
import {
  MapPin,
  Box,
  FileText,
  Shield,
  ArrowRight,
  Activity,
  Layers,
  Building,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import type { AssetSummary } from "../types/twin";
import { StatusBadge } from "./common/StatusBadge";
import { PublicTab } from "./common/PublicHeader";

interface PublicHomeProps {
  assets: AssetSummary[];
  onNavigate?: (tab: any) => void;
  onNavigateToGIS?: () => void;
  onNavigateToTwin?: (asset: AssetSummary) => void;
  onNavigateToReports?: (assetCode: string) => void;
  onOpenCitizenReport?: () => void;
  onOpenOfficerPortal?: () => void;
  onSelectAsset?: (asset: AssetSummary) => void;
}

export function PublicHome({
  assets,
  onNavigate,
  onNavigateToGIS,
  onNavigateToTwin,
  onNavigateToReports,
  onOpenCitizenReport,
  onOpenOfficerPortal,
  onSelectAsset,
}: PublicHomeProps) {
  const [activeCategory, setActiveCategory] = useState<string>("ALL");

  // Calculate real metrics from assets
  const totalAssets = assets.length;
  const categories = Array.from(new Set(assets.map((a) => (a.category || a.type || "").toUpperCase()))).filter(Boolean);
  const districts = Array.from(new Set(assets.map((a) => a.district))).filter(Boolean);
  const highRiskCount = assets.filter((a) => (a.risk_score ?? 0) >= 40).length;
  const healthyCount = assets.filter((a) => a.risk_score != null && a.risk_score < 20).length;

  const spotlightAssets = assets.slice(0, 6);

  return (
    <div className="min-h-screen bg-[#F4F7FA] text-slate-800">
      {/* 1. Hero Section */}
      <section className="relative -mt-[88px] pt-[88px] bg-[#0B3B63] overflow-hidden text-white border-b border-[#0D4E7A]">
        {/* Real Infrastructure Image Background with Dark Blue Overlay */}
        <div className="absolute inset-0 z-0">
          <img
            src="/images/simras-landing-hero.png"
            alt="Andhra Pradesh Civil Infrastructure"
            className="w-full h-full object-cover object-center  opacity-100 brightness-100 object-cover object-center"
            onError={(e) => {
              // fallback image if local asset URL requires external mirror
              (e.target as HTMLImageElement).src =
                "https://images.unsplash.com/photo-1541888946425-d0fbb186f5f8?auto=format&fit=crop&w=2000&q=80";
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#082946]/95 via-[#0B3B63]/85 to-[#0D4E7A]/75" />
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-3xl">
            {/* Government Authority Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#16689A]/80 border border-sky-300/30 text-sky-200 text-xs font-semibold uppercase tracking-wider mb-6">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>State Critical Infrastructure Directorate</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
              SIMRAS
            </h1>
            <p className="text-lg sm:text-xl font-medium text-sky-200 mt-2 tracking-wide">
              Smart Infrastructure Monitoring & Risk Assistance System
            </p>

            {/* Mission Statement */}
            <p className="text-2xl sm:text-3xl font-bold text-white mt-6 leading-snug">
              Safer Infrastructure. Stronger Communities.
            </p>

            {/* Sub-tagline */}
            <p className="text-sm sm:text-base text-slate-300 mt-2 font-medium">
              Monitor • Assess • Maintain • Build a Resilient India
            </p>

            {/* Key Pillars Checklist */}
            <div className="mt-8 flex flex-wrap gap-4 text-xs font-medium text-sky-100">
              <span className="flex items-center gap-1.5 bg-[#0D4E7A]/60 px-3 py-1.5 rounded-md border border-sky-400/20">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Live Hydrology & SCADA Telemetry
              </span>
              <span className="flex items-center gap-1.5 bg-[#0D4E7A]/60 px-3 py-1.5 rounded-md border border-sky-400/20">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                3D Parametric Digital Twins
              </span>
              <span className="flex items-center gap-1.5 bg-[#0D4E7A]/60 px-3 py-1.5 rounded-md border border-sky-400/20">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Calibrated RUL & Multi-Criteria Risk
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Four Large Navigation Cards */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 -mt-8 relative z-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: GIS Command */}
          <div
            onClick={() => (onNavigateToGIS ? onNavigateToGIS() : onNavigate?.("GIS"))}
            className="group bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-md hover:shadow-lg hover:border-[#1268A8] transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-11 h-11 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[#1268A8] mb-4 group-hover:bg-[#1268A8] group-hover:text-white transition">
                <MapPin className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 group-hover:text-[#1268A8] transition">
                GIS Command
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Spatial map view across 26 Andhra Pradesh districts. Filter dams, barrages, bridges, airports, and heritage structures.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-[#1268A8]">
              <span>Open Map Command</span>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
            </div>
          </div>

          {/* Card 2: Digital Twin */}
          <div
            onClick={() => (onNavigateToTwin ? onNavigateToTwin(spotlightAssets[0] || assets[0]) : onNavigate?.("TWIN"))}
            className="group bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-md hover:shadow-lg hover:border-[#1268A8] transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-11 h-11 rounded-lg bg-cyan-50 border border-cyan-100 flex items-center justify-center text-[#18A8D8] mb-4 group-hover:bg-[#18A8D8] group-hover:text-white transition">
                <Box className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 group-hover:text-[#1268A8] transition">
                Digital Twin
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Parametric 3D structural engineering models with real-time SCADA telemetry, strain sensors, and hydraulic gate controls.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-[#1268A8]">
              <span>Explore 3D Models</span>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
            </div>
          </div>

          {/* Card 3: Reports */}
          <div
            onClick={() => (onNavigateToReports ? onNavigateToReports((spotlightAssets[0] || assets[0])?.asset_code || "") : onNavigate?.("REPORTS"))}
            className="group bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-md hover:shadow-lg hover:border-[#1268A8] transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-11 h-11 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 mb-4 group-hover:bg-emerald-600 group-hover:text-white transition">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 group-hover:text-[#1268A8] transition">
                Reports
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Statutory civil dossiers, NBI-compatible bridge scorecards, hydrologic audit records, and exportable PDF/CSV data.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-[#1268A8]">
              <span>Access Dossiers</span>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
            </div>
          </div>

          {/* Card 4: Officer Login */}
          <div
            onClick={() => (onOpenOfficerPortal ? onOpenOfficerPortal() : onNavigate?.("OFFICER"))}
            className="group bg-white rounded-lg border border-[#D8E2EA] p-5 shadow-md hover:shadow-lg hover:border-[#1268A8] transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-11 h-11 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 mb-4 group-hover:bg-[#0B3B63] group-hover:text-white transition">
                <Shield className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 group-hover:text-[#1268A8] transition">
                Officer Login
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Secure access for APWRD Executive Engineers, Inspection Officers, and Disaster Management Reviewers to log audits.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-[#1268A8]">
              <span>Enter Secure Portal</span>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
            </div>
          </div>
        </div>
      </section>

      {/* 3. Dynamic Summary from Real Backend Values */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="bg-white rounded-lg border border-[#D8E2EA] p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-slate-100 gap-2">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                State Infrastructure Health Summary
              </h2>
              <p className="text-xs text-slate-500">
                Live statistics computed directly from the Government of Andhra Pradesh Asset Registry
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
              Active Telemetry Sync
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Total Assets
              </span>
              <div className="text-3xl font-bold text-[#0B3B63]">{totalAssets}</div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                100% Georeferenced
              </span>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Infrastructure Categories
              </span>
              <div className="text-3xl font-bold text-[#1268A8]">
                {categories.length || 5}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Dams, Barrages, Bridges, Airports, Temples
              </span>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                District Coverage
              </span>
              <div className="text-3xl font-bold text-slate-800">
                {districts.length || 26}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Across Andhra Pradesh
              </span>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Monitoring Status
              </span>
              <div className="text-3xl font-bold text-emerald-600">24 / 7</div>
              <span className="text-[11px] text-emerald-700 font-medium mt-1 block">
                Automated SCADA & Sensor Grid
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Critical Infrastructure Watchlist (Real Backend Assets) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-16">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              Monitored State Assets
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Select any infrastructure asset to inspect digital twin telemetry and structural safety reports
            </p>
          </div>
          <button
            onClick={() => (onNavigateToGIS ? onNavigateToGIS() : onNavigate?.("GIS"))}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1268A8] hover:text-[#0B3B63] transition"
          >
            <span>View All On Map</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {spotlightAssets.map((asset) => {
            const riskVal = asset.risk_score;
            const healthVal = asset.health_score;
            return (
              <div
                key={asset.asset_code}
                onClick={() => {
                  if (onSelectAsset) onSelectAsset(asset);
                  if (onNavigateToTwin) onNavigateToTwin(asset);
                  else if (onNavigate) onNavigate("TWIN");
                }}
                className="bg-white rounded-lg border border-[#D8E2EA] hover:border-[#1268A8] hover:shadow-md transition-all cursor-pointer overflow-hidden flex flex-col justify-between"
              >
                <div className="p-5">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <span className="text-[11px] font-mono font-bold text-[#1268A8] px-2 py-0.5 bg-blue-50 rounded border border-blue-200">
                      {asset.asset_code}
                    </span>
                    <StatusBadge
                      status={riskVal == null ? "MODEL_PENDING" : riskVal >= 50
                          ? "HIGH_RISK"
                          : riskVal >= 30
                          ? "MEDIUM_RISK"
                          : "HEALTHY"
                      }
                    />
                  </div>

                  <h3 className="text-base font-bold text-slate-900 truncate">
                    {asset.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    {asset.district} • <span className="capitalize">{asset.category || asset.type}</span>
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block">
                        Health Score
                      </span>
                      <span className="text-lg font-bold text-slate-800">
                        {healthVal?.toFixed(0) ?? "Unavailable"}
                        <span className="text-xs font-normal text-slate-400">/100</span>
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 block">
                        Risk Level
                      </span>
                      <span
                        className={`text-lg font-bold ${
                          riskVal >= 50
                            ? "text-red-600"
                            : riskVal >= 30
                            ? "text-amber-600"
                            : "text-emerald-600"
                        }`}
                      >
                        {riskVal == null ? "Unavailable" : riskVal >= 50 ? "High" : riskVal >= 30 ? "Medium" : "Low"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-[#1268A8]">
                  <span>Open Digital Twin</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Footer Notice */}
      <footer className="bg-[#082946] text-slate-400 text-xs py-8 border-t border-[#0B3B63]">
      </footer>
      {/* SIMRAS_PUBLIC_FOOTER_V1 */}
      <section className="mt-12 border-t border-slate-200 bg-white">

        <footer className="text-slate-200" style={{ backgroundImage: 'linear-gradient(rgba(3, 28, 42, 0.86), rgba(3, 28, 42, 0.92)), url("/simras-resilient-india-banner.png")', backgroundSize: "cover", backgroundPosition: "center", backgroundRepeat: "no-repeat" }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            <div>
              <h2 className="text-white font-bold text-lg">SIMRAS</h2>
              <p className="text-sm text-slate-300 mt-2 leading-6">
                Smart Infrastructure Monitoring &amp; Risk Assistance System for evidence-aware infrastructure monitoring, digital twins and decision support.
              </p>
              <p className="text-xs text-slate-400 mt-4">
                SIMRAS does not replace statutory inspection, certification or directions issued by a competent authority.
              </p>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-3">About &amp; Public Information</h3>
              <div className="space-y-2 text-sm">
                <a className="block hover:text-white" href="/about.html">About SIMRAS</a>
                <a className="block hover:text-white" href="/data-sources.html">Government Sources</a>
                <a className="block hover:text-white" href="/accessibility.html">Accessibility</a>
                <a className="block hover:text-white" href="/contact.html">Contact &amp; Feedback</a>
                <a className="block hover:text-white" href="/sitemap.html">Sitemap</a>
              </div>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-3">Policies</h3>
              <div className="space-y-2 text-sm">
                <a className="block hover:text-white" href="/terms.html">Terms &amp; Conditions</a>
                <a className="block hover:text-white" href="/privacy.html">Privacy Policy</a>
                <a className="block hover:text-white" href="/disclaimer.html">Disclaimer</a>
              </div>
            </div>

            <div>
              <h3 className="text-white font-semibold mb-3">Official Source Links</h3>
              <div className="space-y-2 text-sm">
                <a className="block hover:text-white" href="https://www.ap.gov.in/" target="_blank" rel="noopener noreferrer">Government of Andhra Pradesh</a>
                <a className="block hover:text-white" href="https://irrigation.ap.gov.in/" target="_blank" rel="noopener noreferrer">AP Water Resources / Irrigation</a>
                <a className="block hover:text-white" href="https://cwc.gov.in/" target="_blank" rel="noopener noreferrer">Central Water Commission</a>
                <a className="block hover:text-white" href="https://indiawris.gov.in/" target="_blank" rel="noopener noreferrer">India-WRIS</a>
                <a className="block hover:text-white" href="https://mausam.imd.gov.in/" target="_blank" rel="noopener noreferrer">India Meteorological Department</a>
                <a className="block hover:text-white" href="https://www.aai.aero/" target="_blank" rel="noopener noreferrer">Airports Authority of India</a>
              </div>
            </div>
          </div>

          <div className="border-t border-white/10">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2 text-xs text-slate-400">
              <span>SIMRAS - Infrastructure monitoring and decision-support portal</span>
              <span>Government-source links are provided for traceability; source ownership remains with the respective authority.</span>
            </div>
          </div>
        </footer>
      </section>
    </div>
  );
}



