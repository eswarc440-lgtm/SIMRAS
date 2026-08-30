import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

function score(value?: number | null) {
  return value != null ? `${value.toFixed(0)}/100` : "N/A";
}

function label(value?: string | null) {
  return value ? value.replaceAll("_", " ") : "N/A";
}

const hiddenDimensionKeys = new Set([
  "representation",
  "template",
  "source_basis",
  "source_references",
  "alignment_status",
]);

function dimensionLabel(key: string) {
  return key
    .replace(/_m3s$/, " (m3/s)")
    .replace(/_mcm$/, " (MCM)")
    .replace(/_tmc$/, " (TMC)")
    .replace(/_m$/, " (m)")
    .replaceAll("_", " ");
}

function dimensionValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  }
  return String(value).replaceAll("_", " ");
}

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  const dimensions = Object.entries(twin.twin.dimensions).filter(
    ([key, value]) =>
      !hiddenDimensionKeys.has(key) && value !== null && value !== undefined,
  );

  return (
    <div className="clean-twin-panels">
      <section className="clean-score-grid">
        <div><span>SIMRAS health</span><strong>{score(twin.ai.health_score)}</strong><small>Research prediction</small></div>
        <div><span>SIMRAS risk</span><strong style={{ color: riskColor(twin.ai.risk_level) }}>{score(twin.ai.risk_score)}</strong><small>{label(twin.ai.risk_level)}</small></div>
        <div><span>SIMRAS hazard</span><strong style={{ color: riskColor(twin.ai.hazard_level) }}>{score(twin.ai.hazard_score)}</strong><small>{label(twin.ai.hazard_level)}</small></div>
        <div><span>Prediction confidence</span><strong>{twin.ai.confidence != null ? `${Math.round(twin.ai.confidence * 100)}%` : "N/A"}</strong><small>Not an official rating</small></div>
      </section>

      <section className="clean-panel">
        <header className="clean-panel-header"><div><span className="clean-kicker">EXPERIMENTAL</span><h3>Remaining useful life proxy</h3></div></header>
        <table className="clean-data-table"><tbody>
          <tr><th>Estimated remaining life</th><td>{twin.ai.remaining_life_years != null ? `${twin.ai.remaining_life_years.toFixed(1)} years` : "N/A"}</td></tr>
          <tr><th>Estimated range</th><td>{twin.ai.rul_lower_bound != null && twin.ai.rul_upper_bound != null ? `${twin.ai.rul_lower_bound.toFixed(1)} - ${twin.ai.rul_upper_bound.toFixed(1)} years` : "N/A"}</td></tr>
          <tr><th>Basis</th><td>{twin.ai.rul_basis_url ? <a href={twin.ai.rul_basis_url} target="_blank" rel="noreferrer">{twin.ai.rul_basis ?? "Open basis source"}</a> : (twin.ai.rul_basis ?? "N/A")}</td></tr>
          <tr><th>Status</th><td>{label(twin.ai.rul_status)}</td></tr>
          <tr><th>RUL confidence</th><td>{twin.ai.rul_confidence != null ? `${Math.round(twin.ai.rul_confidence * 100)}%` : "N/A"}</td></tr>
        </tbody></table>
        <p className="clean-note">Experimental planning-life proxy only; not an official structural remaining-life or dam-safety rating.</p>
      </section>

      <section className="clean-panel">
        <header className="clean-panel-header"><div><span className="clean-kicker">SOURCE BACKED</span><h3>Dimensions & characteristics</h3></div></header>
        <table className="clean-data-table"><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>
          {dimensions.map(([key, value]) => <tr key={key}><td>{dimensionLabel(key)}</td><td>{dimensionValue(value)}</td></tr>)}
        </tbody></table>
        <p className="clean-note">Dimensions follow linked records. Unprovided geometry remains parametric/approximate unless measured geometry is linked.</p>
      </section>

      <section className="clean-two-column">
        <article className="clean-panel"><h3>Recommendations</h3><ul className="clean-list">{(twin.ai.recommendations ?? []).map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article className="clean-panel"><h3>Why this prediction?</h3><ul className="clean-list">{twin.ai.factors.map((item) => <li key={item}>{item}</li>)}</ul></article>
      </section>
    </div>
  );
}