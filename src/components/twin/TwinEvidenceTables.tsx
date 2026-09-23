import type { TwinViewModel } from "./twinViewModel";

function EmptyState({ children }: { children: string }) {
  return <div className="p-5 text-center text-xs font-semibold text-slate-400">{children}</div>;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-xl border border-[#DDE5EC] bg-white shadow-sm">
      <h3 className="border-b border-[#DDE5EC] bg-slate-50 px-4 py-3 text-xs font-bold uppercase tracking-wide text-[#0C4775]">
        {title}
      </h3>
      <div className="overflow-x-auto">{children}</div>
    </section>
  );
}

const headClass = "px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wide text-slate-500";
const cellClass = "px-3 py-2 text-xs text-slate-700 border-t border-slate-100";

export function TwinEvidenceTables({ view }: { view: TwinViewModel }) {
  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
      <Card title="Engineering Dimensions">
        {view.dimensions.length === 0 ? <EmptyState>DATA NOT AVAILABLE</EmptyState> : (
          <table className="w-full"><thead><tr><th className={headClass}>Parameter</th><th className={headClass}>Value</th><th className={headClass}>Unit</th><th className={headClass}>Source</th></tr></thead>
            <tbody>{view.dimensions.map((row) => <tr key={row.parameter}><td className={cellClass}>{row.parameter}</td><td className={`${cellClass} font-semibold`}>{row.value}</td><td className={cellClass}>{row.unit}</td><td className={cellClass}>{row.source}</td></tr>)}</tbody>
          </table>
        )}
      </Card>

      <Card title="Telemetry">
        {view.telemetry.length === 0 ? <EmptyState>DATA NOT AVAILABLE</EmptyState> : (
          <table className="w-full"><thead><tr><th className={headClass}>Metric</th><th className={headClass}>Value</th><th className={headClass}>Status</th><th className={headClass}>Updated / Source</th></tr></thead>
            <tbody>{view.telemetry.map((row) => <tr key={`${row.metric}-${row.unit}`}><td className={cellClass}>{row.metric}</td><td className={`${cellClass} font-semibold`}>{row.value} {row.unit}</td><td className={cellClass}><span className="rounded bg-slate-100 px-2 py-1 text-[10px] font-bold">{row.status}</span></td><td className={cellClass}>{row.lastUpdated}<span className="block text-[10px] text-slate-400">{row.source}</span></td></tr>)}</tbody>
          </table>
        )}
      </Card>

      <Card title="Recent Inspections">
        {view.inspections.length === 0 ? <EmptyState>DATA NOT AVAILABLE</EmptyState> : (
          <table className="w-full"><thead><tr><th className={headClass}>Date / ID</th><th className={headClass}>Inspector</th><th className={headClass}>Condition</th><th className={headClass}>Defects / Status</th></tr></thead>
            <tbody>{view.inspections.map((row) => <tr key={row.id}><td className={cellClass}>{row.date}<span className="block font-mono text-[10px] text-slate-400">{row.id}</span></td><td className={cellClass}>{row.inspector}<span className="block text-[10px] text-slate-400">{row.type}</span></td><td className={cellClass}>{row.condition}</td><td className={cellClass}>{row.defects} defects<span className="block text-[10px] font-bold text-[#0875BE]">{row.status}</span></td></tr>)}</tbody>
          </table>
        )}
      </Card>

      <Card title="Maintenance">
        {view.maintenance.length === 0 ? <EmptyState>DATA NOT AVAILABLE</EmptyState> : (
          <table className="w-full"><thead><tr><th className={headClass}>Work Order</th><th className={headClass}>Title</th><th className={headClass}>Priority</th><th className={headClass}>Due / Status</th></tr></thead>
            <tbody>{view.maintenance.map((row) => <tr key={row.id}><td className={`${cellClass} font-mono`}>{row.id}</td><td className={cellClass}>{row.title}<span className="block text-[10px] text-slate-400">{row.category}</span></td><td className={cellClass}><span className={`rounded px-2 py-1 text-[10px] font-bold ${row.priority === "HIGH" ? "bg-red-50 text-red-700" : row.priority === "MEDIUM" ? "bg-amber-50 text-amber-700" : "bg-blue-50 text-blue-700"}`}>{row.priority}</span></td><td className={cellClass}>{row.dueDate}<span className="block text-[10px] font-bold text-[#0875BE]">{row.status}</span></td></tr>)}</tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
