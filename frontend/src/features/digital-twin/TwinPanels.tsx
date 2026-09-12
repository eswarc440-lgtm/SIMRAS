import { StatusPill } from "../../components/StatusPill";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

const empty = "â€”";

const ignoredDimensionKeys = new Set([
  "template",
  "representation",
  "source_basis",
  "source_references",
  "alignment_status",
  "structural_form",
  "dam_type",
]);

function score(value?: number | null) {
  return value != null ? (
    <>
      {value.toFixed(0)}
      <small>/100</small>
    </>
  ) : (
    empty
  );
}

function healthLabel(value?: number | null) {
  if (value == null) return "UNAVAILABLE";
  if (value >= 85) return "EXCELLENT";
  if (value >= 70) return "GOOD";
  if (value >= 55) return "MONITOR";
  if (value >= 40) return "POOR";
  return "CRITICAL";
}

function sourceBacked(twin: TwinResponse) {
  const representation = String(
    twin.twin.dimensions["representation"] ?? "",
  ).toLowerCase();

  return (
    twin.twin.fidelity_level !== "L0" &&
    twin.twin.is_asset_specific &&
    (
      Boolean(twin.twin.source_url) ||
      representation.includes("source_backed") ||
      representation.includes("source_extracted")
    )
  );
}

function dimName(key: string) {
  return key
    .replace(/_m3s$/, " (mÂ³/s)")
    .replace(/_m$/, " (m)")
    .replaceAll("_", " ");
}

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  const backed = sourceBacked(twin);

  const dimensions = Object.entries(twin.twin.dimensions).filter(
    ([key, value]) =>
      !ignoredDimensionKeys.has(key) &&
      value != null &&
      (
        typeof value === "number" ||
        typeof value === "string"
      ),
  );

  return (
    <div className="twin-panels">
      <section className="panel score-panel score-panel-four">
        <div>
          <span>SIMRAS predicted health</span>
          <strong>{score(twin.ai.health_score)}</strong>
          <small>{healthLabel(twin.ai.health_score)}</small>
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

        {(twin.asset.asset_type === "dam" || twin.asset.asset_type === "barrage") && (
          <div>
            <span>Operational / hydrologic risk</span>
            <strong style={{ color: riskColor(twin.ai.operational_risk_level) }}>
              {score(twin.ai.operational_risk_score)}
            </strong>
            <small>
              {twin.ai.operational_risk_score != null
                ? `${(twin.ai.operational_risk_level ?? "N/A").replaceAll("_", " ")} · ${twin.ai.operational_confidence != null ? `${Math.round(twin.ai.operational_confidence * 100)}% input confidence` : "confidence N/A"}`
                : "Insufficient hydrology inputs"}
            </small>
          </div>
        )}
        <div>
          <span>Prediction confidence</span>
          <strong>
            {twin.ai.confidence != null
              ? `${Math.round(twin.ai.confidence * 100)}%`
              : empty}
          </strong>
          <small>Prediction confidence Â· not official condition</small>
        </div>
      </section>

      <section className="panel">
        <header>
          <h3>Digital twin geometry & provenance</h3>
          <StatusPill
            label={twin.twin.fidelity_level}
            tone={backed ? "good" : "warn"}
          />
        </header>

        <dl>
          <div>
            <dt>Geometry status</dt>
            <dd>
              {backed
                ? "Source-driven asset-specific parametric representation"
                : "Illustrative only; no source-backed dimensions linked"}
            </dd>
          </div>

          <div>
            <dt>Model source</dt>
            <dd>
              {twin.twin.source_url ? (
                <a
                  href={twin.twin.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="model-source-link"
                >
                  {twin.twin.model_source} â†—
                </a>
              ) : (
                twin.twin.model_source
              )}
            </dd>
          </div>

          <div>
            <dt>Identity</dt>
            <dd>{twin.asset.identity_status}</dd>
          </div>

          <div>
            <dt>Accuracy statement</dt>
            <dd>
              {twin.twin.uri
                ? "Use source/model metadata for survey/BIM accuracy."
                : backed
                  ? "Dimensions follow linked records; unprovided geometry remains parametric/approximate."
                  : "Do not use visual proportions as engineering measurements."}
            </dd>
          </div>
        </dl>

        {backed && dimensions.length > 0 && (
          <div className="dimension-list">
            <h4>Source-backed dimensions / characteristics</h4>
            <dl>
              {dimensions.map(([key, value]) => (
                <div key={key}>
                  <dt>{dimName(key)}</dt>
                  <dd>{String(value).replaceAll("_", " ")}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
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
          label={
            twin.ai.model_validated
              ? "VALIDATED"
              : twin.ai.status
          }
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
    </div>
  );
}