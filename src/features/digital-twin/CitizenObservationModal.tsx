import React, { useState } from "react";
import { AlertTriangle, X, Send, ShieldAlert, CheckCircle, MapPin, Camera } from "lucide-react";
import type { CitizenHazardObservationRecord } from "../../types/twin";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  assetCode: string;
  assetName: string;
  onSubmitted: (newObservation: CitizenHazardObservationRecord) => void;
}

export function CitizenObservationModal({
  isOpen,
  onClose,
  assetCode,
  assetName,
  onSubmitted,
}: Props) {
  const [reporterName, setReporterName] = useState("");
  const [reporterPhone, setReporterPhone] = useState("");
  const [observationType, setObservationType] = useState<CitizenHazardObservationRecord["observation_type"]>("DEBRIS_JAM");
  const [severity, setSeverity] = useState<CitizenHazardObservationRecord["severity"]>("HIGH");
  const [description, setDescription] = useState("");
  const [componentLocation, setComponentLocation] = useState("Crest Gates 30-34");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reporterName.trim() || !description.trim()) {
      setError("Please provide your name and a detailed description.");
      return;
    }

    setSubmitting(true);
    setError(undefined);

    // Approximate 3D coordinates based on selected component
    let coords: [number, number, number] = [0, 2.5, 5];
    if (observationType === "DEBRIS_JAM") coords = [8, 2.8, 6];
    else if (observationType === "STRUCTURAL_CRACK") coords = [-16, 3.2, 2];
    else if (observationType === "EROSION_SCOUR") coords = [-8, -1.5, 10];
    else if (observationType === "WATER_OVERFLOW") coords = [0, 4.0, 12];
    else if (observationType === "GATE_MALFUNCTION") coords = [18, 2.2, 4];

    try {
      const res = await fetch(`/api/v1/assets/${assetCode}/observations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reporter_name: reporterName,
          reporter_phone: reporterPhone,
          observation_type: observationType,
          severity,
          description: `[Location: ${componentLocation}] ${description}`,
          coordinates_3d: coords,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to submit observation");
      }

      const created: CitizenHazardObservationRecord = await res.json();
      setSuccess(true);
      setTimeout(() => {
        onSubmitted(created);
        onClose();
        setSuccess(false);
        setDescription("");
      }, 1200);
    } catch (err: any) {
      setError(err.message || "Failed to submit observation");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl border border-[#D9E3EC] bg-white shadow-2xl p-6 text-[#172B3A] relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#61788A] hover:text-[#172B3A] hover:bg-slate-100 transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2.5 mb-2">
          <div className="p-2 rounded-lg bg-amber-50 text-[#F2A623] border border-amber-200">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#0C4775] tracking-tight">
              Submit Public Hazard & Observation
            </h3>
            <p className="text-xs text-[#61788A]">
              Report real-world field observation for: <strong className="text-[#0875BE]">{assetName}</strong>
            </p>
          </div>
        </div>

        {success ? (
          <div className="py-8 text-center space-y-2">
            <CheckCircle className="w-12 h-12 text-[#20A36A] mx-auto animate-bounce" />
            <div className="text-sm font-bold text-[#20A36A]">Observation Submitted Successfully!</div>
            <p className="text-xs text-[#61788A]">
              Your field report has been ingested. An interactive hazard pin is now mapped directly onto the 3D Digital Twin and alerted to the Command Center.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
            {error && (
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-[#D94343]">
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                  Reporter Name / Citizen ID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. K. Prasad (Citizen / Field Staff)"
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] placeholder-[#61788A] focus:border-[#0875BE] focus:ring-1 focus:ring-[#0875BE] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                  Contact Mobile Number
                </label>
                <input
                  type="text"
                  placeholder="+91 98480 XXXXX"
                  value={reporterPhone}
                  onChange={(e) => setReporterPhone(e.target.value)}
                  className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] placeholder-[#61788A] focus:border-[#0875BE] focus:ring-1 focus:ring-[#0875BE] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                  Hazard Observation Type *
                </label>
                <select
                  value={observationType}
                  onChange={(e) => setObservationType(e.target.value as any)}
                  className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] focus:border-[#0875BE] focus:outline-none"
                >
                  <option value="DEBRIS_JAM">Debris / Floating Timber Jam</option>
                  <option value="WATER_OVERFLOW">Sudden Water Rise / Overtopping</option>
                  <option value="STRUCTURAL_CRACK">Structural Crack / Concrete Spalling</option>
                  <option value="EROSION_SCOUR">Riverbed Erosion / Scour Hole</option>
                  <option value="GATE_MALFUNCTION">Spillway Gate Hoist Malfunction</option>
                  <option value="SURFACE_POTHOLE">Surface Settlement / Deformation</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                  Perceived Severity *
                </label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as any)}
                  className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] focus:border-[#0875BE] focus:outline-none"
                >
                  <option value="LOW">Low (Minor Advisory)</option>
                  <option value="MEDIUM">Medium (Watch Condition)</option>
                  <option value="HIGH">High (Immediate Risk Warning)</option>
                  <option value="CRITICAL">Critical (Emergency Threat)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                Estimated Location on Structure
              </label>
              <input
                type="text"
                placeholder="e.g. Spillway Bay 32, Upstream Abutment, Pier 14, Downstream Apron"
                value={componentLocation}
                onChange={(e) => setComponentLocation(e.target.value)}
                className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] placeholder-[#61788A] focus:border-[#0875BE] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[#172B3A] mb-1">
                Detailed Observation & Physical Evidence *
              </label>
              <textarea
                required
                rows={3}
                placeholder="Describe what you observed (water swirls, abnormal vibration, cracking sound, blockage dimensions, time first noticed)..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg border border-[#D9E3EC] bg-white px-3 py-1.5 text-xs text-[#172B3A] placeholder-[#61788A] focus:border-[#0875BE] focus:outline-none"
              />
            </div>

            <div className="pt-3 flex items-center justify-between border-t border-[#D9E3EC]">
              <span className="text-[11px] text-[#61788A] flex items-center gap-1 font-medium">
                <MapPin className="w-3.5 h-3.5 text-[#0875BE]" />
                Will be pinned to 3D Digital Twin
              </span>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3 py-1.5 rounded-lg border border-[#D9E3EC] text-xs font-semibold text-[#61788A] hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-[#0875BE] hover:bg-[#0C4775] text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  {submitting ? "Submitting..." : "Submit to 3D Twin"}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
