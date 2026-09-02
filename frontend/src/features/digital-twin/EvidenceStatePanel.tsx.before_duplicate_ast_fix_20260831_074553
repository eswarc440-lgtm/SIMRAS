import { StatusPill } from "../../components/StatusPill";
import type {
  EvidenceBand,
  EvidenceStateResponse,
} from "../../types/evidence";

const unavailable = "—";

function label(value: string | null | undefined) {
  return value ? value.replaceAll("_", " ") : unavailable;
}

function toneFor(value: string): "good" | "warn" | "danger" {
  if (value === "HEALTHY" || value === "LOW" || value === "HIGH") {
    return value === "HIGH" ? "warn" : "good";
  }

  if (
    value === "MONITOR" ||
    value === "MEDIUM" ||
    value === "HIGH_PRIORITY"
  ) {
    return "warn";
  }

  if (value === "CRITICAL" || value === "WEAK") {
    return "danger";
  }

  return "warn";
}

function bandColour(value: EvidenceBand) {
  switch (value) {
    case "LOW":
      return "#37d3a2";
    case "MEDIUM":
      return "#f7c948";
    case "HIGH":
      return "#ff8a4c";
    case "CRITICAL":
      return "#ff5b62";
    default:
      return "#94a3b8";
  }
}

function displayValue(value: number | string | null, unit?: string | null) {
  if (value == null) return unavailable;

  const rendered =
    typeof value === "number"
      ? Number.isInteger(value)
        ? String(value)
        : value.toFixed(2)
      : String(value);

  return unit ? `${rendered} ${unit}` : rendered;
}

export function EvidenceStatePanel({
  state,
}: {
  state: EvidenceStateResponse;
}) {
  const environment = Object.entries(state.environment);
  const importantEvidence = state.evidence.filter(
    (item) =>
      item.authority_level === "A1" ||
      item.authority_level === "A2",
  );

  return (
    <div className="twin-panels">
      <section className="panel score-panel score-panel-four">
        <div>
          <span>Structural condition</span>
          <strong>{label(state.condition.condition)}</strong>
          <small>{label(state.condition.origin)}</small>
        </div>

        <div>
          <span>Structural risk</span>
          <strong
            style={{
              color: bandColour(state.condition.risk),
            }}
          >
            {label(state.condition.risk)}
          </strong>
          <small>
            {state.condition.authority_level
              ? `Evidence ${state.condition.authority_level}`
              : "Official condition evidence unavailable"}
          </small>
        </div>

        <div>
          <span>Environmental hazard</span>
          <strong
            style={{
              color: bandColour(state.hazard.value),
            }}
          >
            {label(state.hazard.value)}
          </strong>
          <small>{label(state.hazard.origin)}</small>
        </div>

        <div>
          <span>Evidence strength</span>
          <strong>{label(state.evidence_strength)}</strong>
          <small>No fabricated health percentage</small>
        </div>
      </section>

      <section className="panel prediction-disclosure">
        <div>
          <span>Overall risk</span>
          <strong style={{ color: bandColour(state.risk.value) }}>
            {label(state.risk.value)}
          </strong>
        </div>

        <div>
          <span>Health score</span>
          <strong>{unavailable}</strong>
        </div>

        <div>
          <span>Remaining life</span>
          <strong>{unavailable}</strong>
        </div>

        <StatusPill
          label={label(state.risk.origin)}
          tone={toneFor(state.risk.value)}
        />
      </section>

      <section className="panel">
        <header>
          <h3>Government environmental observations</h3>
          <StatusPill
            label={
              environment.length > 0
                ? "GOVERNMENT DATA"
                : "NO MATCHED FEED"
            }
            tone={environment.length > 0 ? "good" : "warn"}
          />
        </header>

        <div className="metric-grid">
          {environment.map(([key, item]) => (
            <article key={key}>
              <span>{label(key)}</span>
              <strong>{displayValue(item.value, item.unit)}</strong>
              <small>
                {item.source ?? "Unknown source"}
                {item.observed_at
                  ? ` · ${new Date(item.observed_at).toLocaleString()}`
                  : ""}
              </small>
              <small>
                {label(item.quality_flag)}
                {item.confidence != null
                  ? ` · ${Math.round(item.confidence * 100)}% confidence`
                  : ""}
              </small>
            </article>
          ))}

          {environment.length === 0 && (
            <p>No government environmental observation is matched.</p>
          )}
        </div>
      </section>

      <section className="panel provenance-panel">
        <header>
          <h3>Official structural evidence</h3>
          <StatusPill
            label={
              state.condition.condition === "UNKNOWN"
                ? "INSUFFICIENT CONDITION EVIDENCE"
                : state.condition.origin
            }
            tone={
              state.condition.condition === "UNKNOWN"
                ? "warn"
                : "good"
            }
          />
        </header>

        <dl>
          <div>
            <dt>Condition</dt>
            <dd>{label(state.condition.condition)}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{state.condition.source ?? unavailable}</dd>
          </div>
          <div>
            <dt>Document</dt>
            <dd>
              {state.condition.document_url ? (
                <a
                  className="model-source-link"
                  href={state.condition.document_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {state.condition.document ?? "Official document"} ↗
                </a>
              ) : (
                state.condition.document ?? unavailable
              )}
            </dd>
          </div>
          <div>
            <dt>Rating system</dt>
            <dd>{label(state.condition.rating_system)}</dd>
          </div>
          <div>
            <dt>Origin</dt>
            <dd>{label(state.condition.origin)}</dd>
          </div>
          <div>
            <dt>RUL</dt>
            <dd>Disabled until longitudinal AP validation</dd>
          </div>
        </dl>

        {importantEvidence.length > 0 && (
          <div className="dimension-list">
            <h4>A1/A2 evidence linked to this asset</h4>
            <dl>
              {importantEvidence.map((item) => (
                <div key={item.id}>
                  <dt>{label(item.field_name)}</dt>
                  <dd>
                    {item.text_value ??
                      displayValue(item.numeric_value ?? null, item.unit)}
                    {" · "}
                    {label(item.origin)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        <p style={{ marginTop: "1rem", opacity: 0.8 }}>
          {state.condition.message}
        </p>
      </section>
    </div>
  );
}


