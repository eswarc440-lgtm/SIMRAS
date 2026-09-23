import { StatusPill } from "../../components/StatusPill";
import type { TwinResponse } from "../../types/twin";
import { riskColor } from "../../utils";

const empty = "—";

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
  const twinObj = twin?.twin ?? (twin as any)?.model_metadata ?? {};
  const dimensions = (twinObj?.dimensions ?? (twin as any)?.dimensions ?? {}) as Record<string, unknown>;
  const representation = String(dimensions["representation"] ?? "").toLowerCase();

  return (
    twinObj?.fidelity_level !== "L0" &&
    (twinObj?.is_asset_specific ?? true) &&
    (
      Boolean(twinObj?.source_url) ||
      representation.includes("source_backed") ||
      representation.includes("source_extracted")
    )
  );
}

function dimName(key: string) {
  return key
    .replace(/_m3s$/, " (m³/s)")
    .replace(/_m$/, " (m)")
    .replaceAll("_", " ");
}

export function TwinPanels({ twin }: { twin: TwinResponse }) {
  if (!twin) return null;

  const twinObj = twin.twin ?? (twin as any).model_metadata ?? {};
  const dimsObj = (twinObj.dimensions ?? (twin as any).dimensions ?? {}) as Record<string, unknown>;
  const aiObj = twin.ai ?? ({} as any);
  const assetObj = twin.asset ?? ({} as any);

  const backed = sourceBacked(twin);

  const dimensions = Object.entries(dimsObj).filter(
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
          <strong>{score(aiObj.health_score ?? assetObj.health_score)}</strong>
          <small>{healthLabel(aiObj.health_score ?? assetObj.health_score)}</small>
        </div>

        <div>
          <span>SIMRAS risk score</span>
          <strong style={{ color: riskColor(aiObj.risk_level ?? assetObj.risk_level) }}>
            {score(aiObj.risk_score ?? assetObj.risk_score)}
          </strong>
          <small>{aiObj.risk_level ?? assetObj.risk_level ?? "UNAVAILABLE"}</small>
        </div>

        <div>
          <span>Environmental hazard</span>
          <strong style={{ color: riskColor(aiObj.hazard_level) }}>
            {score(aiObj.hazard_score)}
          </strong>
          <small>
            {aiObj.hazard_level ?? "NO VALIDATED HAZARD INPUT"}
          </small>
        </div>

        {(assetObj.asset_type === "dam" || assetObj.asset_type === "barrage") && (
          <div>
            <span>Operational / hydrologic risk</span>
            <strong style={{ color: riskColor(aiObj.operational_risk_level) }}>
              {score(aiObj.operational_risk_score)}
            </strong>
            <small>
              {aiObj.operational_risk_score != null
                ? `${(aiObj.operational_risk_level ?? "N/A").replaceAll("_", " ")} · ${aiObj.operational_confidence != null ? `${Math.round(aiObj.operational_confidence * 100)}% input confidence` : "confidence N/A"}`
                : "Insufficient hydrology inputs"}
            </small>
          </div>
        )}
        <div>
          <span>Prediction confidence</span>
          <strong>
            {aiObj.confidence != null
              ? `${Math.round(aiObj.confidence * 100)}%`
              : empty}
          </strong>
          <small>Prediction confidence · not official condition</small>
        </div>
      </section>

      <section className="panel">
        <header>
          <h3>Digital twin geometry & provenance</h3>
          <StatusPill
            label={twinObj.fidelity_level ?? "L1"}
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
              {twinObj.source_url ? (
                <a
                  href={twinObj.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="model-source-link"
                >
                  {twinObj.model_source ?? "Official Register"} ↗
                </a>
              ) : (
                twinObj.model_source ?? "Official Register"
              )}
            </dd>
          </div>

          <div>
            <dt>Identity</dt>
            <dd>{assetObj.identity_status ?? "OFFICIALLY_GAZETTED"}</dd>
          </div>

          <div>
            <dt>Accuracy statement</dt>
            <dd>
              {twinObj.uri
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
            {aiObj.model_validated
              ? "Validated model"
              : "SIMRAS research decision support"}
          </strong>
        </div>

        <div>
          <span>Engine</span>
          <strong>{aiObj.prediction_method ?? "Not available"}</strong>
        </div>

        <div>
          <span>Version</span>
          <strong>{aiObj.model_version ?? "simras-ai-v2.4"}</strong>
        </div>

        <StatusPill
          label={
            aiObj.model_validated
              ? "VALIDATED"
              : (aiObj.status ?? "OPERATIONAL")
          }
          tone={aiObj.model_validated ? "good" : "warn"}
        />
      </section>

      <section className="panel">
        <header>
          <h3>SIMRAS recommendations</h3>
          <StatusPill label="HUMAN REVIEW REQUIRED" tone="warn" />
        </header>

        <ul className="factor-list">
          {(aiObj.recommendations ?? []).map((item: string) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <header>
          <h3>Why this prediction?</h3>
          <StatusPill label={aiObj.status ?? "OPTIMAL"} tone="warn" />
        </header>

        <ul className="factor-list">
          {(aiObj.factors ?? []).map((item: string) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}