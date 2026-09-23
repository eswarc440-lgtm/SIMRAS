import React, { useState, useEffect } from "react";
import {
  Activity,
  Droplets,
  Wind,
  CloudRain,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Radio,
  Eye,
  PlusCircle,
  CheckCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  MapPin,
  Shield,
  Layers,
} from "lucide-react";
import type { TelemetryFeedRecord, StructuralSensor, CitizenHazardObservationRecord } from "../../types/twin";

interface Props {
  telemetry: TelemetryFeedRecord | null;
  observations: CitizenHazardObservationRecord[];
  onSync: () => Promise<void>;
  onSimulate: (patch: Partial<TelemetryFeedRecord>) => Promise<void>;
  onOpenReportModal: () => void;
  onSelectSensor: (sensor: StructuralSensor) => void;
  onSelectObservation: (obs: CitizenHazardObservationRecord) => void;
  syncing: boolean;
  weatherEffectsEnabled: boolean;
  onToggleWeather: () => void;
  sensorPinsVisible: boolean;
  onToggleSensorPins: () => void;
  inline?: boolean;
}

export function LiveTelemetryHUD({
  telemetry,
  observations,
  onSync,
  onSimulate,
  onOpenReportModal,
  onSelectSensor,
  onSelectObservation,
  syncing,
  weatherEffectsEnabled,
  onToggleWeather,
  sensorPinsVisible,
  onToggleSensorPins,
  inline = false,
}: Props) {
  const [activeTab, setActiveTab] = useState<"LIVE" | "SENSORS" | "OBSERVATIONS" | "SIMULATE">("LIVE");
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Safe fallback weather object to ensure no unhandled property access
  const weather = telemetry?.weather ?? {
    condition: "OVERCAST" as const,
    precipitation_mm_hr: 0,
    wind_speed_kmh: 14,
    temperature_c: 28,
  };

  // Simulation sliders state
  const [simWaterLevel, setSimWaterLevel] = useState<number>(telemetry?.water_level_m ?? 17.45);
  const [simInflow, setSimInflow] = useState<number>(telemetry?.inflow_cusecs ?? 385000);
  const [simGatesOpen, setSimGatesOpen] = useState<number>(telemetry?.gates_open ?? 48);
  const [simWeather, setSimWeather] = useState<TelemetryFeedRecord["weather"]["condition"]>(
    telemetry?.weather?.condition ?? "MONSOON_STORM"
  );

  // Sync simulation sliders whenever telemetry feed is updated
  useEffect(() => {
    if (telemetry) {
      if (typeof telemetry.water_level_m === "number") setSimWaterLevel(telemetry.water_level_m);
      if (typeof telemetry.inflow_cusecs === "number") setSimInflow(telemetry.inflow_cusecs);
      if (typeof telemetry.gates_open === "number") setSimGatesOpen(telemetry.gates_open);
      if (telemetry.weather?.condition) setSimWeather(telemetry.weather.condition);
    }
  }, [telemetry]);

  if (!telemetry) {
    return (
      <div
        className={
          inline
            ? "w-full rounded-xl border border-gray-800 bg-[#0b1a2a] p-4 text-xs text-gray-400"
            : "absolute top-4 right-4 z-30 bg-slate-950/90 border border-gray-800 rounded-xl p-3 text-xs text-gray-400"
        }
      >
        Connecting to public portal telemetry stream...
      </div>
    );
  }

  const handleApplySim = () => {
    const totalGates = telemetry.total_gates || 70;
    const maxWater = telemetry.max_water_level_m || 18;
    const storagePct = Math.min(100, Math.max(10, (simWaterLevel / maxWater) * 100));

    onSimulate({
      water_level_m: simWaterLevel,
      storage_percent: Number(storagePct.toFixed(1)),
      inflow_cusecs: simInflow,
      outflow_cusecs: simGatesOpen > 0 ? Math.round(simInflow * 0.96) : 0,
      gates_open: simGatesOpen,
      gate_clearance_m: simGatesOpen > 0 ? Number(((simGatesOpen / totalGates) * 3.5).toFixed(1)) : 0,
      weather: {
        condition: simWeather,
        precipitation_mm_hr: simWeather === "MONSOON_STORM" ? 32 : simWeather === "RAIN" ? 14 : 0,
        wind_speed_kmh: simWeather === "MONSOON_STORM" ? 48 : 16,
        temperature_c: weather.temperature_c ?? 28,
      },
    });
  };

  const isAlertLevel = (telemetry.storage_percent ?? 0) >= 90;

  return (
    <div
      className={
        inline
          ? "w-full rounded-xl border border-gray-800 bg-[#0b1a2a] shadow-xl text-gray-100 overflow-hidden flex flex-col transition-all"
          : "absolute top-4 right-4 z-30 w-80 md:w-96 rounded-2xl border border-cyan-500/30 bg-[#081524]/95 shadow-2xl backdrop-blur-md text-gray-100 overflow-hidden flex flex-col transition-all max-h-[85vh]"
      }
    >
      {/* Top Telemetry Header */}
      <div className="p-3 bg-[#0d2035] border-b border-cyan-500/20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          </div>
          <div>
            <div className="text-[10px] font-black uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
              <span>Public Portal & IoT Ingestion</span>
              <span className="px-1.5 py-0.2 rounded bg-cyan-950 border border-cyan-400/40 text-[9px] text-cyan-200">
                LIVE
              </span>
            </div>
            <div className="text-[9px] text-gray-400 truncate max-w-[200px]">
              WRIS · CWC · IMD · AP Real-Time Grid
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onSync}
            disabled={syncing}
            className="p-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/30 text-cyan-300 transition"
            title="Ingest Latest Telemetry from Portals"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg bg-gray-800/60 hover:bg-gray-700 text-gray-300 transition"
          >
            {isCollapsed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Sub Tabs */}
          <div className="grid grid-cols-4 bg-[#0a1829] border-b border-gray-800 text-[10px] font-semibold">
            <button
              onClick={() => setActiveTab("LIVE")}
              className={`py-2 text-center transition ${
                activeTab === "LIVE"
                  ? "bg-cyan-950/60 text-cyan-300 border-b-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Telemetry
            </button>
            <button
              onClick={() => setActiveTab("SENSORS")}
              className={`py-2 text-center transition flex items-center justify-center gap-1 ${
                activeTab === "SENSORS"
                  ? "bg-cyan-950/60 text-cyan-300 border-b-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <span>Sensors</span>
              <span className="w-4 h-4 rounded-full bg-cyan-900 text-cyan-300 text-[9px] flex items-center justify-center">
                {telemetry.structural_sensors?.length ?? 0}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("OBSERVATIONS")}
              className={`py-2 text-center transition flex items-center justify-center gap-1 ${
                activeTab === "OBSERVATIONS"
                  ? "bg-cyan-950/60 text-cyan-300 border-b-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <span>Public Pins</span>
              <span className="w-4 h-4 rounded-full bg-amber-900 text-amber-300 text-[9px] flex items-center justify-center">
                {observations?.length ?? 0}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("SIMULATE")}
              className={`py-2 text-center transition ${
                activeTab === "SIMULATE"
                  ? "bg-cyan-950/60 text-cyan-300 border-b-2 border-cyan-400"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Simulator
            </button>
          </div>

          {/* View Tab Body */}
          <div className={`p-4 space-y-3.5 ${inline ? "overflow-visible" : "overflow-y-auto max-h-[50vh]"}`}>
            {activeTab === "LIVE" && (
              <div className="space-y-3 text-xs">
                {/* Water Level / FRL Bar */}
                <div className="rounded-xl bg-[#0e2238] border border-gray-800 p-3 space-y-1.5 shadow-inner">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-gray-400 flex items-center gap-1">
                      <Droplets className="w-3.5 h-3.5 text-cyan-400" />
                      Reservoir Water Level
                    </span>
                    <span className={`font-mono font-bold ${isAlertLevel ? "text-amber-400" : "text-cyan-300"}`}>
                      {telemetry.water_level_m} m / {telemetry.max_water_level_m} m
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-700 ${
                        telemetry.storage_percent > 95
                          ? "bg-red-500"
                          : telemetry.storage_percent > 85
                          ? "bg-amber-400"
                          : "bg-cyan-500"
                      }`}
                      style={{ width: `${Math.min(100, telemetry.storage_percent)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-gray-400 pt-0.5">
                    <span>Current Storage: <strong className="text-white">{telemetry.storage_percent}% FRL</strong></span>
                    {telemetry.storage_tmc && <span>{telemetry.storage_tmc} TMC Gross</span>}
                  </div>
                </div>

                {/* Inflow / Outflow & Gates */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl bg-[#0e2238] border border-gray-800 p-2.5">
                    <span className="text-[10px] text-gray-400 block">Upstream Inflow</span>
                    <div className="text-sm font-bold text-white font-mono mt-0.5">
                      {(telemetry.inflow_cusecs ?? 0).toLocaleString()}
                      <span className="text-[9px] font-normal text-gray-400 ml-0.5">cusecs</span>
                    </div>
                  </div>

                  <div className="rounded-xl bg-[#0e2238] border border-gray-800 p-2.5">
                    <span className="text-[10px] text-gray-400 block">Spillway Discharge</span>
                    <div className="text-sm font-bold text-cyan-300 font-mono mt-0.5">
                      {(telemetry.outflow_cusecs ?? 0).toLocaleString()}
                      <span className="text-[9px] font-normal text-gray-400 ml-0.5">cusecs</span>
                    </div>
                  </div>
                </div>

                {/* Gates Status */}
                {telemetry.total_gates > 0 && (
                  <div className="rounded-xl bg-[#0e2238] border border-gray-800 p-2.5 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-gray-400 block">Spillway Crest Gates</span>
                      <span className="text-xs font-bold text-white font-mono">
                        {telemetry.gates_open} of {telemetry.total_gates} Gates Raised
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-gray-400 block">Clearance</span>
                      <span className="text-xs font-bold text-cyan-300 font-mono">
                        {telemetry.gate_clearance_m} m
                      </span>
                    </div>
                  </div>
                )}

                {/* Weather Doppler Radar */}
                <div className="rounded-xl bg-[#0e2238] border border-gray-800 p-2.5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CloudRain className="w-4 h-4 text-cyan-400" />
                    <div>
                      <span className="text-[10px] text-gray-400 block">IMD Doppler Weather</span>
                      <span className="text-xs font-bold text-white uppercase">
                        {(weather.condition || "CLEAR").replace("_", " ")}
                      </span>
                    </div>
                  </div>
                  <div className="text-right text-[10px] text-gray-300">
                    <div>{weather.precipitation_mm_hr ?? 0} mm/hr rain</div>
                    <div className="text-gray-400">{weather.wind_speed_kmh ?? 12} km/h wind</div>
                  </div>
                </div>

                {/* Quick Toggle Controls for 3D View */}
                <div className="pt-1 flex items-center justify-between text-[11px] border-t border-gray-800">
                  <button
                    onClick={onToggleWeather}
                    className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
                      weatherEffectsEnabled
                        ? "bg-cyan-950 border-cyan-500/50 text-cyan-300"
                        : "bg-[#0b1b2d] border-gray-800 text-gray-400"
                    }`}
                  >
                    🌧️ 3D Rain & Sky: {weatherEffectsEnabled ? "ON" : "OFF"}
                  </button>

                  <button
                    onClick={onToggleSensorPins}
                    className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
                      sensorPinsVisible
                        ? "bg-cyan-950 border-cyan-500/50 text-cyan-300"
                        : "bg-[#0b1b2d] border-gray-800 text-gray-400"
                    }`}
                  >
                    📍 3D Sensor Pins: {sensorPinsVisible ? "ON" : "OFF"}
                  </button>
                </div>
              </div>
            )}

            {activeTab === "SENSORS" && (
              <div className="space-y-2 text-xs">
                <div className="text-[10px] text-gray-400">
                  Click any sensor to focus its location on the 3D structure:
                </div>
                {(telemetry.structural_sensors ?? []).map((sensor) => (
                  <div
                    key={sensor.id}
                    onClick={() => onSelectSensor(sensor)}
                    className="p-2.5 rounded-xl bg-[#0e2238] hover:bg-[#122b46] border border-gray-800 hover:border-cyan-500/40 cursor-pointer transition flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-cyan-400 font-bold text-[10px]">{sensor.id}</span>
                        <span className="font-semibold text-white truncate max-w-[170px]">{sensor.name}</span>
                      </div>
                      <span className="text-[9px] text-gray-400 block mt-0.5">Type: {sensor.type}</span>
                    </div>

                    <div className="text-right">
                      <div className="font-mono font-bold text-white">
                        {sensor.value} {sensor.unit}
                      </div>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.2 rounded inline-block mt-0.5 ${
                          sensor.status === "CRITICAL"
                            ? "bg-red-950 text-red-300 border border-red-500/40"
                            : sensor.status === "WARNING"
                            ? "bg-amber-950 text-amber-300 border border-amber-500/40"
                            : "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                        }`}
                      >
                        {sensor.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "OBSERVATIONS" && (
              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-gray-400">Citizen Observations Pinned:</span>
                  <button
                    onClick={onOpenReportModal}
                    className="text-[10px] font-bold px-2 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 flex items-center gap-1 transition"
                  >
                    <PlusCircle className="w-3 h-3" />
                    Submit New
                  </button>
                </div>

                {(observations?.length ?? 0) === 0 ? (
                  <div className="text-center py-6 text-gray-500 text-xs">
                    No active hazard reports pinned to this structure.
                  </div>
                ) : (
                  (observations ?? []).map((obs) => (
                    <div
                      key={obs.id}
                      onClick={() => onSelectObservation(obs)}
                      className="p-2.5 rounded-xl bg-[#0e2238] hover:bg-[#122b46] border border-amber-500/30 hover:border-amber-400 cursor-pointer transition space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-amber-400 font-bold text-[10px]">{obs.id}</span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                            obs.severity === "CRITICAL" || obs.severity === "HIGH"
                              ? "bg-red-950 text-red-300 border border-red-500/40"
                              : "bg-amber-950 text-amber-300 border border-amber-500/40"
                          }`}
                        >
                          {obs.severity} SEVERITY
                        </span>
                      </div>
                      <div className="text-white font-medium text-[11px] truncate">
                        {obs.observation_type.replace("_", " ")}
                      </div>
                      <p className="text-[10px] text-gray-300 line-clamp-2 leading-relaxed">
                        {obs.description}
                      </p>
                      <div className="flex items-center justify-between text-[9px] text-gray-400 pt-1 border-t border-gray-800">
                        <span>By: {obs.reporter_name}</span>
                        {obs.verified_by_officer ? (
                          <span className="text-emerald-400 flex items-center gap-0.5">
                            <CheckCircle className="w-2.5 h-2.5" /> Verified
                          </span>
                        ) : (
                          <span className="text-amber-400">Pending Field Audit</span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "SIMULATE" && (
              <div className="space-y-3 text-xs">
                <div className="p-2 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-[10px] text-cyan-200">
                  Adjust parameters below to test flood hydrodynamics and gate clearance states in the 3D model:
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-gray-300">Water Level (RL m):</span>
                    <span className="font-mono text-cyan-300 font-bold">{simWaterLevel} m</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max={Math.max(30, (telemetry.max_water_level_m || 20) * 1.2)}
                    step="0.1"
                    value={simWaterLevel}
                    onChange={(e) => setSimWaterLevel(parseFloat(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-gray-300">Flood Inflow (cusecs):</span>
                    <span className="font-mono text-cyan-300 font-bold">{simInflow.toLocaleString()}</span>
                  </div>
                  <input
                    type="range"
                    min="10000"
                    max="600000"
                    step="10000"
                    value={simInflow}
                    onChange={(e) => setSimInflow(parseInt(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-gray-300">Gates Raised:</span>
                    <span className="font-mono text-cyan-300 font-bold">{simGatesOpen} / {telemetry.total_gates}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={telemetry.total_gates || 70}
                    step="1"
                    value={simGatesOpen}
                    onChange={(e) => setSimGatesOpen(parseInt(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                </div>

                <div className="space-y-1">
                  <span className="text-[11px] text-gray-300 block">Weather Scenario:</span>
                  <select
                    value={simWeather}
                    onChange={(e) => setSimWeather(e.target.value as any)}
                    className="w-full rounded-lg border border-gray-700 bg-[#0e2236] px-2.5 py-1.5 text-xs text-white focus:border-cyan-400 focus:outline-none"
                  >
                    <option value="CLEAR">Clear Daylight</option>
                    <option value="OVERCAST">Overcast Monsoon Cloud Cover</option>
                    <option value="RAIN">Active Rainfall (14 mm/h)</option>
                    <option value="MONSOON_STORM">Extreme Cyclone/Monsoon Storm (32 mm/h)</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleApplySim}
                  className="w-full py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-cyan-600/30 transition mt-2"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  Apply Physical Dynamics to 3D Twin
                </button>
              </div>
            )}
          </div>

          {/* Bottom Action Footer */}
          <div className="p-3 bg-[#0a1829] border-t border-gray-800 flex items-center justify-between text-xs">
            <span className="text-[10px] text-gray-400 truncate">
              Last Ingestion: {telemetry.last_sync ? new Date(telemetry.last_sync).toLocaleTimeString() : "Live Stream"}
            </span>
            <button
              onClick={onOpenReportModal}
              className="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 flex items-center gap-1 transition"
            >
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              Report Hazard Pin
            </button>
          </div>
        </>
      )}
    </div>
  );
}
