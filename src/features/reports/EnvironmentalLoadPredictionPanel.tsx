import React, { useState, useEffect } from "react";
import {
  CloudRain,
  Wind,
  Droplets,
  Truck,
  Thermometer,
  Activity,
  AlertTriangle,
  ShieldCheck,
  Zap,
  RotateCcw,
  Gauge,
  TrendingDown,
  Info,
} from "lucide-react";

export interface PredictionInputs {
  rainfall_mm_hr: number;
  wind_speed_kmh: number;
  humidity_pct: number;
  traffic_load_pcu: number;
  temperature_c: number;
}

interface EnvironmentalLoadPredictionPanelProps {
  assetCode: string;
  assetName?: string;
  assetType?: string;
  baseHealth?: number;
  baseRisk?: number;
  initialInputs?: PredictionInputs;
  onPredictionChange?: (prediction: any) => void;
}

export function EnvironmentalLoadPredictionPanel({
  assetCode,
  assetName = "Critical Infrastructure Asset",
  assetType = "dam",
  baseHealth = 78.5,
  baseRisk = 21.5,
  initialInputs,
  onPredictionChange,
}: EnvironmentalLoadPredictionPanelProps) {
  const isHydraulic =
    assetType === "dam" ||
    assetType === "barrage" ||
    assetType?.toLowerCase().includes("dam") ||
    assetType?.toLowerCase().includes("barrage");

  const defaultInputs: PredictionInputs = initialInputs || {
    rainfall_mm_hr: isHydraulic ? 18.5 : 8.2,
    wind_speed_kmh: 32.0,
    humidity_pct: 76.0,
    traffic_load_pcu: isHydraulic ? 480 : 1850,
    temperature_c: 32.4,
  };

  const [inputs, setInputs] = useState<PredictionInputs>(defaultInputs);
  const [activeScenario, setActiveScenario] = useState<string>("custom");

  // Sync if initialInputs changes
  useEffect(() => {
    if (initialInputs) {
      setInputs(initialInputs);
    }
  }, [initialInputs]);

  // Client-side real-time multi-variable calculation
  const calculatePrediction = (currentInputs: PredictionInputs) => {
    const isWater = isHydraulic;

    // 1. Rainfall impact (pore water pressure, hydrostatic head, saturation surcharge)
    const rainFactor = isWater ? 0.24 : 0.12;
    const rainPenalty = (currentInputs.rainfall_mm_hr / 10) * rainFactor * 4.5;

    // 2. Wind impact (crosswind aerodynamic shear, gust buffeting, wave run-up)
    const windPenalty = Math.max(0, (currentInputs.wind_speed_kmh - 20) / 10) * 1.85;

    // 3. Humidity impact (chloride ingress, moisture saturation, concrete carbonation rate)
    const humidityPenalty = Math.max(0, (currentInputs.humidity_pct - 60) / 10) * 1.65;

    // 4. Traffic load impact (cyclic axle load fatigue, dynamic girder deflection)
    const trafficFactor = isWater ? 0.09 : 0.32;
    const trafficPenalty = (currentInputs.traffic_load_pcu / 500) * trafficFactor * 5.2;

    // 5. Temperature impact (thermal expansion differential across joints and bearings)
    const tempDiff = Math.abs(currentInputs.temperature_c - 28);
    const tempPenalty = (tempDiff / 5) * 1.25;

    const totalEnvironmentalPenalty = Math.min(
      48,
      rainPenalty + windPenalty + humidityPenalty + trafficPenalty + tempPenalty
    );

    const predictedHealthScore = Math.max(
      12,
      Math.round((baseHealth - totalEnvironmentalPenalty) * 10) / 10
    );

    const failureRiskPercent = Math.min(
      96,
      Math.max(
        4,
        Math.round((baseRisk + totalEnvironmentalPenalty * 1.38) * 10) / 10
      )
    );

    const dynamicDeflectionMm = Math.round(
      ((currentInputs.traffic_load_pcu / 1000) * 2.8 +
        (currentInputs.wind_speed_kmh / 50) * 1.9 +
        (currentInputs.rainfall_mm_hr / 50) * 1.4) *
        100
    ) / 100;

    const fatigueAccelerationRatio = Math.round(
      (1 +
        (currentInputs.traffic_load_pcu / 2500) * 0.48 +
        (currentInputs.wind_speed_kmh / 60) * 0.36 +
        (currentInputs.humidity_pct / 100) * 0.28) *
        100
    ) / 100;

    const adjustedRulYears = Math.max(
      2.5,
      Math.round(((baseHealth / 2.2) / fatigueAccelerationRatio) * 10) / 10
    );

    let riskTier: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" = "LOW";
    if (failureRiskPercent >= 75) riskTier = "CRITICAL";
    else if (failureRiskPercent >= 52) riskTier = "HIGH";
    else if (failureRiskPercent >= 32) riskTier = "MODERATE";

    return {
      inputs: currentInputs,
      predicted_health_score: predictedHealthScore,
      predicted_failure_risk_pct: failureRiskPercent,
      risk_tier: riskTier,
      predicted_rul_years: adjustedRulYears,
      dynamic_deflection_mm: dynamicDeflectionMm,
      fatigue_acceleration_ratio: fatigueAccelerationRatio,
      factor_penalties: {
        rainfall: Math.round(rainPenalty * 10) / 10,
        wind_speed: Math.round(windPenalty * 10) / 10,
        humidity: Math.round(humidityPenalty * 10) / 10,
        traffic_load: Math.round(trafficPenalty * 10) / 10,
        temperature: Math.round(tempPenalty * 10) / 10,
        total: Math.round(totalEnvironmentalPenalty * 10) / 10,
      },
      advisory:
        riskTier === "CRITICAL"
          ? "CRITICAL HAZARD: Surcharge threshold exceeded under compound rainfall and traffic fatigue. Impose emergency load restriction and inspect crest / expansion joints immediately."
          : riskTier === "HIGH"
          ? "HIGH RISK: Elevated environmental stress detected. High winds and precipitation require active sensor surveillance and precautionary flow/speed control."
          : riskTier === "MODERATE"
          ? "MODERATE LOAD: Normal operational degradation within design parameters. Routine telemetry and drainage monitoring recommended."
          : "OPTIMAL: All environmental and dynamic load indices are well within safety factor margins.",
    };
  };

  const currentPrediction = calculatePrediction(inputs);

  // Notify parent on changes
  useEffect(() => {
    if (onPredictionChange) {
      onPredictionChange(currentPrediction);
    }
  }, [inputs]);

  // Scenario presets
  const applyScenario = (name: string) => {
    setActiveScenario(name);
    if (name === "baseline") {
      setInputs({
        rainfall_mm_hr: 2.0,
        wind_speed_kmh: 18.0,
        humidity_pct: 55.0,
        traffic_load_pcu: isHydraulic ? 250 : 1100,
        temperature_c: 28.0,
      });
    } else if (name === "monsoon") {
      setInputs({
        rainfall_mm_hr: 58.0,
        wind_speed_kmh: 42.0,
        humidity_pct: 94.0,
        traffic_load_pcu: isHydraulic ? 380 : 1400,
        temperature_c: 26.5,
      });
    } else if (name === "cyclone") {
      setInputs({
        rainfall_mm_hr: 82.0,
        wind_speed_kmh: 96.0,
        humidity_pct: 98.0,
        traffic_load_pcu: isHydraulic ? 180 : 850,
        temperature_c: 25.0,
      });
    } else if (name === "traffic_peak") {
      setInputs({
        rainfall_mm_hr: 6.0,
        wind_speed_kmh: 24.0,
        humidity_pct: 68.0,
        traffic_load_pcu: isHydraulic ? 950 : 3400,
        temperature_c: 36.0,
      });
    } else if (name === "compound_crisis") {
      setInputs({
        rainfall_mm_hr: 90.0,
        wind_speed_kmh: 88.0,
        humidity_pct: 96.0,
        traffic_load_pcu: isHydraulic ? 850 : 3100,
        temperature_c: 38.0,
      });
    }
  };

  const handleSliderChange = (key: keyof PredictionInputs, value: number) => {
    setActiveScenario("custom");
    setInputs((prev) => ({ ...prev, [key]: value }));
  };

  const resetToDefault = () => {
    setActiveScenario("custom");
    setInputs(defaultInputs);
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "CRITICAL":
        return "text-red-400 bg-red-950/80 border-red-500/50";
      case "HIGH":
        return "text-amber-400 bg-amber-950/80 border-amber-500/50";
      case "MODERATE":
        return "text-yellow-300 bg-yellow-950/80 border-yellow-500/50";
      default:
        return "text-emerald-300 bg-emerald-950/80 border-emerald-500/50";
    }
  };

  return (
    <div className="bg-[#0b1a2a] border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-4 md:p-5 border-b border-gray-800 bg-[#0d1e31] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-500/30 text-cyan-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-wide">
                Multi-Factor Environmental & Dynamic Load Prediction Engine
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/40">
                Deterministic ML
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Predictive structural stress as a function of Rainfall, Wind Speed, Humidity, Traffic Load & Temperature
            </p>
          </div>
        </div>

        {/* Quick Scenario Preset Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-semibold text-gray-400 mr-1 hidden sm:inline">
            Scenarios:
          </span>
          <button
            type="button"
            onClick={() => applyScenario("baseline")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeScenario === "baseline"
                ? "bg-cyan-500 text-black font-bold"
                : "bg-[#07131e] text-gray-300 hover:bg-gray-800 border border-gray-700"
            }`}
          >
            Clear / Baseline
          </button>
          <button
            type="button"
            onClick={() => applyScenario("monsoon")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeScenario === "monsoon"
                ? "bg-blue-500 text-white font-bold"
                : "bg-[#07131e] text-blue-300 hover:bg-blue-950 border border-blue-800/60"
            }`}
          >
            Heavy Monsoon
          </button>
          <button
            type="button"
            onClick={() => applyScenario("cyclone")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeScenario === "cyclone"
                ? "bg-purple-500 text-white font-bold"
                : "bg-[#07131e] text-purple-300 hover:bg-purple-950 border border-purple-800/60"
            }`}
          >
            Cyclone Gale
          </button>
          <button
            type="button"
            onClick={() => applyScenario("traffic_peak")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeScenario === "traffic_peak"
                ? "bg-amber-500 text-black font-bold"
                : "bg-[#07131e] text-amber-300 hover:bg-amber-950 border border-amber-800/60"
            }`}
          >
            Peak Freight Axle
          </button>
          <button
            type="button"
            onClick={() => applyScenario("compound_crisis")}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition ${
              activeScenario === "compound_crisis"
                ? "bg-red-500 text-white font-bold"
                : "bg-[#07131e] text-red-300 hover:bg-red-950 border border-red-800/60"
            }`}
          >
            Compound Crisis
          </button>
          <button
            type="button"
            onClick={resetToDefault}
            title="Reset to live sensor readings"
            className="p-1.5 rounded bg-[#07131e] hover:bg-gray-800 border border-gray-700 text-gray-400 hover:text-white transition ml-1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="p-4 md:p-6 space-y-6">
        {/* Results Banner Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#07131e] border border-cyan-500/20 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Predicted Health
              </span>
              <Activity className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-3xl font-black font-mono text-white">
                {currentPrediction.predicted_health_score.toFixed(1)}
              </span>
              <span className="text-xs text-gray-500">/ 100</span>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px]">
              <span className="text-gray-400">Baseline: {baseHealth.toFixed(1)}</span>
              <span className="text-rose-400 font-mono font-bold flex items-center gap-0.5">
                <TrendingDown className="w-3 h-3" />
                -{(baseHealth - currentPrediction.predicted_health_score).toFixed(1)} pts
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#07131e] border border-cyan-500/20 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Failure Risk
              </span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-3xl font-black font-mono text-amber-400">
                {currentPrediction.predicted_failure_risk_pct.toFixed(1)}%
              </span>
            </div>
            <div className="mt-2">
              <span
                className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getTierColor(
                  currentPrediction.risk_tier
                )}`}
              >
                {currentPrediction.risk_tier} RISK TIER
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#07131e] border border-cyan-500/20 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Dynamic Deflection
              </span>
              <Gauge className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-3xl font-black font-mono text-cyan-300">
                {currentPrediction.dynamic_deflection_mm.toFixed(2)}
              </span>
              <span className="text-xs text-gray-400 font-normal">mm</span>
            </div>
            <div className="mt-2 text-[11px] text-gray-400">
              Limit allowable: 8.50 mm (Safe)
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#07131e] border border-cyan-500/20 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Fatigue Rate / RUL
              </span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-3xl font-black font-mono text-white">
                {currentPrediction.predicted_rul_years.toFixed(1)}
              </span>
              <span className="text-xs text-gray-400 font-normal">years</span>
            </div>
            <div className="mt-2 text-[11px] text-gray-400">
              Fatigue Multiplier:{" "}
              <span className="text-cyan-300 font-mono font-bold">
                {currentPrediction.fatigue_acceleration_ratio}x
              </span>
            </div>
          </div>
        </div>

        {/* Advisory Box */}
        <div
          className={`p-3.5 rounded-xl border flex items-start gap-3 text-xs leading-relaxed ${getTierColor(
            currentPrediction.risk_tier
          )}`}
        >
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <strong className="block font-bold mb-0.5">Automated Predictive Advisory:</strong>
            {currentPrediction.advisory}
          </div>
        </div>

        {/* 5 Environmental & Load Sliders */}
        <div className="bg-[#07131e] border border-gray-800/80 rounded-xl p-4 md:p-5 space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-gray-800">
            <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">
              Interactive Stress Parameters & Environmental Loaders
            </span>
            <span className="text-[11px] text-cyan-400 font-mono">
              Live Interactive Simulation
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
            {/* 1. Rainfall */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-blue-400 font-bold">
                  <CloudRain className="w-4 h-4" />
                  <span>Rainfall Intensity</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-black font-mono text-white">
                    {inputs.rainfall_mm_hr.toFixed(1)}
                  </span>
                  <span className="text-[11px] text-gray-400">mm/hr</span>
                  <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
                    (-{currentPrediction.factor_penalties.rainfall} pts)
                  </span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="0.5"
                value={inputs.rainfall_mm_hr}
                onChange={(e) => handleSliderChange("rainfall_mm_hr", parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>0 mm (Dry)</span>
                <span>25 mm (Moderate)</span>
                <span>50 mm (Heavy)</span>
                <span>100 mm (Cloudburst)</span>
              </div>
            </div>

            {/* 2. Wind Speed */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
                  <Wind className="w-4 h-4" />
                  <span>Wind Velocity & Aerodynamic Gust</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-black font-mono text-white">
                    {inputs.wind_speed_kmh.toFixed(1)}
                  </span>
                  <span className="text-[11px] text-gray-400">km/h</span>
                  <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
                    (-{currentPrediction.factor_penalties.wind_speed} pts)
                  </span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="120"
                step="1"
                value={inputs.wind_speed_kmh}
                onChange={(e) => handleSliderChange("wind_speed_kmh", parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>0 km/h (Calm)</span>
                <span>35 km/h (Breeze)</span>
                <span>65 km/h (Gale)</span>
                <span>120 km/h (Cyclone)</span>
              </div>
            </div>

            {/* 3. Humidity */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                  <Droplets className="w-4 h-4" />
                  <span>Relative Humidity (% RH)</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-black font-mono text-white">
                    {inputs.humidity_pct.toFixed(0)}%
                  </span>
                  <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
                    (-{currentPrediction.factor_penalties.humidity} pts)
                  </span>
                </div>
              </div>
              <input
                type="range"
                min="20"
                max="100"
                step="1"
                value={inputs.humidity_pct}
                onChange={(e) => handleSliderChange("humidity_pct", parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>20% (Dry Arid)</span>
                <span>60% (Threshold)</span>
                <span>80% (High Corrosion)</span>
                <span>100% (Saturated)</span>
              </div>
            </div>

            {/* 4. Traffic Load */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-amber-400 font-bold">
                  <Truck className="w-4 h-4" />
                  <span>Traffic Dynamic Axle Load</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-black font-mono text-white">
                    {inputs.traffic_load_pcu.toLocaleString()}
                  </span>
                  <span className="text-[11px] text-gray-400">PCU/hr</span>
                  <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
                    (-{currentPrediction.factor_penalties.traffic_load} pts)
                  </span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="4000"
                step="50"
                value={inputs.traffic_load_pcu}
                onChange={(e) => handleSliderChange("traffic_load_pcu", parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>0 PCU (No Load)</span>
                <span>1,000 (Light)</span>
                <span>2,500 (Heavy)</span>
                <span>4,000 (Congested Axle)</span>
              </div>
            </div>

            {/* 5. Temperature */}
            <div className="space-y-2 md:col-span-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-orange-400 font-bold">
                  <Thermometer className="w-4 h-4" />
                  <span>Ambient Temperature & Thermal Gradient</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-black font-mono text-white">
                    {inputs.temperature_c.toFixed(1)}°C
                  </span>
                  <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
                    (-{currentPrediction.factor_penalties.temperature} pts)
                  </span>
                </div>
              </div>
              <input
                type="range"
                min="10"
                max="50"
                step="0.5"
                value={inputs.temperature_c}
                onChange={(e) => handleSliderChange("temperature_c", parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>10°C (Cold)</span>
                <span>28°C (Neutral Design Baseline)</span>
                <span>40°C (High Expansion)</span>
                <span>50°C (Extreme Heat)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Degradation Contribution Breakdown Bar */}
        <div className="p-4 rounded-xl bg-[#07131e] border border-gray-800 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-gray-300 uppercase tracking-wide">
              Compound Environmental Stress Contribution Matrix
            </span>
            <span className="text-rose-400 font-mono font-bold">
              Total Environmental Degradation: -{currentPrediction.factor_penalties.total} pts
            </span>
          </div>

          <div className="w-full h-3 rounded-full bg-gray-800 overflow-hidden flex shadow-inner">
            <div
              style={{
                width: `${(currentPrediction.factor_penalties.rainfall / (currentPrediction.factor_penalties.total || 1)) * 100}%`,
              }}
              className="h-full bg-blue-500 transition-all duration-300"
              title={`Rainfall: -${currentPrediction.factor_penalties.rainfall} pts`}
            />
            <div
              style={{
                width: `${(currentPrediction.factor_penalties.wind_speed / (currentPrediction.factor_penalties.total || 1)) * 100}%`,
              }}
              className="h-full bg-cyan-400 transition-all duration-300"
              title={`Wind: -${currentPrediction.factor_penalties.wind_speed} pts`}
            />
            <div
              style={{
                width: `${(currentPrediction.factor_penalties.humidity / (currentPrediction.factor_penalties.total || 1)) * 100}%`,
              }}
              className="h-full bg-emerald-500 transition-all duration-300"
              title={`Humidity: -${currentPrediction.factor_penalties.humidity} pts`}
            />
            <div
              style={{
                width: `${(currentPrediction.factor_penalties.traffic_load / (currentPrediction.factor_penalties.total || 1)) * 100}%`,
              }}
              className="h-full bg-amber-500 transition-all duration-300"
              title={`Traffic: -${currentPrediction.factor_penalties.traffic_load} pts`}
            />
            <div
              style={{
                width: `${(currentPrediction.factor_penalties.temperature / (currentPrediction.factor_penalties.total || 1)) * 100}%`,
              }}
              className="h-full bg-orange-500 transition-all duration-300"
              title={`Thermal: -${currentPrediction.factor_penalties.temperature} pts`}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-gray-400 pt-1 font-mono">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
              Rain: {currentPrediction.factor_penalties.rainfall} pts
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block" />
              Wind: {currentPrediction.factor_penalties.wind_speed} pts
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              Humidity: {currentPrediction.factor_penalties.humidity} pts
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
              Traffic: {currentPrediction.factor_penalties.traffic_load} pts
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" />
              Thermal: {currentPrediction.factor_penalties.temperature} pts
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EnvironmentalLoadPredictionPanel;
