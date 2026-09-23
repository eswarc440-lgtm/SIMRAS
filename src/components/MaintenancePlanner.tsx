import React, { useState, useEffect } from "react";
import { Wrench, PlusCircle, CheckCircle, Clock, AlertCircle, ArrowRight } from "lucide-react";

interface MaintenanceRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  title: string;
  category: "PREVENTIVE" | "CORRECTIVE" | "REHABILITATION" | "EMERGENCY";
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  scheduled_start: string;
  scheduled_end: string;
  actual_completed?: string;
  cost_inr_lakhs?: number;
  assigned_contractor_or_team: string;
  work_description: string;
  status: "PLANNED" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED";
  verification_notes?: string;
  created_at: string;
}

interface MaintenancePlannerProps {
  selectedAssetCode?: string;
  userRole?: string;
  onSelectAsset?: (code: string) => void;
}

export function MaintenancePlanner({ selectedAssetCode }: MaintenancePlannerProps) {
  const [plans, setPlans] = useState<MaintenanceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Form State
  const [assetCode, setAssetCode] = useState(selectedAssetCode || "AP_DAM_00001");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<MaintenanceRecord["category"]>("PREVENTIVE");
  const [priority, setPriority] = useState<MaintenanceRecord["priority"]>("HIGH");
  const [start, setStart] = useState(new Date().toISOString().split("T")[0]);
  const [end, setEnd] = useState("");
  const [costLakhs, setCostLakhs] = useState("25.0");
  const [team, setTeam] = useState("APWRD Mechanical Division / State PWD");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const url = selectedAssetCode
        ? `/api/v1/maintenance?asset_code=${encodeURIComponent(selectedAssetCode)}`
        : "/api/v1/maintenance";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setPlans(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, [selectedAssetCode]);

  const updateStatus = async (id: string, newStatus: MaintenanceRecord["status"]) => {
    try {
      const res = await fetch(`/api/v1/maintenance/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchPlans();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !end) return;

    setSubmitting(true);
    try {
      const res = await fetch("/api/v1/maintenance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_code: assetCode,
          title: title.trim(),
          category,
          priority,
          scheduled_start: start,
          scheduled_end: end,
          cost_inr_lakhs: parseFloat(costLakhs) || undefined,
          assigned_contractor_or_team: team.trim(),
          work_description: description.trim(),
          status: "PLANNED",
        }),
      });

      if (res.ok) {
        setShowModal(false);
        setTitle("");
        setDescription("");
        fetchPlans();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1d2c] p-4 rounded-xl border border-gray-800">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Wrench className="w-5 h-5 text-cyan-400" />
            Maintenance Work Orders & Capital Rehabilitation
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {selectedAssetCode
              ? `Filtered to active asset: ${selectedAssetCode}`
              : "State-wide infrastructure maintenance schedules and cost tracking"}
          </p>
        </div>

        <button
          onClick={() => {
            if (selectedAssetCode) setAssetCode(selectedAssetCode);
            setShowModal(true);
          }}
          className="flex items-center gap-2 py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-xs font-bold transition shadow-lg shadow-cyan-500/20"
        >
          <PlusCircle className="w-4 h-4" />
          Schedule Work Order
        </button>
      </div>

      {/* Grid of Work Orders */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-8 text-center text-gray-500 text-sm">
            Loading maintenance schedules...
          </div>
        ) : plans.length === 0 ? (
          <div className="col-span-full py-8 text-center text-gray-500 text-sm">
            No active maintenance orders found.
          </div>
        ) : (
          plans.map((p) => (
            <div
              key={p.id}
              className="bg-[#0b1723] rounded-xl border border-gray-800 p-4 flex flex-col justify-between hover:border-cyan-500/30 transition shadow-lg"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="font-mono text-[11px] font-bold text-cyan-400">{p.id}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      p.priority === "URGENT"
                        ? "bg-red-950/60 text-red-400 border border-red-500/30"
                        : p.priority === "HIGH"
                        ? "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                        : "bg-blue-950/60 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {p.priority}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-white mb-1 leading-snug">{p.title}</h4>
                <div className="text-[11px] text-gray-400 mb-2 font-mono">{p.asset_name} ({p.asset_code})</div>
                <p className="text-xs text-gray-300 line-clamp-3 mb-3 leading-relaxed">{p.work_description}</p>

                <div className="space-y-1 text-[11px] text-gray-400 bg-[#112233] p-2.5 rounded-lg border border-gray-800/80 mb-3">
                  <div className="flex justify-between">
                    <span>Schedule:</span>
                    <span className="text-white font-medium">{p.scheduled_start} → {p.scheduled_end}</span>
                  </div>
                  {p.cost_inr_lakhs && (
                    <div className="flex justify-between">
                      <span>Sanctioned Cost:</span>
                      <span className="text-cyan-300 font-semibold">₹ {p.cost_inr_lakhs} Lakhs</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Team / Vendor:</span>
                    <span className="text-gray-300 truncate max-w-[150px]">{p.assigned_contractor_or_team}</span>
                  </div>
                </div>
              </div>

              {/* Status and transition buttons */}
              <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between">
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                    p.status === "VERIFIED"
                      ? "bg-emerald-950/60 text-emerald-400"
                      : p.status === "COMPLETED"
                      ? "bg-cyan-950/60 text-cyan-300"
                      : p.status === "IN_PROGRESS"
                      ? "bg-amber-950/60 text-amber-300"
                      : "bg-gray-800 text-gray-300"
                  }`}
                >
                  {p.status.replace(/_/g, " ")}
                </span>

                <div className="flex items-center gap-1.5">
                  {p.status === "PLANNED" && (
                    <button
                      onClick={() => updateStatus(p.id, "IN_PROGRESS")}
                      className="text-[11px] text-amber-400 hover:text-amber-300 font-medium px-2 py-1 rounded bg-[#13273b]"
                    >
                      Start Work →
                    </button>
                  )}
                  {p.status === "IN_PROGRESS" && (
                    <button
                      onClick={() => updateStatus(p.id, "COMPLETED")}
                      className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium px-2 py-1 rounded bg-[#13273b]"
                    >
                      Mark Complete →
                    </button>
                  )}
                  {p.status === "COMPLETED" && (
                    <button
                      onClick={() => updateStatus(p.id, "VERIFIED")}
                      className="text-[11px] text-emerald-400 hover:text-emerald-300 font-medium px-2 py-1 rounded bg-[#13273b]"
                    >
                      Sign Off Verified ✓
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Schedule Work Order Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#0b1723] border border-cyan-500/30 rounded-xl max-w-lg w-full p-6 shadow-2xl relative text-white max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-white mb-1">Schedule Maintenance Work Order</h3>
            <p className="text-xs text-gray-400 mb-4">Official engineering work sanction</p>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Target Asset Code</label>
                <input
                  type="text"
                  required
                  value={assetCode}
                  onChange={(e) => setAssetCode(e.target.value)}
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Work Order Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Scouring Sluice Gate Overhaul & Apron Grouting"
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as any)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="PREVENTIVE">Preventive Maintenance</option>
                    <option value="CORRECTIVE">Corrective Repair</option>
                    <option value="REHABILITATION">Capital Rehabilitation</option>
                    <option value="EMERGENCY">Emergency Response</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as any)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Start Date</label>
                  <input
                    type="date"
                    required
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Target Completion Date *</label>
                  <input
                    type="date"
                    required
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Estimated Cost (₹ Lakhs)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={costLakhs}
                    onChange={(e) => setCostLakhs(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Contractor / Team</label>
                  <input
                    type="text"
                    value={team}
                    onChange={(e) => setTeam(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Scope of Work & Specification</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Detail the technical execution procedure, materials, and NDT requirements..."
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="py-2 px-4 rounded-lg bg-[#13273b] hover:bg-[#1a334d] text-xs text-gray-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="py-2 px-5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-xs font-bold transition disabled:opacity-50"
                >
                  {submitting ? "Sanctioning..." : "Sanction Work Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
