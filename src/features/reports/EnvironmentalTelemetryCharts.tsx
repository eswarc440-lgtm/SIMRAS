import React, { useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  CloudRain,
  Wind,
  Droplets,
  Thermometer,
  Truck,
  Activity,
  Calendar,
  Layers,
  Sparkles,
} from "lucide-react";

interface EnvironmentalTelemetryChartsProps {
  timeSeriesData?: any[];
  sevenDayForecast?: any[];
  assetName?: string;
  isHydraulic?: boolean;
}

export function EnvironmentalTelemetryCharts({
  timeSeriesData = [],
  sevenDayForecast = [],
  assetName = "Monitored Asset",
  isHydraulic = true,
}: EnvironmentalTelemetryChartsProps) {
  const [activeTab, setActiveTab] = useState<string>("all");

  // Fallback 24-hour time series if empty
  const defaultTimeSeries = [
    { time: "00:00", rainfall_mm: 3.2, wind_speed_kmh: 18, humidity_pct: 88, temperature_c: 25.5, traffic_pcu: 220, structural_stress_mpa: 13.1, predicted_health: 78.4 },
    { time: "02:00", rainfall_mm: 4.8, wind_speed_kmh: 21, humidity_pct: 90, temperature_c: 24.8, traffic_pcu: 150, structural_stress_mpa: 12.9, predicted_health: 78.6 },
    { time: "04:00", rainfall_mm: 8.5, wind_speed_kmh: 24, humidity_pct: 94, temperature_c: 24.2, traffic_pcu: 180, structural_stress_mpa: 13.4, predicted_health: 78.0 },
    { time: "06:00", rainfall_mm: 12.0, wind_speed_kmh: 28, humidity_pct: 92, temperature_c: 26.0, traffic_pcu: 540, structural_stress_mpa: 14.8, predicted_health: 76.8 },
    { time: "08:00", rainfall_mm: 18.5, wind_speed_kmh: 34, humidity_pct: 85, temperature_c: 28.5, traffic_pcu: 1450, structural_stress_mpa: 18.2, predicted_health: 74.2 },
    { time: "10:00", rainfall_mm: 26.4, wind_speed_kmh: 38, humidity_pct: 80, temperature_c: 31.2, traffic_pcu: 1820, structural_stress_mpa: 19.8, predicted_health: 72.5 },
    { time: "12:00", rainfall_mm: 38.2, wind_speed_kmh: 46, humidity_pct: 76, temperature_c: 33.5, traffic_pcu: 1680, structural_stress_mpa: 21.4, predicted_health: 70.8 },
    { time: "14:00", rainfall_mm: 31.0, wind_speed_kmh: 42, humidity_pct: 72, temperature_c: 34.8, traffic_pcu: 1750, structural_stress_mpa: 20.6, predicted_health: 71.6 },
    { time: "16:00", rainfall_mm: 22.5, wind_speed_kmh: 36, humidity_pct: 78, temperature_c: 33.0, traffic_pcu: 1950, structural_stress_mpa: 21.0, predicted_health: 71.2 },
    { time: "18:00", rainfall_mm: 16.0, wind_speed_kmh: 32, humidity_pct: 82, temperature_c: 30.5, traffic_pcu: 2100, structural_stress_mpa: 20.2, predicted_health: 72.0 },
    { time: "20:00", rainfall_mm: 11.2, wind_speed_kmh: 26, humidity_pct: 86, temperature_c: 28.0, traffic_pcu: 1250, structural_stress_mpa: 16.8, predicted_health: 75.2 },
    { time: "22:00", rainfall_mm: 6.4, wind_speed_kmh: 22, humidity_pct: 89, temperature_c: 26.8, traffic_pcu: 680, structural_stress_mpa: 14.5, predicted_health: 77.1 },
  ];

  const series = timeSeriesData && timeSeriesData.length > 0 ? timeSeriesData : defaultTimeSeries;

  // Custom Chart Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#0b1b2d] border border-cyan-500/40 p-2.5 rounded-lg shadow-xl text-xs space-y-1">
          <p className="font-bold text-cyan-300 font-mono border-b border-gray-700 pb-1 mb-1">
            Time: {label}
          </p>
          {payload.map((entry: any, index: number) => (
            <div key={`item-${index}`} className="flex items-center justify-between gap-3 text-[11px]">
              <span style={{ color: entry.color }} className="font-medium">
                {entry.name}:
              </span>
              <strong className="text-white font-mono">{entry.value}</strong>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-4 md:p-5 border-b border-gray-800 bg-[#0d1e31] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-500/30 text-cyan-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-wide">
                Environmental Telemetry & Structural Stress Graphs
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/40">
                Live Sensor Telemetry
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Continuous 24-hour records: Rainfall, Wind Velocity, Humidity, Temperature & Dynamic Traffic Load
            </p>
          </div>
        </div>

        {/* Chart View Toggle Tabs */}
        <div className="flex flex-wrap items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeTab === "all"
                ? "bg-cyan-500 text-black font-bold"
                : "bg-[#07131e] text-gray-400 hover:text-white border border-gray-800"
            }`}
          >
            All Graphs
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("rain")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "rain"
                ? "bg-blue-500 text-white font-bold"
                : "bg-[#07131e] text-blue-400 hover:text-blue-300 border border-gray-800"
            }`}
          >
            <CloudRain className="w-3 h-3" />
            Rainfall
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("wind")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "wind"
                ? "bg-cyan-400 text-black font-bold"
                : "bg-[#07131e] text-cyan-300 hover:text-cyan-200 border border-gray-800"
            }`}
          >
            <Wind className="w-3 h-3" />
            Wind
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("humidity")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "humidity"
                ? "bg-emerald-500 text-white font-bold"
                : "bg-[#07131e] text-emerald-400 hover:text-emerald-300 border border-gray-800"
            }`}
          >
            <Droplets className="w-3 h-3" />
            Humidity
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("temperature")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "temperature"
                ? "bg-orange-500 text-white font-bold"
                : "bg-[#07131e] text-orange-400 hover:text-orange-300 border border-gray-800"
            }`}
          >
            <Thermometer className="w-3 h-3" />
            Temperature
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("traffic")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "traffic"
                ? "bg-amber-500 text-black font-bold"
                : "bg-[#07131e] text-amber-400 hover:text-amber-300 border border-gray-800"
            }`}
          >
            <Truck className="w-3 h-3" />
            Traffic & Stress
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("forecast")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition flex items-center gap-1 ${
              activeTab === "forecast"
                ? "bg-purple-500 text-white font-bold"
                : "bg-[#07131e] text-purple-400 hover:text-purple-300 border border-gray-800"
            }`}
          >
            <Calendar className="w-3 h-3" />
            7-Day Forecast
          </button>
        </div>
      </div>

      <div className="p-4 md:p-6 space-y-6">
        {/* Graph Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 1. Rainfall Graph */}
          {(activeTab === "all" || activeTab === "rain") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-blue-950/80 text-blue-400">
                    <CloudRain className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Rainfall Precipitation & Hydrologic Inflow
                    </h4>
                    <span className="text-[10px] text-gray-400">Precipitation intensity (mm/hr)</span>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-blue-400 font-bold">
                  Peak: 38.2 mm/hr
                </span>
              </div>

              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis stroke="#6b7280" fontSize={10} tickLine={false} unit=" mm" />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={30} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Heavy Rain (30mm)", fill: "#ef4444", fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="rainfall_mm"
                      name="Rainfall (mm/hr)"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#rainGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 2. Wind Speed Graph */}
          {(activeTab === "all" || activeTab === "wind") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-cyan-950/80 text-cyan-400">
                    <Wind className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Wind Velocity & Aerodynamic Gusts
                    </h4>
                    <span className="text-[10px] text-gray-400">Wind velocity & structural drag (km/h)</span>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-cyan-400 font-bold">
                  Peak: 46.0 km/h
                </span>
              </div>

              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis stroke="#6b7280" fontSize={10} tickLine={false} unit=" km/h" />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={45} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "High Wind Alert (45km/h)", fill: "#f59e0b", fontSize: 10 }} />
                    <Line
                      type="monotone"
                      dataKey="wind_speed_kmh"
                      name="Wind Speed (km/h)"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#06b6d4" }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 3. Humidity Graph */}
          {(activeTab === "all" || activeTab === "humidity") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-emerald-950/80 text-emerald-400">
                    <Droplets className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Relative Atmospheric Humidity & Corrosion Rate
                    </h4>
                    <span className="text-[10px] text-gray-400">Moisture saturation & concrete carbonation (% RH)</span>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-emerald-400 font-bold">
                  Range: 72% - 94%
                </span>
              </div>

              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="humidityGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.7} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis domain={[50, 100]} stroke="#6b7280" fontSize={10} tickLine={false} unit="%" />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={80} stroke="#10b981" strokeDasharray="3 3" label={{ value: "Corrosion Acceleration (>80%)", fill: "#10b981", fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="humidity_pct"
                      name="Humidity (% RH)"
                      stroke="#10b981"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#humidityGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 4. Temperature Graph */}
          {(activeTab === "all" || activeTab === "temperature") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-orange-950/80 text-orange-400">
                    <Thermometer className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Thermal Gradient & Structural Expansion
                    </h4>
                    <span className="text-[10px] text-gray-400">Diurnal temperature cycle (°C)</span>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-orange-400 font-bold">
                  Peak: 34.8°C
                </span>
              </div>

              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis domain={[20, 42]} stroke="#6b7280" fontSize={10} tickLine={false} unit="°C" />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={28} stroke="#9ca3af" strokeDasharray="2 2" label={{ value: "Design Baseline (28°C)", fill: "#9ca3af", fontSize: 10 }} />
                    <Line
                      type="monotone"
                      dataKey="temperature_c"
                      name="Temperature (°C)"
                      stroke="#f97316"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#f97316" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 5. Traffic Load & Structural Stress Graph */}
          {(activeTab === "all" || activeTab === "traffic") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-amber-950/80 text-amber-400">
                    <Truck className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Dynamic Traffic Axle Load vs Structural Stress (MPa)
                    </h4>
                    <span className="text-[10px] text-gray-400">
                      Correlation between vehicular PCU throughput and girder stress
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-amber-400 font-bold">Peak Traffic: 2,100 PCU</span>
                  <span className="text-rose-400 font-bold">Max Stress: 21.4 MPa</span>
                </div>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis yAxisId="left" stroke="#6b7280" fontSize={10} tickLine={false} unit=" PCU" />
                    <YAxis yAxisId="right" orientation="right" domain={[10, 30]} stroke="#f43f5e" fontSize={10} tickLine={false} unit=" MPa" />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                    <Bar yAxisId="left" dataKey="traffic_pcu" name="Traffic Load (PCU/hr)" fill="#f59e0b" radius={[4, 4, 0, 0]} opacity={0.85} />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="structural_stress_mpa"
                      name="Structural Stress (MPa)"
                      stroke="#f43f5e"
                      strokeWidth={3}
                      dot={{ r: 4, fill: "#f43f5e" }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 6. Composite Health Curve */}
          {(activeTab === "all" || activeTab === "traffic") && (
            <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 flex flex-col lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded bg-cyan-950/80 text-cyan-400">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      Composite Environmental Degradation & Health Score Trajectory
                    </h4>
                    <span className="text-[10px] text-gray-400">
                      Real-time health score response to combined weather and traffic surges
                    </span>
                  </div>
                </div>
                <span className="text-[11px] font-mono text-emerald-400 font-bold">
                  Design Safety Margin: Validated
                </span>
              </div>

              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="healthGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                    <YAxis domain={[60, 90]} stroke="#6b7280" fontSize={10} tickLine={false} unit=" pts" />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={70} stroke="#eab308" strokeDasharray="3 3" label={{ value: "Caution Threshold (70 pts)", fill: "#eab308", fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="predicted_health"
                      name="Predicted Health Score"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#healthGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* 7-Day Forward Weather & Load Predictive Projection Table */}
        {(activeTab === "all" || activeTab === "forecast") && (
          <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-purple-400" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  7-Day Forward Environmental Weather & Structural Risk Outlook
                </h4>
              </div>
              <span className="text-[10px] text-purple-300 font-mono">
                Model: ECMWF / IMD High-Resolution Grid Ensemble
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px]">
                    <th className="py-2 px-3">Timeline</th>
                    <th className="py-2 px-3">Condition</th>
                    <th className="py-2 px-3">Rainfall (mm)</th>
                    <th className="py-2 px-3">Wind (km/h)</th>
                    <th className="py-2 px-3">Humidity</th>
                    <th className="py-2 px-3">Temp (°C)</th>
                    <th className="py-2 px-3">Traffic (PCU)</th>
                    <th className="py-2 px-3">Predicted Health</th>
                    <th className="py-2 px-3">Risk Tier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-medium">
                  {(sevenDayForecast.length > 0
                    ? sevenDayForecast
                    : [
                        { day: "Day 1 (Wed)", date: "2026-09-23", forecast_condition: "PARTLY CLOUDY", rainfall_mm: 12.0, wind_speed_kmh: 24, humidity_pct: 72, temperature_c: 32.0, traffic_pcu: 1750, predicted_health_score: 76.5, failure_risk_pct: 23.5, alert_tier: "LOW" },
                        { day: "Day 2 (Thu)", date: "2026-09-24", forecast_condition: "MONSOON SQUALL", rainfall_mm: 64.5, wind_speed_kmh: 50, humidity_pct: 92, temperature_c: 27.5, traffic_pcu: 1550, predicted_health_score: 64.2, failure_risk_pct: 54.0, alert_tier: "HIGH" },
                        { day: "Day 3 (Fri)", date: "2026-09-25", forecast_condition: "HEAVY RAIN", rainfall_mm: 42.0, wind_speed_kmh: 36, humidity_pct: 86, temperature_c: 28.5, traffic_pcu: 1650, predicted_health_score: 69.8, failure_risk_pct: 38.5, alert_tier: "MODERATE" },
                        { day: "Day 4 (Sat)", date: "2026-09-26", forecast_condition: "MODERATE RAIN", rainfall_mm: 22.5, wind_speed_kmh: 28, humidity_pct: 80, temperature_c: 30.0, traffic_pcu: 1950, predicted_health_score: 73.4, failure_risk_pct: 28.0, alert_tier: "LOW" },
                        { day: "Day 5 (Sun)", date: "2026-09-27", forecast_condition: "CLEAR / DRY", rainfall_mm: 4.5, wind_speed_kmh: 18, humidity_pct: 68, temperature_c: 33.5, traffic_pcu: 2150, predicted_health_score: 76.0, failure_risk_pct: 24.0, alert_tier: "LOW" },
                        { day: "Day 6 (Mon)", date: "2026-09-28", forecast_condition: "GUSTY WINDS", rainfall_mm: 8.0, wind_speed_kmh: 44, humidity_pct: 70, temperature_c: 34.0, traffic_pcu: 2350, predicted_health_score: 72.8, failure_risk_pct: 32.5, alert_tier: "MODERATE" },
                        { day: "Day 7 (Tue)", date: "2026-09-29", forecast_condition: "PARTLY CLOUDY", rainfall_mm: 14.0, wind_speed_kmh: 26, humidity_pct: 74, temperature_c: 32.5, traffic_pcu: 1850, predicted_health_score: 75.8, failure_risk_pct: 25.0, alert_tier: "LOW" },
                      ]
                  ).map((fc: any, i: number) => (
                    <tr key={i} className="hover:bg-cyan-950/20 transition">
                      <td className="py-2.5 px-3 font-mono text-cyan-300 font-bold">{fc.day}</td>
                      <td className="py-2.5 px-3 text-white">{fc.forecast_condition}</td>
                      <td className="py-2.5 px-3 font-mono text-blue-400 font-bold">{fc.rainfall_mm} mm</td>
                      <td className="py-2.5 px-3 font-mono text-cyan-300">{fc.wind_speed_kmh} km/h</td>
                      <td className="py-2.5 px-3 font-mono text-emerald-400">{fc.humidity_pct}%</td>
                      <td className="py-2.5 px-3 font-mono text-orange-400">{fc.temperature_c}°C</td>
                      <td className="py-2.5 px-3 font-mono text-amber-300">{fc.traffic_pcu.toLocaleString()}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-white">{fc.predicted_health_score.toFixed(1)}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase border ${
                            fc.alert_tier === "HIGH"
                              ? "bg-amber-950 text-amber-400 border-amber-500/40"
                              : fc.alert_tier === "MODERATE"
                              ? "bg-yellow-950 text-yellow-300 border-yellow-500/40"
                              : "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                          }`}
                        >
                          {fc.alert_tier}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default EnvironmentalTelemetryCharts;
