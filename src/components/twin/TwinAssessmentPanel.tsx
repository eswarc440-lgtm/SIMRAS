import { Activity, Calendar, FileText, ShieldCheck } from "lucide-react";
import type { AssetSummary } from "../../types/twin";
import type { TwinViewModel } from "./twinViewModel";

function score(value: number | null) {
  return value === null ? "N/A" : `${Math.round(value)}/100`;
}

export function TwinAssessmentPanel({
  asset,
  view,
  loading,
  onOpenReport,
}: {
  asset: AssetSummary;
  view: TwinViewModel;
  loading: boolean;
  onOpenReport: () => void;
}) {
  const riskTone =
    view.riskScore !== null && view.riskScore >= 60
      ? "text-red-700 bg-red-50 border-red-200"
      : view.riskScore !== null && view.riskScore >= 30
        ? "text-amber-700 bg-amber-50 border-amber-200"
        : "text-emerald-700 bg-emerald-50 border-emerald-200";

  return (
    <aside className="h-full rounded-xl border border-[#DDE5EC] bg-white p-4 shadow-sm overflow-y-auto">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#0875BE]">Assessment</p>
          <h2 className="text-sm font-bold text-[#0C4775]">Structural condition</h2>
        </div>
        <ShieldCheck className="h-5 w-5 text-[#0875BE]" />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
          <span className="text-[10px] font-bold uppercase text-slate-500">Health</span>
          <p className="mt-1 text-2xl font-extrabold text-[#0875BE]">{score(view.healthScore)}</p>
        </div>
        <div className={`rounded-lg border p-3 ${riskTone}`}>
          <span className="text-[10px] font-bold uppercase">Risk</span>
          <p className="mt-1 text-2xl font-extrabold">{score(view.riskScore)}</p>
        </div>
      </div>

      <dl className="mt-4 divide-y divide-slate-100 text-xs">
        <div className="flex items-center justify-between gap-3 py-3">
          <dt className="flex items-center gap-2 text-slate-500"><Activity className="h-4 w-4" />Risk level</dt>
          <dd className="font-bold text-slate-800">{view.riskLevel ?? "NOT AVAILABLE"}</dd>
        </div>
        <div className="flex items-center justify-between gap-3 py-3">
          <dt className="flex items-center gap-2 text-slate-500"><ShieldCheck className="h-4 w-4" />RUL</dt>
          <dd className="font-bold text-slate-800">{view.rulYears === null ? "NOT AVAILABLE" : `${view.rulYears} years`}</dd>
        </div>
        <div className="flex items-center justify-between gap-3 py-3">
          <dt className="flex items-center gap-2 text-slate-500"><Calendar className="h-4 w-4" />Last inspection</dt>
          <dd className="font-semibold text-slate-700">{view.lastInspection ?? "NOT AVAILABLE"}</dd>
        </div>
        <div className="flex items-center justify-between gap-3 py-3">
          <dt className="text-slate-500">Identity</dt>
          <dd className="font-semibold text-slate-700">{asset.identity_status || "NOT VERIFIED"}</dd>
        </div>
      </dl>

      {loading && <p className="mt-3 text-[11px] text-slate-500">Refreshing verified records…</p>}

      <button
        type="button"
        onClick={onOpenReport}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-md bg-[#0875BE] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#0C4775]"
      >
        <FileText className="h-4 w-4" /> View Official Report
      </button>
    </aside>
  );
}
