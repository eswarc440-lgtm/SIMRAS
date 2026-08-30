import type { EvidenceStateResponse } from "../../types/evidence";

function label(value: string | null | undefined) {
  return value ? value.replaceAll("_", " ") : "N/A";
}

function displayValue(value: number | string | null | undefined, unit?: string | null) {
  if (value === null || value === undefined) return "N/A";
  const rendered = typeof value === "number"
    ? (Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 3 }))
    : String(value).replaceAll("_", " ");
  return unit ? `${rendered} ${unit}` : rendered;
}

export function EvidenceStatePanel({ state }: { state: EvidenceStateResponse }) {
  const environment = Object.entries(state.environment);
  const officialCondition = state.condition.condition === "UNKNOWN" ? "Not published in linked official records" : label(state.condition.condition);
  const officialRisk = state.condition.risk === "UNKNOWN" ? "Not published in linked official records" : label(state.condition.risk);

  return (
    <div className="clean-evidence-panels">
      <section className="clean-panel">
        <header className="clean-panel-header"><div><span className="clean-kicker">GOVERNMENT EVIDENCE</span><h3>Official safety & structural evidence</h3></div></header>
        <table className="clean-data-table"><tbody>
          <tr><th>Official structural condition</th><td>{officialCondition}</td></tr>
          <tr><th>Official structural risk</th><td>{officialRisk}</td></tr>
          <tr><th>Evidence strength</th><td>{label(state.evidence_strength)}</td></tr>
          <tr><th>Asset identity</th><td>{label(state.asset.identity_status)}</td></tr>
          <tr><th>District</th><td>{state.asset.district ?? "N/A"}</td></tr>
          <tr><th>Owner</th><td>{state.asset.owner ?? "N/A"}</td></tr>
        </tbody></table>
        <p className="clean-note">Missing official condition/risk values are not replaced with SIMRAS predictions.</p>
      </section>

      <section className="clean-panel">
        <header className="clean-panel-header"><div><span className="clean-kicker">LINKED RECORDS</span><h3>Real official evidence</h3></div></header>
        <div className="clean-table-scroll"><table className="clean-data-table evidence-record-table"><thead><tr><th>Field</th><th>Value</th><th>Authority</th><th>Agency / source</th><th>Document</th><th>Confidence</th></tr></thead><tbody>
          {state.evidence.map((item) => <tr key={item.id}>
            <td>{label(item.field_name)}</td>
            <td>{item.text_value ?? displayValue(item.numeric_value, item.unit)}</td>
            <td>{label(item.authority_level)}</td>
            <td>{item.agency ?? item.source_name ?? "N/A"}</td>
            <td>{item.document_url ? <a href={item.document_url} target="_blank" rel="noreferrer">{item.document_title ?? "Official document"}</a> : (item.document_title ?? "N/A")}</td>
            <td>{item.confidence_score != null ? `${Math.round(item.confidence_score * 100)}%` : "N/A"}</td>
          </tr>)}
          {state.evidence.length === 0 && <tr><td colSpan={6}>No linked official evidence record.</td></tr>}
        </tbody></table></div>
        <p className="clean-note">Governance/safety records such as an Emergency Action Plan are real official evidence, but do not by themselves establish a structural-condition rating.</p>
      </section>

      <section className="clean-panel">
        <header className="clean-panel-header"><div><span className="clean-kicker">OBSERVED DATA</span><h3>Government environmental observations</h3></div></header>
        <div className="clean-table-scroll"><table className="clean-data-table"><thead><tr><th>Variable</th><th>Value</th><th>Source</th><th>Observed at</th><th>Quality</th><th>Confidence</th></tr></thead><tbody>
          {environment.map(([key, item]) => <tr key={key}>
            <td>{label(key)}</td><td>{displayValue(item.value, item.unit)}</td><td>{item.source ?? "N/A"}</td><td>{item.observed_at ? new Date(item.observed_at).toLocaleString() : "N/A"}</td><td>{label(item.quality_flag)}</td><td>{item.confidence != null ? `${Math.round(item.confidence * 100)}%` : "N/A"}</td>
          </tr>)}
          {environment.length === 0 && <tr><td colSpan={6}>No matched government environmental observation.</td></tr>}
        </tbody></table></div>
      </section>
    </div>
  );
}