import React from "react";
import { Shield, ExternalLink, User, CheckCircle2, AlertTriangle } from "lucide-react";

export type PublicTab = "home" | "gis" | "twin" | "reports" | "citizen_report" | "HOME" | "GIS" | "TWIN" | "REPORTS";
export type PublicNavTab = PublicTab;

interface PublicHeaderProps {
  currentTab?: PublicTab;
  activeTab?: PublicTab;
  onSelectTab: (tab: any) => void;
  onOpenOfficerPortal?: () => void;
  onOpenOfficerLogin?: () => void;
  onOpenCitizenReport?: () => void;
  selectedAssetCode?: string;
  isLoggedIn?: boolean;
  officerName?: string;
}

export function GovernmentEmblem({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <img src="/images/ap-government-emblem.png" alt="Andhra Pradesh Government Emblem" className={`${className} shrink-0 object-contain`} />
  );
}

export function PublicHeader({
  currentTab,
  activeTab,
  onSelectTab,
  onOpenOfficerPortal,
  onOpenOfficerLogin,
  onOpenCitizenReport,
  selectedAssetCode,
  isLoggedIn,
  officerName,
}: PublicHeaderProps) {
  const active = (activeTab || currentTab || "home").toString().toLowerCase();

  const navItems = [
    { id: "home", label: "Home" },
    { id: "gis", label: "GIS" },
    { id: "twin", label: "Digital Twin" },
    { id: "reports", label: "Reports" },
  ];

  const handleOfficerClick = () => {
    if (onOpenOfficerLogin) onOpenOfficerLogin();
    else if (onOpenOfficerPortal) onOpenOfficerPortal();
  };

  return (
    <header className={`${activeTab === "home" ? "bg-transparent border-0 shadow-none" : "bg-[#0B3B63] border-b border-[#0D4E7A] shadow-md"} text-white sticky top-0 z-40`}>
      {/* Upper sub-bar: Government of Andhra Pradesh Authority notice */}
      <div className={`${activeTab === "home" ? "bg-transparent border-0" : "bg-[#082946] border-b border-[#0B3B63]/60"} px-4 py-1 flex items-center justify-between text-[11px] text-slate-300`}>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sky-200">GOVERNMENT OF ANDHRA PRADESH</span>
          <span className="text-slate-500">•</span>
          <span className="hidden sm:inline">Disaster Management & Infrastructure Asset Authority</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 text-emerald-300 font-medium">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span className="hidden xs:inline">EVIDENCE BACKED</span>
          </span>
          <span className="text-slate-500 hidden sm:inline">•</span>
          <span className="hidden md:inline font-mono text-[10px] text-sky-300/80">AP-SIMRAS v4.2 PROD</span>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left Branding */}
        <div
          onClick={() => onSelectTab("home")}
          className="flex items-center gap-3 cursor-pointer group shrink-0"
        >
          <img src="/images/ap-government-emblem.png" alt="Andhra Pradesh Government Emblem" className="w-10 h-10 shrink-0 object-contain drop-shadow" />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
<span className="text-xl font-bold tracking-wider text-white font-sans">
                SIMRAS
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#16689A] text-sky-100 font-semibold uppercase tracking-wider hidden sm:inline-block">
                Portal
              </span>
            </div>
            <span className="text-[11px] text-slate-300 font-normal leading-tight hidden sm:block">
              Smart Infrastructure Monitoring & Risk Assistance System
            </span>
          </div>
        </div>

        {/* Center Navigation Links */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          {navItems.map((item) => {
            const isItemActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`relative px-3 py-2 text-xs sm:text-sm font-medium transition-colors duration-150 rounded-md ${
                  isItemActive
                    ? "text-white bg-[#0D4E7A] font-semibold shadow-inner"
                    : "text-slate-200 hover:text-white hover:bg-[#0D4E7A]/50"
                }`}
              >
                {item.label}
                {isItemActive && (
                  <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-[#18A8D8] rounded-full" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Right CTA Area: Citizen Hazard Report + Officer Access */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {onOpenCitizenReport && (
            <button
              onClick={onOpenCitizenReport}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 text-amber-200 transition"
              title="Submit Citizen Hazard or Distress Alert"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Report Hazard</span>
            </button>
          )}

          <button
            onClick={handleOfficerClick}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold bg-[#1268A8] hover:bg-[#16689A] border border-[#18A8D8]/40 text-white shadow-sm transition"
          >
            <Shield className="w-3.5 h-3.5 text-sky-300" />
            <span>{isLoggedIn ? (officerName ? `Officer: ${officerName.split(" ")[0]}` : "Officer Portal") : "Officer Login"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}






