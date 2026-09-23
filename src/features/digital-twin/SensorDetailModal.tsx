import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  X,
  MapPin,
  Clock,
  Shield,
  Layers,
  Wrench,
  TrendingUp,
} from "lucide-react";
import type { StructuralSensor, CitizenHazardObservationRecord } from "../../types/twin";

interface Props {
  sensor: StructuralSensor | null;
  observation: CitizenHazardObservationRecord | null;
  onClose: () => void;
  onObservationVerified?: (updated: CitizenHazardObservationRecord) => void;
}

export function SensorDetailModal({
  sensor,
  observation,
  onClose,
  onObservationVerified,
}: Props) {
  const [verifying, setVerifying] = useState(false);

  if (!sensor && !observation) return null;

  const handleVerifyObservation = async () => {
    if (!observation) return;
    setVerifying(true);
    try {
      const res = await fetch(`/api/v1/observations/${observation.id}/verify`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verified: true }),
      });
      if (res.ok) {
        const updated = await res.json();
        onObservationVerified?.(updated);
      }
    } catch (e) {
      console.error("Verification failed:", e);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-cyan-500/30 bg-[#081728] shadow-2xl p-5 text-gray-100 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
        >
          <X className="w-4 h-4" />
        </button>

        {sensor && (
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <span className="font-mono text-cyan-400 font-bold text-xs">{sensor.id}</span>
                <h3 className="text-base font-bold text-white">{sensor.name}</h3>
                <span className="text-xs text-gray-400">Structural Health Monitoring (SHM) Telemetry</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[#0d2238] border border-gray-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-gray-400 block uppercase">Real-Time Reading</span>
                <div className="text-2xl font-black font-mono text-white mt-0.5">
                  {sensor.value} <span className="text-sm font-normal text-cyan-300">{sensor.unit}</span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-gray-400 block uppercase">Alert Threshold</span>
                <div className="text-sm font-bold font-mono text-gray-300 mt-0.5">
                  &gt; {sensor.threshold} {sensor.unit}
                </div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded inline-block mt-1 ${
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

            <div className="space-y-2 text-xs text-gray-300">
              <div className="flex justify-between py-1 border-b border-gray-800">
                <span className="text-gray-400">Sensor Class</span>
                <span className="font-semibold text-white">{sensor.type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-800">
                <span className="text-gray-400">3D Position Relative to Datum</span>
                <span className="font-mono text-cyan-300">
                  [{sensor.position[0]}, {sensor.position[1]}, {sensor.position[2]}]
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-800">
                <span className="text-gray-400">Data Acquisition Frequency</span>
                <span className="text-white">1 Hz (Continuous SCADA Polling)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-gray-400">Ingestion Authority</span>
                <span className="text-white">Andhra Pradesh Dam Safety Organisation (DSO)</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-xs transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        )}

        {observation && (
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <span className="font-mono text-amber-400 font-bold text-xs">{observation.id}</span>
                <h3 className="text-base font-bold text-white">
                  {observation.observation_type.replace("_", " ")}
                </h3>
                <span className="text-xs text-gray-400">Public Portal Citizen Incident Pin</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#0d2238] border border-gray-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Severity Assessment:</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    observation.severity === "CRITICAL" || observation.severity === "HIGH"
                      ? "bg-red-950 text-red-300 border border-red-500/40"
                      : "bg-amber-950 text-amber-300 border border-amber-500/40"
                  }`}
                >
                  {observation.severity} SEVERITY
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Reporter:</span>
                <span className="font-semibold text-white">{observation.reporter_name}</span>
              </div>

              {observation.reporter_phone && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Contact:</span>
                  <span className="font-mono text-cyan-300">{observation.reporter_phone}</span>
                </div>
              )}

              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">Reported At:</span>
                <span className="text-gray-300">{new Date(observation.reported_at).toLocaleString()}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#091a2c] border border-gray-800 text-xs">
              <span className="text-[10px] font-bold text-gray-400 block mb-1 uppercase">Observation Details:</span>
              <p className="text-gray-200 leading-relaxed">{observation.description}</p>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-gray-800">
              <div>
                {observation.verified_by_officer ? (
                  <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    Verified by Field Inspector
                  </span>
                ) : (
                  <span className="text-xs text-amber-400 font-medium">Pending Official Verification</span>
                )}
              </div>

              <div className="flex gap-2">
                {!observation.verified_by_officer && (
                  <button
                    type="button"
                    onClick={handleVerifyObservation}
                    disabled={verifying}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1 transition"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    {verifying ? "Verifying..." : "Verify as Officer"}
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:bg-gray-800 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
