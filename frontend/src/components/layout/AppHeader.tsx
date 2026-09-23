import React, { useState } from "react";
import { useSelectedAsset } from "../../context/AssetContext";
import {
  Activity,
  Box,
  Building2,
  ChevronDown,
  Database,
  FileCheck2,
  FileText,
  Layers,
  MapPin,
  Shield,
  Sparkles,
  UserCheck,
} from "lucide-react";

export type AppModule =
  | "DASHBOARD"
  | "GIS"
  | "REGISTRY"
  | "ENGINEERING"
  | "TWIN"
  | "AI"
  | "EVIDENCE"
  | "INSPECTIONS"
  | "REPORTS"
  | "OFFICER";

interface AppHeaderProps {
  activeModule: AppModule;
  onSelectModule: (module: AppModule) => void;
}

export function AppHeader({ activeModule, onSelectModule }: AppHeaderProps) {
  const { assets, selected, selectedCode, setSelectedCode } = useSelectedAsset();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const modules: Array<{ id: AppModule; label: string; icon: React.ComponentType<{ className?: string }> }> = [
    { id: "DASHBOARD", label: "Dashboard", icon: Activity },
    { id: "GIS", label: "GIS Command", icon: MapPin },
    { id: "REGISTRY", label: "Asset Registry", icon: Building2 },
    { id: "ENGINEERING", label: "Engineering", icon: Layers },
    { id: "TWIN", label: "Digital Twin 3D", icon: Box },
    { id: "AI", label: "AI Assessment", icon: Sparkles },
    { id: "EVIDENCE", label: "Government Evidence", icon: Database },
    { id: "INSPECTIONS", label: "Inspections", icon: FileCheck2 },
    { id: "REPORTS", label: "Reports", icon: FileText },
    { id: "OFFICER", label: "Officer Portal", icon: UserCheck },
  ];

  return (
    <header className="simras-header">
      {/* Top Banner Row */}
      <div className="header-top-row">
        <div className="brand-container">
          <div className="brand-badge">S</div>
          <div>
            <div className="brand-title">SIMRAS</div>
            <div className="brand-subtitle">
              Smart Infrastructure Monitoring & Risk Assessment System · Andhra Pradesh
            </div>
          </div>
        </div>

        {/* Global Active Asset Pill & Selector */}
        <div className="active-asset-container">
          <div className="relative">
            <button
              type="button"
              className="active-asset-pill"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              title="Click to switch active asset across all modules"
            >
              <span className="pill-dot" />
              <div className="pill-info">
                <span className="pill-code">{selected?.asset_code || "SELECT ASSET"}</span>
                <span className="pill-name">{selected?.name || "No asset chosen"}</span>
              </div>
              <span className="pill-type">{selected?.asset_type || "asset"}</span>
              <span
                className={`pill-risk ${
                  selected?.risk_level === "HIGH"
                    ? "risk-high"
                    : selected?.risk_level === "MEDIUM"
                    ? "risk-medium"
                    : "risk-low"
                }`}
              >
                {selected?.risk_score != null ? `${selected.risk_score.toFixed(1)} Risk` : "LOW RISK"}
              </span>
              <ChevronDown className="size-4 opacity-70" />
            </button>

            {dropdownOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
                <div className="asset-dropdown-menu">
                  <div className="dropdown-header">Select Monitored Asset (Updates All Views)</div>
                  <div className="dropdown-list">
                    {assets.map((asset) => (
                      <button
                        key={asset.asset_code}
                        type="button"
                        className={`dropdown-item ${asset.asset_code === selectedCode ? "active" : ""}`}
                        onClick={() => {
                          setSelectedCode(asset.asset_code);
                          setDropdownOpen(false);
                        }}
                      >
                        <div className="item-main">
                          <span className="item-name">{asset.name}</span>
                          <span className="item-code">{asset.asset_code} · {asset.district || "AP"}</span>
                        </div>
                        <span className="item-badge">{asset.asset_type}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="auth-status-pill">
            <Shield className="size-3.5 text-emerald-400" />
            <span>Govt Verified Ledger</span>
          </div>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <nav className="header-nav">
        {modules.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`nav-tab ${activeModule === id ? "active" : ""}`}
            onClick={() => onSelectModule(id)}
          >
            <Icon className="size-4" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </header>
  );
}
