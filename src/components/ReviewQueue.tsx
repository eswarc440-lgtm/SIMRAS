import React, { useState, useEffect } from "react";
import { RegistrationReviewQueue } from './RegistrationReviewQueue';
import { CheckCircle2, XCircle, Clock, AlertTriangle, MessageSquare, Shield } from "lucide-react";

interface InspectionRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  inspector_name: string;
  inspector_email: string;
  inspection_type: string;
  inspection_date: string;
  condition_rating: string;
  findings: string;
  defects: Array<{ component: string; severity: string; description: string }>;
  recommended_actions: string;
  status: "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";
  reviewer_comments?: string;
  reviewed_by?: string;
}

export function ReviewQueue({ onRegistrationsChanged }: { onRegistrationsChanged?: () => Promise<unknown> }) {
  const [items, setItems] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InspectionRecord | null>(null);
  const [decisionComment, setDecisionComment] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/inspections");
      if (res.ok) {
        const data: InspectionRecord[] = await res.json();
        // Show pending items first, or recently reviewed
        setItems(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleDecision = async (status: "APPROVED" | "REJECTED") => {
    if (!selectedItem) return;
    setActionLoading(true);

    const token = localStorage.getItem("simras_token");

    try {
      const res = await fetch(`/api/v1/inspections/${selectedItem.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          status,
          comments: decisionComment.trim() || (status === "APPROVED" ? "Approved after structural engineering review." : "Rejected for clarification on defect extent."),
        }),
      });

      if (res.ok) {
        setSelectedItem(null);
        setDecisionComment("");
        fetchQueue();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const pendingCount = (items ?? []).filter((i) => i.status === "SUBMITTED").length;

  return (
    <div className="space-y-6">
      <RegistrationReviewQueue onReviewed={onRegistrationsChanged} />
      <div className="bg-[#0e1d2c] p-4 rounded-xl border border-gray-800 flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            Technical Review & Statutory Approval Queue
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Peer audit by State Dam Safety Organisation & Senior Review Engineers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
            {pendingCount} Pending Decision{pendingCount !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List of inspections */}
        <div className="lg:col-span-2 space-y-3">
          {loading ? (
            <div className="p-8 text-center text-gray-500 text-sm bg-[#0b1723] rounded-xl border border-gray-800">
              Loading review queue...
            </div>
          ) : (items?.length ?? 0) === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm bg-[#0b1723] rounded-xl border border-gray-800">
              No inspections available in the audit queue.
            </div>
          ) : (
            (items ?? []).map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  setSelectedItem(item);
                  setDecisionComment(item.reviewer_comments || "");
                }}
                className={`p-4 rounded-xl border cursor-pointer transition ${
                  selectedItem?.id === item.id
                    ? "bg-[#122538] border-cyan-400 shadow-lg shadow-cyan-500/10"
                    : "bg-[#0b1723] border-gray-800 hover:border-gray-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <span className="font-mono text-xs font-bold text-cyan-400 mr-2">{item.id}</span>
                    <strong className="text-white text-sm">{item.asset_name}</strong>
                    <span className="text-xs text-gray-400 ml-2">({item.asset_code})</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      item.status === "APPROVED"
                        ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                        : item.status === "REJECTED"
                        ? "bg-red-950/60 text-red-400 border border-red-500/30"
                        : "bg-cyan-950/60 text-cyan-300 border border-cyan-500/30"
                    }`}
                  >
                    {item.status.replace(/_/g, " ")}
                  </span>
                </div>

                <p className="text-xs text-gray-300 line-clamp-2 mb-2 leading-relaxed">{item.findings}</p>

                <div className="flex items-center justify-between text-[11px] text-gray-400 pt-2 border-t border-gray-800/60">
                  <span>Inspector: {item.inspector_name}</span>
                  <span>Date: {item.inspection_date}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Selected Audit Details & Decision Panel */}
        <div className="bg-[#0b1723] border border-gray-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
          {selectedItem ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-cyan-400">
                  Inspection Audit Dossier
                </span>
                <h4 className="text-sm font-bold text-white mt-1">{selectedItem.asset_name}</h4>
                <div className="text-xs font-mono text-gray-400">{selectedItem.id} · {selectedItem.asset_code}</div>
              </div>

              <div className="bg-[#112233] p-3 rounded-lg border border-gray-800 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Condition Rating:</span>
                  <span className="font-bold text-white">{selectedItem.condition_rating}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Audit Type:</span>
                  <span className="font-medium text-cyan-200">{selectedItem.inspection_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Inspector:</span>
                  <span className="text-gray-300">{selectedItem.inspector_name}</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Field Observations</label>
                <div className="text-xs text-gray-300 bg-[#071018] p-3 rounded-lg border border-gray-800/80 leading-relaxed max-h-32 overflow-y-auto">
                  {selectedItem.findings}
                </div>
              </div>

              {(selectedItem.defects?.length ?? 0) > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-amber-300 mb-1">
                    Recorded Defects ({selectedItem.defects?.length ?? 0})
                  </label>
                  <div className="space-y-1">
                    {(selectedItem.defects ?? []).map((d, i) => (
                      <div key={i} className="text-[11px] bg-[#122233] p-2 rounded border border-gray-800">
                        <strong className="text-white">{d.component}</strong> ({d.severity}): {d.description}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Recommended Remedial Actions</label>
                <div className="text-xs text-cyan-300/90 bg-[#071018] p-2.5 rounded-lg border border-gray-800">
                  {selectedItem.recommended_actions || "No specific actions specified."}
                </div>
              </div>

              {/* Reviewer Action */}
              <div className="pt-3 border-t border-gray-800">
                <label className="block text-xs font-medium text-gray-300 mb-1">
                  Senior Reviewer Comments / Directives
                </label>
                <textarea
                  rows={2}
                  value={decisionComment}
                  onChange={(e) => setDecisionComment(e.target.value)}
                  placeholder="State engineering reason for approval or specific rectifications needed..."
                  className="w-full bg-[#122233] border border-gray-700 rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400"
                />

                <div className="grid grid-cols-2 gap-2 mt-3">
                  <button
                    onClick={() => handleDecision("REJECTED")}
                    disabled={actionLoading}
                    className="py-2 px-3 rounded-lg bg-red-950/60 hover:bg-red-900/80 border border-red-500/40 text-red-300 text-xs font-bold transition flex items-center justify-center gap-1.5"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject Audit
                  </button>
                  <button
                    onClick={() => handleDecision("APPROVED")}
                    disabled={actionLoading}
                    className="py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-black text-xs font-bold transition flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Sign Off & Approve
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-gray-500 text-xs">
              Select an inspection record from the list to review evidence and record your statutory decision.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
