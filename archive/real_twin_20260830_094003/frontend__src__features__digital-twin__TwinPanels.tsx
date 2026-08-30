import { StatusPill } from "../../components/StatusPill";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

const unavailable = "—";

const metadataKeys = new Set([
  "representation",
  "source_basis",
  "source_references",
  "structural_form",
  "dam_type",
  "height_basis",
]);

function score(value?: number | null) {
  return value != null ? (
    <>
      {value.toFixed(0)}
      <small>/100</small>
    </>
  ) : (
    unavailable
  );
}

function healthClass(value?: number | null) {
  if (value == null) return "UNAVAILABLE";
  if (value >= 85) return "EXCELLENT";
  if (value >= 70) return "GOOD";
  if (value >= 55) return "MONITOR";
  if (value >= 40) return "POOR";
  return "CRITICAL";
}

function sourceBacked(twin: TwinResponse): boolean {
  const representation = String(
    twin.twin.dimensions["representation"] ?? "",
  ).toLowerCase();

  return Boolean(
    twin.twin.is_asset_specific &&
      twin.twin.source_url &&
      twin.twin.fidelity_level !== "L0" &&
      representation.includes("source_backed"),
  );
}

function label(key: string) {
  return key
    .replace(/_m3s$/, " (m³/s)")
    .replace(/_m$/, " (m)")
    .replaceAll("_", " ");
}

function valueText(value: unknown) {
  if (typeof value === "number") {
    return value.toLocaleString(undefined, {
      maximumFractionDigits: 3,
    });
  }

  return String(value).replaceAll("_", " ");
}

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  const backed = sourceBacked(twin);

  const dimensions = Object.entries(twin.twin.dimensions).filter(
    ([key, value]) =>
      !metadataKeys.has(key) &&
      value != null &&
      (typeof value === "number" || typeof value === "string"),
  );

  return (
    <div className="twin-panels">
      <section className="panel score-panel score-panel-four">
        <div>
          <span>SIMRAS predicted health</span>
          <strong>{score(twin.ai.health_score)}</strong>
          <small>{healthClass(twin.ai.health_score)}</small>
        </div>

        <div>
          <span>SIMRAS risk score</span>
          <strong style={{ color: riskColor(twin.ai.risk_level) }}>
            {score(twin.ai.risk_score)}
          </strong>
          <small>{twin.ai.risk_level ?? "UNAVAILABLE"}</small>
        </div>

        <div>
          <span>Environmental hazard</span>
          <strong style={{ color: riskColor(twin.ai.hazard_level) }}>
            {score(twin.ai.hazard_score)}
          </strong>
          <small>
            {twin.ai.hazard_level ?? "NO VALIDATED HAZARD INPUT"}
          </small>
        </div>

        <div>
          <span>Prediction confidence</span>
          <strong>
            {twin.ai.confidence != null
              ? `${Math.round(twin.ai.confidence * 100)}%`
              : unavailable}
          </strong>
          <small>Model/data confidence, not official condition</small>
        </div>
      </section>

      <section className="panel prediction-disclosure">
        <div>
          <span>Prediction layer</span>
          <strong>
            {twin.ai.model_validated
              ? "Validated model"
              : "SIMRAS research decision support"}
          </strong>
        </div>

        <div>
          <span>Engine</span>
          <strong>{twin.ai.prediction_method ?? "Not available"}</strong>
        </div>

        <div>
          <span>Version</span>
          <strong>{twin.ai.model_version}</strong>
        </div>

        <StatusPill
          label={twin.ai.model_validated ? "VALIDATED" : twin.ai.status}
          tone={twin.ai.model_validated ? "good" : "warn"}
        />
      </section>

      <section className="panel">
        <header>
          <h3>SIMRAS recommendations</h3>
          <StatusPill label="HUMAN REVIEW REQUIRED" tone="warn" />
        </header>

        <ul className="factor-list">
          {(twin.ai.recommendations ?? []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <header>
          <h3>Why this prediction?</h3>
          <StatusPill label={twin.ai.status} tone="warn" />
        </header>

        <ul className="factor-list">
          {twin.ai.factors.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="panel provenance-panel">
        <header>
          <h3>Digital twin & provenance</h3>
          <StatusPill
            label={twin.asset.identity_status}
            tone={twin.asset.identity_status === "VERIFIED" ? "good" : "warn"}
          />
        </header>

        <dl>
          <div>
            <dt>3D fidelity</dt>
            <dd>
              {twin.twin.fidelity_level}
              {" · "}
              {backed
                ? "source-backed dimensional representation"
                : "illustrative type representation"}
            </dd>
          </div>

          <div>
            <dt>Model source</dt>
            <dd>
              {twin.twin.source_url ? (
                <a
                  className="model-source-link"
                  href={twin.twin.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {twin.twin.model_source} ↗
                </a>
              ) : (
                "No source-backed geometry linked"
              )}
            </dd>
          </div>

          <div>
            <dt>Geometry truth status</dt>
            <dd>
              {backed
                ? "L1 dimension-derived approximation; not survey/BIM/LiDAR accuracy"
                : "L0 illustrative; visual proportions must not be read as engineering measurements"}
            </dd>
          </div>

          <div>
            <dt>Structural sensors</dt>
            <dd>{twin.sensors_status.replaceAll("_", " ")}</dd>
          </div>

          <div>
            <dt>Inspection</dt>
            <dd>{twin.inspection.quality_flag.replaceAll("_", " ")}</dd>
          </div>

          <div>
            <dt>RUL</dt>
            <dd>Disabled until longitudinal Andhra Pradesh validation</dd>
          </div>
        </dl>

        {backed && dimensions.length > 0 && (
          <div className="dimension-list">
            <h4>Source-backed model dimensions</h4>

            <dl>
              {dimensions.map(([key, value]) => (
                <div key={key}>
                  <dt>{label(key)}</dt>
                  <dd>{valueText(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>
    </div>
  );
}
