import { StatusPill } from "../../components/StatusPill";
import type { TwinResponse } from "../../types/twin";
import { formatValue, riskColor } from "../../utils";

const unavailable = "—";

function dimensionLabel(key: string) {
  return key
    .replace(/_m$/, " (m)")
    .replaceAll("_", " ");
}

function dimensionValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toString()
      : value.toFixed(2);
  }

  return String(value).replaceAll("_", " ");
}

function scoreValue(value?: number | null) {
  return value != null ? (
    <>
      {value.toFixed(1)}
      <small>/100</small>
    </>
  ) : (
    unavailable
  );
}

function percentageValue(value?: number | null) {
  return value != null
    ? `${value.toFixed(1)}%`
    : unavailable;
}

function formatTimestamp(value?: string | null) {
  if (!value) return unavailable;

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function TwinPanels({
  twin,
}: {
  twin: TwinResponse;
}) {
  const dimensions = Object.entries(
    twin.twin.dimensions,
  ).filter(([key]) => key !== "representation");

  const isResearchTransfer =
    twin.ai.status === "RESEARCH_TRANSFER";

  const isPersisted =
    twin.ai.prediction_method === "persisted_bridge_ml";

  const rul = twin.ai.remaining_life_years;

  const rulInterval =
    twin.ai.rul_lower_bound != null &&
    twin.ai.rul_upper_bound != null
      ? `${twin.ai.rul_lower_bound.toFixed(1)} – ${twin.ai.rul_upper_bound.toFixed(1)} years`
      : null;

  const healthInterval =
    twin.ai.health_lower_bound != null &&
    twin.ai.health_upper_bound != null
      ? `${twin.ai.health_lower_bound.toFixed(1)} – ${twin.ai.health_upper_bound.toFixed(1)}`
      : null;

  const hasSyntheticEnvironment =
    Object.values(twin.environment).some(
      (item) =>
        item.source_type === "SYNTHETIC_DEMO" ||
        item.is_estimated,
    );

  return (
    <div className="twin-panels">
      <section className="panel score-panel score-panel-four">
        <div>
          <span>Health score</span>

          <strong>
            {scoreValue(twin.ai.health_score)}
          </strong>

          {healthInterval && (
            <small>
              Prediction interval {healthInterval}
            </small>
          )}
        </div>

        <div>
          <span>
            {isResearchTransfer
              ? `Poor-condition probability (${twin.ai.forecast_horizon_years ?? 3}y)`
              : "Structural risk"}
          </span>

          <strong
            style={{
              color: riskColor(twin.ai.risk_level),
            }}
          >
            {percentageValue(twin.ai.risk_score)}
          </strong>

          <small>
            {twin.ai.risk_level ?? "Not classified"}
          </small>
        </div>

        <div>
          <span>Environment hazard</span>

          <strong
            style={{
              color: riskColor(twin.ai.hazard_level),
            }}
          >
            {scoreValue(twin.ai.hazard_score)}
          </strong>

          <small>
            {twin.ai.hazard_level ?? "Not classified"}
          </small>
        </div>

        <div>
          <span>AI confidence</span>

          <strong>
            {twin.ai.confidence != null
              ? `${Math.round(
                  twin.ai.confidence * 100,
                )}%`
              : unavailable}
          </strong>

          <small>Evidence/model confidence</small>
        </div>
      </section>

      <section className="panel prediction-disclosure">
        <header>
          <h3>AI prediction state</h3>

          <StatusPill
            label={
              twin.ai.model_validated
                ? "VALIDATED"
                : twin.ai.status
            }
            tone={
              twin.ai.model_validated
                ? "good"
                : "warn"
            }
          />
        </header>

        <div>
          <span>Prediction source</span>
          <strong>
            {isPersisted
              ? "Persisted PostgreSQL prediction"
              : twin.ai.prediction_method ??
                "Not available"}
          </strong>
        </div>

        <div>
          <span>Model version</span>
          <strong>{twin.ai.model_version}</strong>
        </div>

        <div>
          <span>Feature version</span>
          <strong>
            {twin.ai.feature_version}
          </strong>
        </div>

        <div>
          <span>Prediction generated</span>
          <strong>
            {formatTimestamp(
              twin.ai.prediction_time,
            )}
          </strong>
        </div>

        <div>
          <span>Local validation</span>
          <strong>
            {twin.ai.model_validated
              ? "Validated"
              : "Pending Andhra Pradesh validation"}
          </strong>
        </div>

        {isResearchTransfer && (
          <div className="research-warning">
            <strong>Research decision support</strong>
            <small>
              This bridge model is transferred from
              FHWA/NBI histories and is not yet locally
              validated for Andhra Pradesh.
            </small>
          </div>
        )}
      </section>

      <section className="panel prediction-disclosure">
        <header>
          <h3>Remaining-life estimate</h3>

          <StatusPill
            label={
              twin.ai.model_validated
                ? "VALIDATED"
                : "EXPERIMENTAL"
            }
            tone={
              twin.ai.model_validated
                ? "good"
                : "warn"
            }
          />
        </header>

        <div>
          <span>
            Years to poor-condition threshold
          </span>

          <strong>
            {rul != null
              ? `${rul.toFixed(1)} years`
              : unavailable}
          </strong>

          {rulInterval && (
            <small>
              Experimental interval {rulInterval}
            </small>
          )}
        </div>

        <div>
          <span>Forecast horizon</span>

          <strong>
            {twin.ai.forecast_horizon_years != null
              ? `${twin.ai.forecast_horizon_years} years`
              : unavailable}
          </strong>
        </div>

        <div>
          <span>Training scope</span>

          <strong>
            {twin.ai.training_scope?.replaceAll(
              "_",
              " ",
            ) ?? unavailable}
          </strong>
        </div>

        {!twin.ai.model_validated && (
          <small>
            RUL is an experimental research estimate,
            not an engineering-certified remaining-life
            assessment.
          </small>
        )}
      </section>

      <section className="panel">
        <header>
          <h3>Current environment</h3>

          <StatusPill
            label={twin.freshness.environment}
          />
        </header>

        {hasSyntheticEnvironment && (
          <div className="research-warning">
            <strong>
              Demonstration environmental data
            </strong>

            <small>
              One or more values are synthetic,
              estimated, or unverified and must not be
              interpreted as current field
              measurements.
            </small>
          </div>
        )}

        <div className="metric-grid">
          {Object.entries(twin.environment).map(
            ([key, item]) => (
              <article key={key}>
                <span>
                  {key.replaceAll("_", " ")}
                </span>

                <strong>
                  {formatValue(
                    item.value,
                    item.unit,
                  )}
                </strong>

                <small>
                  {item.source_type.replaceAll(
                    "_",
                    " ",
                  )}
                  {" · "}
                  {item.source}
                </small>

                <small>
                  Confidence:{" "}
                  {item.confidence != null
                    ? `${Math.round(
                        item.confidence * 100,
                      )}%`
                    : unavailable}
                </small>
              </article>
            ),
          )}

          {Object.keys(twin.environment).length ===
            0 && (
            <p>
              No environmental feed is currently
              matched to this asset.
            </p>
          )}
        </div>
      </section>

      <section className="panel">
        <header>
          <h3>Inspection state</h3>

          <StatusPill
            label={
              twin.inspection.is_synthetic
                ? "SYNTHETIC"
                : twin.inspection.quality_flag
            }
            tone={
              twin.inspection.is_synthetic
                ? "warn"
                : "good"
            }
          />
        </header>

        <dl>
          <div>
            <dt>Date</dt>
            <dd>
              {twin.inspection.inspection_date ??
                unavailable}
            </dd>
          </div>

          <div>
            <dt>Condition</dt>
            <dd>
              {twin.inspection.condition ??
                unavailable}
            </dd>
          </div>

          <div>
            <dt>Inspection score</dt>
            <dd>
              {twin.inspection.score != null
                ? `${twin.inspection.score.toFixed(
                    1,
                  )}/100`
                : unavailable}
            </dd>
          </div>

          <div>
            <dt>Quality flag</dt>
            <dd>
              {twin.inspection.quality_flag.replaceAll(
                "_",
                " ",
              )}
            </dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <header>
          <h3>Recommendations</h3>

          <StatusPill
            label={
              twin.ai.model_validated
                ? "VALIDATED"
                : "HUMAN REVIEW REQUIRED"
            }
            tone={
              twin.ai.model_validated
                ? "good"
                : "warn"
            }
          />
        </header>

        <ul className="factor-list">
          {(twin.ai.recommendations ?? []).map(
            (recommendation) => (
              <li key={recommendation}>
                {recommendation}
              </li>
            ),
          )}
        </ul>
      </section>

      <section className="panel">
        <header>
          <h3>Decision-support factors</h3>

          <StatusPill
            label={twin.ai.status}
            tone={
              twin.ai.model_validated
                ? "good"
                : "warn"
            }
          />
        </header>

        <ul className="factor-list">
          {twin.ai.factors.map((factor) => (
            <li key={factor}>{factor}</li>
          ))}
        </ul>
      </section>

      <section className="panel provenance-panel">
        <header>
          <h3>Reality & provenance</h3>

          <StatusPill
            label={twin.asset.identity_status}
            tone={
              twin.asset.identity_status ===
              "VERIFIED"
                ? "good"
                : "warn"
            }
          />
        </header>

        <dl>
          <div>
            <dt>3D fidelity</dt>
            <dd>
              {twin.twin.fidelity_level}
              {" · "}
              {twin.twin.model_source}
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
                  Published engineering source ↗
                </a>
              ) : (
                unavailable
              )}
            </dd>
          </div>

          <div>
            <dt>Asset identity</dt>
            <dd>
              {twin.asset.identity_status.replaceAll(
                "_",
                " ",
              )}
            </dd>
          </div>

          <div>
            <dt>Asset data confidence</dt>
            <dd>
              {twin.asset.data_confidence != null
                ? `${Math.round(
                    twin.asset.data_confidence *
                      100,
                  )}%`
                : unavailable}
            </dd>
          </div>

          <div>
            <dt>Structural sensors</dt>
            <dd>
              {twin.sensors_status.replaceAll(
                "_",
                " ",
              )}
            </dd>
          </div>

          <div>
            <dt>RUL status</dt>
            <dd>
              {rul != null
                ? `${rul.toFixed(1)} years${
                    rulInterval
                      ? ` (${rulInterval})`
                      : ""
                  } — ${
                    twin.ai.model_validated
                      ? "validated"
                      : "experimental"
                  }`
                : "Unavailable"}
            </dd>
          </div>
        </dl>

        {dimensions.length > 0 && (
          <div className="dimension-list">
            <h4>Published model dimensions</h4>

            <dl>
              {dimensions.map(
                ([key, value]) => (
                  <div key={key}>
                    <dt>
                      {dimensionLabel(key)}
                    </dt>

                    <dd>
                      {dimensionValue(value)}
                    </dd>
                  </div>
                ),
              )}
            </dl>
          </div>
        )}
      </section>
    </div>
  );
}