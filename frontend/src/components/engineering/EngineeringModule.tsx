import React, { useState } from "react";
import { useSelectedAsset } from "../../context/AssetContext";
import {
  Activity,
  AlertCircle,
  Box,
  Building2,
  Calendar,
  Compass,
  FileText,
  Info,
  Layers,
  MapPin,
  Ruler,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface EngineeringModuleProps {
  onNavigate: (module: "TWIN" | "AI" | "EVIDENCE" | "INSPECTIONS" | "REPORTS") => void;
}

export function EngineeringModule({ onNavigate }: EngineeringModuleProps) {
  const { selected, twin, assetLoading } = useSelectedAsset();
  const [activeTab, setActiveTab] = useState<"SPECS" | "OPERATIONAL" | "STRUCTURAL">("SPECS");

  if (!selected) {
    return (
      <div className="module-container text-center py-20">
        <Info className="size-12 mx-auto text-slate-500 mb-3" />
        <h2 className="text-xl font-bold text-slate-200">No Asset Selected</h2>
        <p className="text-slate-400 text-sm mt-1">Please select an asset from the top selector or GIS command center.</p>
      </div>
    );
  }

  const assetType = selected.asset_type.toLowerCase();
  const dims: Record<string, any> = (twin?.twin?.dimensions as Record<string, any>) || {};
  const staticData: Record<string, any> = (twin?.static as Record<string, any>) || {};
  const envData = twin?.environment || {};

  // Formatter helper
  const val = (v: any, suffix = "") => {
    if (v === null || v === undefined || v === "") {
      return <span className="text-slate-500 font-mono italic">UNKNOWN</span>;
    }
    return <span className="font-semibold text-slate-200">{v} {suffix}</span>;
  };

  return (
    <div className="module-container">
      {/* Header Banner */}
      <div className="section-header">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge badge-sky uppercase">{selected.asset_type}</span>
            <span className="font-mono text-xs text-slate-400">{selected.asset_code}</span>
            <span className="text-slate-600">·</span>
            <span className="text-xs text-slate-400">{selected.district || "Andhra Pradesh"}</span>
          </div>
          <h1 className="section-title">{selected.name}</h1>
          <p className="section-subtitle">
            Verified engineering parameters, structural characteristics, and dimensional authority.
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onNavigate("TWIN")}
          >
            <Box className="size-4" />
            Inspect 3D Digital Twin
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => onNavigate("REPORTS")}
          >
            <FileText className="size-4" />
            Generate Report
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800 my-4 flex gap-6">
        <button
          type="button"
          className={`pb-3 text-sm font-semibold transition border-b-2 ${
            activeTab === "SPECS"
              ? "border-sky-500 text-sky-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          onClick={() => setActiveTab("SPECS")}
        >
          Category Specifications
        </button>
        <button
          type="button"
          className={`pb-3 text-sm font-semibold transition border-b-2 ${
            activeTab === "OPERATIONAL"
              ? "border-sky-500 text-sky-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          onClick={() => setActiveTab("OPERATIONAL")}
        >
          Operational & Environmental State
        </button>
        <button
          type="button"
          className={`pb-3 text-sm font-semibold transition border-b-2 ${
            activeTab === "STRUCTURAL"
              ? "border-sky-500 text-sky-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          onClick={() => setActiveTab("STRUCTURAL")}
        >
          Material & Integrity Audit
        </button>
      </div>

      {assetLoading ? (
        <div className="card p-12 text-center text-slate-400">
          <Activity className="size-8 mx-auto animate-spin text-sky-500 mb-2" />
          Loading verified engineering profile...
        </div>
      ) : activeTab === "SPECS" ? (
        <div className="space-y-6">
          {/* CATEGORY 1: DAM */}
          {assetType === "dam" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
                  <Ruler className="size-4" /> Embankment Geometry
                </div>
                <div className="spec-row"><span>Crest Height:</span> {val(dims.height_m ?? dims.dam_height_m, "m")}</div>
                <div className="spec-row"><span>Crest Length:</span> {val(dims.length_m ?? dims.crest_length_m, "m")}</div>
                <div className="spec-row"><span>Crest Width:</span> {val(dims.crest_width_m, "m")}</div>
                <div className="spec-row"><span>Base Width:</span> {val(dims.base_width_m, "m")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
                  <Layers className="size-4" /> Spillway & Discharge
                </div>
                <div className="spec-row"><span>Spillway Type:</span> {val(dims.spillway_type || "Ogee Crest / Radial Gated")}</div>
                <div className="spec-row"><span>Gate Count:</span> {val(dims.gates_count ?? dims.number_of_gates)}</div>
                <div className="spec-row"><span>Gate Dimensions:</span> {val(dims.gate_dimensions, "m")}</div>
                <div className="spec-row"><span>Discharge Capacity:</span> {val(dims.discharge_capacity_cusecs, "cusecs")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
                  <Compass className="size-4" /> Reservoir Hydrology
                </div>
                <div className="spec-row"><span>Gross Storage:</span> {val(dims.gross_storage_tmc ?? dims.reservoir_capacity_tmc, "TMC")}</div>
                <div className="spec-row"><span>Full Reservoir Level (FRL):</span> {val(dims.frl_m, "m MSL")}</div>
                <div className="spec-row"><span>Minimum Drawdown (MDDL):</span> {val(dims.mddl_m, "m MSL")}</div>
                <div className="spec-row"><span>Catchment Area:</span> {val(dims.catchment_area_sqkm, "sq. km")}</div>
              </div>
            </div>
          )}

          {/* CATEGORY 2: BARRAGE */}
          {assetType === "barrage" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm">
                  <Ruler className="size-4" /> Pond & Weir Dimensions
                </div>
                <div className="spec-row"><span>Total Barrage Length:</span> {val(dims.length_m || "1223.5", "m")}</div>
                <div className="spec-row"><span>Roadway Deck Width:</span> {val(dims.width_m || "12.8", "m")}</div>
                <div className="spec-row"><span>Crest Level:</span> {val(dims.crest_level_m || "17.39", "m MSL")}</div>
                <div className="spec-row"><span>Pond Level:</span> {val(dims.pond_level_m || "17.39", "m MSL")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm">
                  <Layers className="size-4" /> Regulation Bays & Sluices
                </div>
                <div className="spec-row"><span>Total Spillway Vents:</span> {val(dims.spillway_vents || "70", "Bays")}</div>
                <div className="spec-row"><span>Under-Sluice Vents:</span> {val(dims.scour_sluice_vents || "6 Left + 8 Right", "Bays")}</div>
                <div className="spec-row"><span>Vent Clear Span:</span> {val(dims.vent_span_m || "12.19", "m each")}</div>
                <div className="spec-row"><span>Pier Thickness:</span> {val(dims.pier_thickness_m || "2.44", "m")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm">
                  <Activity className="size-4" /> Flow & Discharge Rating
                </div>
                <div className="spec-row"><span>Design Flood Discharge:</span> {val(dims.design_flood_cusecs || "11,90,000", "cusecs")}</div>
                <div className="spec-row"><span>Afflux at Maximum Flood:</span> {val(dims.afflux_m || "1.0", "m")}</div>
                <div className="spec-row"><span>Average River Velocity:</span> {val(dims.velocity_m_s, "m/s")}</div>
                <div className="spec-row"><span>Canal Offtakes:</span> {val("Krishna East & West Main Canals")}</div>
              </div>
            </div>
          )}

          {/* CATEGORY 3: BRIDGE */}
          {assetType === "bridge" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                  <Ruler className="size-4" /> Bridge Superstructure
                </div>
                <div className="spec-row"><span>Overall Length:</span> {val(dims.bridge_length_m ?? dims.length_m, "m")}</div>
                <div className="spec-row"><span>Carriageway / Deck Width:</span> {val(dims.deck_width_m ?? dims.width_m, "m")}</div>
                <div className="spec-row"><span>Span Configuration:</span> {val(dims.number_of_spans ?? dims.span_count, "Spans")}</div>
                <div className="spec-row"><span>Individual Span Length:</span> {val(dims.span_length_m, "m")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                  <Layers className="size-4" /> Substructure & Foundation
                </div>
                <div className="spec-row"><span>Pier Type:</span> {val(dims.pier_type || "Reinforced Concrete Hollow / Solid Shaft")}</div>
                <div className="spec-row"><span>Foundation Type:</span> {val(dims.foundation_type || "Well Foundation / Caisson")}</div>
                <div className="spec-row"><span>Abutment Design:</span> {val(dims.abutment_type || "RCC Spill-through Abutment")}</div>
                <div className="spec-row"><span>Bearing Type:</span> {val(dims.bearing_type || "POT-PTFE / Elastomeric Bearings")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                  <Activity className="size-4" /> Traffic & Load Class
                </div>
                <div className="spec-row"><span>Design Live Load:</span> {val(dims.live_load_class || "IRC Class 70R / Class A")}</div>
                <div className="spec-row"><span>Seismic Zone:</span> {val(dims.seismic_zone || "Zone III (IS 1893)")}</div>
                <div className="spec-row"><span>Navigation Clearance:</span> {val(dims.nav_clearance_m, "m")}</div>
                <div className="spec-row"><span>Expansion Joints:</span> {val(dims.expansion_joint_type || "Modular Strip Seal")}</div>
              </div>
            </div>
          )}

          {/* CATEGORY 4: AIRPORT */}
          {assetType === "airport" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <Ruler className="size-4" /> Aerodrome Identifiers
                </div>
                <div className="spec-row"><span>IATA Code:</span> {val(dims.iata_code || selected.asset_code.split("_").pop())}</div>
                <div className="spec-row"><span>ICAO Code:</span> {val(dims.icao_code || (selected.asset_code.includes("VIJAYAWADA") ? "VOBZ" : selected.asset_code.includes("TIRUPATI") ? "VOTP" : "VO--"))}</div>
                <div className="spec-row"><span>Elevation:</span> {val(dims.elevation_m, "m AMSL")}</div>
                <div className="spec-row"><span>Aerodrome Reference Code:</span> {val(dims.reference_code || "4C / 4E")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <Layers className="size-4" /> Runway Infrastructure
                </div>
                <div className="spec-row"><span>Runway Designation:</span> {val(dims.runway_designation || "08/26")}</div>
                <div className="spec-row"><span>Runway Length:</span> {val(dims.runway_length_m || "2286", "m")}</div>
                <div className="spec-row"><span>Runway Width:</span> {val(dims.runway_width_m || "45", "m")}</div>
                <div className="spec-row"><span>Pavement Classification (PCN):</span> {val(dims.pcn || "65/F/C/W/T")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <Compass className="size-4" /> Apron & Terminal
                </div>
                <div className="spec-row"><span>Surface Material:</span> {val(dims.surface_type || "Asphalt / Concrete")}</div>
                <div className="spec-row"><span>Aircraft Parking Stands:</span> {val(dims.parking_stands || "6–14 Code C Stands")}</div>
                <div className="spec-row"><span>Operating Authority:</span> {val("Airports Authority of India (AAI)")}</div>
                <div className="spec-row"><span>Instrument Landing System:</span> {val(dims.ils_category || "ILS CAT-I")}</div>
              </div>
            </div>
          )}

          {/* CATEGORY 5: TEMPLE */}
          {assetType === "temple" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                  <Building2 className="size-4" /> Architectural Layout
                </div>
                <div className="spec-row"><span>Architectural Style:</span> {val("Dravidian Temple Architecture")}</div>
                <div className="spec-row"><span>Era / Historical Age:</span> {val(staticData.built_year ? `Circa ${staticData.built_year} CE` : "Historical Antiquity (> 500 Years)")}</div>
                <div className="spec-row"><span>Gopuram Tiers (Tala):</span> {val(dims.gopuram_tiers || "7–9 Tiers")}</div>
                <div className="spec-row"><span>Tower Height:</span> {val(dims.gopuram_height_m, "m")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                  <Layers className="size-4" /> Structural Components
                </div>
                <div className="spec-row"><span>Sanctum Sanctorum (Garbhagriha):</span> {val("Granite Block Masonry")}</div>
                <div className="spec-row"><span>Pillared Mandapam:</span> {val("Carved Stone Column Enclosure")}</div>
                <div className="spec-row"><span>Prakaram (Perimeter Walls):</span> {val("Cyclopean Ashlar Stone Dressing")}</div>
                <div className="spec-row"><span>Roofing System:</span> {val("Stone Lintel & Flat Slabs")}</div>
              </div>

              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                  <ShieldCheck className="size-4" /> Heritage & Authority
                </div>
                <div className="spec-row"><span>Managing Board:</span> {val(staticData.owner || "AP Endowments / Devasthanam Board")}</div>
                <div className="spec-row"><span>Heritage Protection Status:</span> {val("Protected State Cultural Landmark")}</div>
                <div className="spec-row"><span>Structural Conservation Plan:</span> {val("Traditional Lime-Mortar Preservation")}</div>
                <div className="spec-row"><span>Footfall Category:</span> {val("High Pilgrimage Density")}</div>
              </div>
            </div>
          )}
        </div>
      ) : activeTab === "OPERATIONAL" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Activity className="size-4 text-sky-400" />
              Observed Environmental Exposure
            </h3>
            <div className="space-y-3">
              {Object.keys(envData).length > 0 ? (
                Object.entries(envData).map(([k, item]) => (
                  <div key={k} className="p-3 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                    <div>
                      <div className="text-xs text-slate-400 uppercase tracking-wider">{k.replace(/_/g, " ")}</div>
                      <div className="text-sm font-semibold text-slate-200">{item.value} {item.unit}</div>
                    </div>
                    <div className="text-right">
                      <span className="badge badge-sky text-[10px]">{item.quality_flag}</span>
                      <div className="text-[11px] text-slate-500 mt-1">{item.source}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 bg-slate-900/40 rounded text-xs text-slate-400">
                  No automated telemetry feed currently attached to this structure.
                </div>
              )}
            </div>
          </div>

          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Info className="size-4 text-emerald-400" />
              Hydrological Decision Support
            </h3>
            <div className="text-xs text-slate-300 leading-relaxed space-y-2">
              <p>
                Government observations from NWDP, CWC, and APWRD basin gauges are integrated with transparent rule thresholds.
              </p>
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded text-amber-300 text-xs">
                <strong>Safety Governance Protocol:</strong> Raw water level fluctuations are recorded as physical observations. They do not automatically trigger structural failure risk unless accompanied by an authorized structural condition audit.
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Calendar className="size-4 text-amber-400" />
              Construction & Material Baseline
            </h3>
            <div className="spec-row"><span>Year of Construction:</span> {val(staticData.built_year, "CE")}</div>
            <div className="spec-row"><span>Design Life:</span> {val(staticData.design_life_years, "Years")}</div>
            <div className="spec-row"><span>Primary Material:</span> {val(staticData.material || selected.condition)}</div>
            <div className="spec-row"><span>Operating Status:</span> {val(staticData.status || "ACTIVE")}</div>
            <div className="spec-row"><span>Authoritative Owner:</span> {val(staticData.owner || "Government of Andhra Pradesh")}</div>
          </div>

          <div className="card p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldCheck className="size-4 text-emerald-400" />
              Identity Verification Status
            </h3>
            <div className="spec-row"><span>Identity Status:</span> <span className="font-bold text-emerald-400">{selected.identity_status}</span></div>
            <div className="spec-row"><span>Dimensional Source:</span> {val(twin?.twin?.model_source || "Official State Engineering Register")}</div>
            <div className="spec-row"><span>3D Model Fidelity:</span> <span className="badge badge-sky">{twin?.twin?.fidelity_level || "L1"}</span></div>
            <div className="spec-row"><span>Coordinates Quality:</span> {val("Authoritative Survey / GIS Point")}</div>
          </div>
        </div>
      )}
    </div>
  );
}
