import React, { useState, useEffect } from "react";
import { ClipboardList, PlusCircle, CheckCircle, Clock, AlertTriangle, ShieldCheck, User } from "lucide-react";

interface InspectionRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  inspector_name: string;
  inspector_email: string;
  inspection_type: "ROUTINE" | "STRUCTURAL_AUDIT" | "SPECIAL_EVENT" | "POST_FLOOD";
  inspection_date: string;
  condition_rating: "EXCELLENT" | "GOOD" | "FAIR" | "POOR" | "CRITICAL";
  findings: string;
  defects: Array<{ component: string; severity: "MINOR" | "MODERATE" | "SEVERE"; description: string }>;
  recommended_actions: string;
  status: "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";
  reviewer_comments?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
}

interface InspectionsManagerProps {
  selectedAssetCode?: string;
  userRole?: string;
  onSelectAsset?: (code: string) => void;
}

export function InspectionsManager({ selectedAssetCode, userRole, onSelectAsset }: InspectionsManagerProps) {
  const [inspections, setInspections] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [showLogModal, setShowLogModal] = useState(false);

  // Form State
  const [formAssetCode, setFormAssetCode] = useState(selectedAssetCode || "AP_DAM_00001");
  const [inspType, setInspType] = useState<InspectionRecord["inspection_type"]>("ROUTINE");
  const [conditionRating, setConditionRating] = useState<InspectionRecord["condition_rating"]>("GOOD");
  const [findings, setFindings] = useState("");
  const [defectComponent, setDefectComponent] = useState("");
  const [defectSeverity, setDefectSeverity] = useState<"MINOR" | "MODERATE" | "SEVERE">("MINOR");
  const [defectDesc, setDefectDesc] = useState("");
  const [defects, setDefects] = useState<Array<{ component: string; severity: "MINOR" | "MODERATE" | "SEVERE"; description: string }>>([]);
  const [recommendedActions, setRecommendedActions] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchInspections = async () => {
    try {
      setLoading(true);
      const url = selectedAssetCode
        ? `/api/v1/inspections?asset_code=${encodeURIComponent(selectedAssetCode)}`
        : "/api/v1/inspections";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setInspections(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspections();
  }, [selectedAssetCode]);

  const addDefect = () => {
    if (!defectComponent.trim() || !defectDesc.trim()) return;
    setDefects([...defects, { component: defectComponent.trim(), severity: defectSeverity, description: defectDesc.trim() }]);
    setDefectComponent("");
    setDefectDesc("");
  };

  const removeDefect = (index: number) => {
    setDefects(defects.filter((_, i) => i !== index));
  };

  const handleCreateInspection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!findings.trim()) return;

    setSubmitting(true);
    const token = localStorage.getItem("simras_token");

    try {
      const res = await fetch("/api/v1/inspections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          asset_code: formAssetCode,
          inspection_type: inspType,
          condition_rating: conditionRating,
          findings: findings.trim(),
          defects,
          recommended_actions: recommendedActions.trim() || "Continue routine scheduled observation.",
          status: "SUBMITTED",
        }),
      });

      if (res.ok) {
        setShowLogModal(false);
        setFindings("");
        setDefects([]);
        setRecommendedActions("");
        fetchInspections();
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
            <ClipboardList className="w-5 h-5 text-cyan-400" />
            Field Inspections & Structural Audits
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {selectedAssetCode
              ? `Filtered to active asset: ${selectedAssetCode}`
              : "State-wide statutory inspection logs and condition ratings"}
          </p>
        </div>

        <button
          onClick={() => {
            if (selectedAssetCode) setFormAssetCode(selectedAssetCode);
            setShowLogModal(true);
          }}
          className="flex items-center gap-2 py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-xs font-bold transition shadow-lg shadow-cyan-500/20"
        >
          <PlusCircle className="w-4 h-4" />
          Log Official Inspection
        </button>
      </div>

      {/* Inspections Table */}
      <div className="bg-[#0b1723] rounded-xl border border-gray-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#112233] text-gray-400 uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="py-3 px-4">Inspection ID</th>
                <th className="py-3 px-4">Asset Code & Name</th>
                <th className="py-3 px-4">Type & Date</th>
                <th className="py-3 px-4">Rating</th>
                <th className="py-3 px-4">Defects</th>
                <th className="py-3 px-4">Status & Review</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 text-gray-300">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    Loading inspection logs...
                  </td>
                </tr>
              ) : inspections.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    No inspection logs recorded for this selection.
                  </td>
                </tr>
              ) : (
                inspections.map((insp) => (
                  <tr key={insp.id} className="hover:bg-[#122436]/50 transition">
                    <td className="py-3 px-4 font-mono font-semibold text-cyan-400">{insp.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-white">{insp.asset_name}</div>
                      <div className="text-[11px] font-mono text-gray-500">{insp.asset_code}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-gray-200">{insp.inspection_type.replace(/_/g, " ")}</div>
                      <div className="text-[11px] text-gray-400">{insp.inspection_date}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          insp.condition_rating === "EXCELLENT" || insp.condition_rating === "GOOD"
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                            : insp.condition_rating === "FAIR"
                            ? "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                            : "bg-red-950/60 text-red-400 border border-red-500/30"
                        }`}
                      >
                        {insp.condition_rating}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {(insp.defects?.length ?? 0) > 0 ? (
                        <span className="text-amber-400 font-medium">
                          {insp.defects?.length} defect{(insp.defects?.length ?? 0) > 1 ? "s" : ""} noted
                        </span>
                      ) : (
                        <span className="text-emerald-400">Nil defects</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        {insp.status === "APPROVED" ? (
                          <span className="flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                            <CheckCircle className="w-3.5 h-3.5" /> Approved
                          </span>
                        ) : insp.status === "REJECTED" ? (
                          <span className="flex items-center gap-1 text-red-400 font-semibold text-[11px]">
                            <AlertTriangle className="w-3.5 h-3.5" /> Rejected
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-cyan-300 font-semibold text-[11px]">
                            <Clock className="w-3.5 h-3.5" /> Pending Review
                          </span>
                        )}
                      </div>
                      {insp.reviewed_by && (
                        <div className="text-[10px] text-gray-500 mt-0.5">By {insp.reviewed_by}</div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Inspection Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#0b1723] border border-cyan-500/30 rounded-xl max-w-xl w-full p-6 shadow-2xl relative text-white max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-bold text-white mb-1">Log New Structural Inspection</h3>
            <p className="text-xs text-gray-400 mb-4">Official statutory audit record submission</p>

            <form onSubmit={handleCreateInspection} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Asset Code</label>
                  <input
                    type="text"
                    required
                    value={formAssetCode}
                    onChange={(e) => setFormAssetCode(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Inspection Type</label>
                  <select
                    value={inspType}
                    onChange={(e) => setInspType(e.target.value as any)}
                    className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  >
                    <option value="ROUTINE">Routine Observation</option>
                    <option value="STRUCTURAL_AUDIT">Comprehensive Structural Audit</option>
                    <option value="POST_FLOOD">Post-Flood Event Audit</option>
                    <option value="SPECIAL_EVENT">Pre-Festival / Special Load Audit</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Overall Condition Rating</label>
                <div className="grid grid-cols-5 gap-2">
                  {(["EXCELLENT", "GOOD", "FAIR", "POOR", "CRITICAL"] as const).map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setConditionRating(r)}
                      className={`py-1.5 px-2 rounded text-[11px] font-bold border transition ${
                        conditionRating === r
                          ? "bg-cyan-600 text-black border-cyan-400"
                          : "bg-[#122233] text-gray-300 border-gray-700 hover:border-gray-500"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Detailed Findings & Observations *</label>
                <textarea
                  required
                  rows={3}
                  value={findings}
                  onChange={(e) => setFindings(e.target.value)}
                  placeholder="Record observed structural condition, scour, crack patterns, or hydraulic behavior..."
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400"
                />
              </div>

              {/* Defect Itemizer */}
              <div className="p-3 bg-[#112233] rounded-lg border border-gray-800 space-y-2">
                <label className="block text-xs font-semibold text-cyan-300">Itemize Structural Defects (Optional)</label>
                <div className="grid grid-cols-12 gap-2">
                  <input
                    type="text"
                    placeholder="Component (e.g. Pier 4 Baffle)"
                    value={defectComponent}
                    onChange={(e) => setDefectComponent(e.target.value)}
                    className="col-span-4 bg-[#0a1520] border border-gray-700 rounded p-1.5 text-xs text-white"
                  />
                  <select
                    value={defectSeverity}
                    onChange={(e) => setDefectSeverity(e.target.value as any)}
                    className="col-span-3 bg-[#0a1520] border border-gray-700 rounded p-1.5 text-xs text-white"
                  >
                    <option value="MINOR">Minor</option>
                    <option value="MODERATE">Moderate</option>
                    <option value="SEVERE">Severe</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Description of wear"
                    value={defectDesc}
                    onChange={(e) => setDefectDesc(e.target.value)}
                    className="col-span-4 bg-[#0a1520] border border-gray-700 rounded p-1.5 text-xs text-white"
                  />
                  <button
                    type="button"
                    onClick={addDefect}
                    className="col-span-1 bg-cyan-600 hover:bg-cyan-500 text-black font-bold rounded flex items-center justify-center text-sm"
                  >
                    +
                  </button>
                </div>

                {defects.length > 0 && (
                  <div className="space-y-1 pt-1">
                    {defects.map((d, i) => (
                      <div key={i} className="flex items-center justify-between text-xs bg-[#0a1520] p-1.5 rounded border border-gray-800">
                        <span>
                          <strong className="text-white">{d.component}</strong> ({d.severity}): {d.description}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeDefect(i)}
                          className="text-red-400 hover:text-red-300 text-xs px-1"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Recommended Remedial Actions</label>
                <input
                  type="text"
                  value={recommendedActions}
                  onChange={(e) => setRecommendedActions(e.target.value)}
                  placeholder="e.g. Schedule high-strength epoxy underwater mortar repair within 30 days"
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="py-2 px-4 rounded-lg bg-[#13273b] hover:bg-[#1a334d] text-xs text-gray-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="py-2 px-5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-xs font-bold transition disabled:opacity-50"
                >
                  {submitting ? "Submitting..." : "Submit Inspection Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
