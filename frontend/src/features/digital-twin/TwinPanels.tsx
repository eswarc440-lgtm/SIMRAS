import type { TwinResponse } from "../../types/twin";
import { formatValue, riskColor } from "../../utils";
import { StatusPill } from "../../components/StatusPill";

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  return (
    <div className="twin-panels">
      <section className="panel score-panel">
        <div>
          <span>Health</span>
          <strong>{twin.ai.health_score?.toFixed(0) ?? "—"}<small>/100</small></strong>
        </div>
        <div>
          <span>Risk</span>
          <strong style={{ color: riskColor(twin.ai.risk_level) }}>
            {twin.ai.risk_score?.toFixed(0) ?? "—"}<small>/100</small>
          </strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{twin.ai.confidence ? `${Math.round(twin.ai.confidence * 100)}%` : "—"}</strong>
        </div>
      </section>

      <section className="panel">
        <header><h3>Current environment</h3><StatusPill label={twin.freshness.environment} /></header>
        <div className="metric-grid">
          {Object.entries(twin.environment).map(([key, item]) => (
            <article key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{formatValue(item.value, item.unit)}</strong>
              <small>{item.source_type.replaceAll("_", " ")} · {item.source}</small>
            </article>
          ))}
          {Object.keys(twin.environment).length === 0 && <p>No environmental feed is matched.</p>}
        </div>
      </section>

      <section className="panel">
        <header><h3>Decision-support factors</h3><StatusPill label={twin.ai.status} tone="warn" /></header>
        <ul className="factor-list">
          {twin.ai.factors.map((factor) => <li key={factor}>{factor}</li>)}
        </ul>
      </section>

      <section className="panel provenance-panel">
        <header><h3>Reality & provenance</h3><StatusPill label={twin.asset.identity_status} tone="warn" /></header>
        <dl>
          <div><dt>3D fidelity</dt><dd>{twin.twin.fidelity_level} · {twin.twin.model_source}</dd></div>
          <div><dt>Structural sensors</dt><dd>{twin.sensors_status.replaceAll("_", " ")}</dd></div>
          <div><dt>Inspection</dt><dd>{twin.inspection.quality_flag.replaceAll("_", " ")}</dd></div>
          <div><dt>RUL</dt><dd>{twin.ai.remaining_life_years ?? "Disabled until longitudinal validation"}</dd></div>
        </dl>
      </section>
    </div>
  );
}

