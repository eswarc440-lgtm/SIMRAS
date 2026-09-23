type Dict = Record<string, unknown>;

function record(value: unknown): Dict {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Dict)
    : {};
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function numberValue(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readable(value: unknown, fallback = "N/A"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value).replaceAll("_", " ");
}

function score(value: unknown): string {
  const parsed = numberValue(value);
  return parsed === null ? "WITHHELD" : `${parsed.toFixed(1)}/100`;
}

function confidence(value: unknown): string {
  const parsed = numberValue(value);
  if (parsed === null) return "N/A";
  const normalized = Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
  return `${Math.round(normalized)}%`;
}

function SourceRow({ source }: { source: Dict }) {
  const url = readable(source.document_url, "");
  const title =
    readable(source.document_title, "") ||
    readable(source.source_name, "") ||
    readable(source.source_code, "Government source");

  return (
    <div className="real-report-source-row">
      <div>
        <strong>{title}</strong>
        <small>
          {readable(source.source_code)}
          {" · "}
          {readable(source.quality_flag)}
          {source.observed_at ? ` · ${readable(source.observed_at)}` : ""}
        </small>
      </div>
      {url ? (
        <a href={url} target="_blank" rel="noreferrer">
          Source ↗
        </a>
      ) : null}
    </div>
  );
}

export function ReportDecisionSupport({ report }: { report: unknown }) {
  const root = record(report);
  const ds = record(root.decision_support);
  if (!ds.contract_version) return null;

  const prediction = record(ds.prediction);
  const structural = record(prediction.structural);
  const operational = record(prediction.operational_hydrologic);
  const hazard = record(prediction.environmental_hazard);
  const rul = record(prediction.remaining_useful_life);
  const model = record(ds.model);
  const governmentEvidence = record(ds.government_evidence);
  const governmentRecords = list(governmentEvidence.records).map(record);
  const requirements = list(ds.required_evidence).map(record);
  const actions = list(ds.recommended_actions).map(record);
  const guidance = list(ds.government_guidance).map(record);

  const structuralAvailable = structural.available === true;
  const operationalAvailable = operational.available === true;

  return (
    <section className="real-report-decision-support">
      <header className="real-report-section-header">
        <div>
          <span>REAL EVIDENCE + MODEL DECISION SUPPORT</span>
          <h3>Prediction, recommendations & required evidence</h3>
          <p>
            Uses the selected asset&apos;s canonical source-backed state. Missing
            engineering evidence stays withheld instead of being generated.
          </p>
        </div>
        <strong>{readable(model.applicability)}</strong>
      </header>

      <div className="real-report-kpi-grid">
        <article>
          <span>Structural health</span>
          <strong>{structuralAvailable ? score(structural.health_score) : "WITHHELD"}</strong>
          <small>{readable(structural.reason)}</small>
        </article>
        <article>
          <span>Structural risk</span>
          <strong>{structuralAvailable ? score(structural.risk_score) : "WITHHELD"}</strong>
          <small>{readable(structural.risk_level)}</small>
        </article>
        <article>
          <span>Operational / hydrologic risk</span>
          <strong>{operationalAvailable ? score(operational.risk_score) : "N/A"}</strong>
          <small>
            {readable(operational.risk_level)}
            {operational.confidence != null
              ? ` · ${confidence(operational.confidence)} confidence`
              : ""}
          </small>
        </article>
        <article>
          <span>Environmental hazard</span>
          <strong>{hazard.available === true ? score(hazard.score) : "N/A"}</strong>
          <small>{readable(hazard.level)}</small>
        </article>
        <article>
          <span>Prediction confidence</span>
          <strong>{confidence(prediction.prediction_confidence)}</strong>
          <small>Input/model confidence — not an official rating</small>
        </article>
      </div>

      <div className="real-report-two-column">
        <article className="real-report-card">
          <span className="real-report-kicker">MODEL GOVERNANCE</span>
          <h4>Prediction basis</h4>
          <dl>
            <div><dt>Method</dt><dd>{readable(model.prediction_method)}</dd></div>
            <div><dt>Version</dt><dd>{readable(model.model_version)}</dd></div>
            <div><dt>Stage</dt><dd>{readable(model.stage)}</dd></div>
            <div>
              <dt>AP/local validation</dt>
              <dd>{model.locally_validated === true ? "VALIDATED LOCAL" : "NOT ESTABLISHED / TRANSFER"}</dd>
            </div>
          </dl>
        </article>

        <article className="real-report-card">
          <span className="real-report-kicker">RUL / DETERIORATION HORIZON</span>
          <h4>{readable(rul.status)}</h4>
          {(rul.status === "AVAILABLE" || rul.status === "RESEARCH_TRANSFER") ? (
            <>
              <dl>
                <div><dt>Estimate</dt><dd>{readable(rul.estimate_years)} years</dd></div>
                <div>
                  <dt>Range</dt>
                  <dd>
                    {readable(rul.lower_bound_years)} - {readable(rul.upper_bound_years)} years
                  </dd>
                </div>
                <div><dt>Mode</dt><dd>{readable(rul.mode)}</dd></div>
                <div><dt>Confidence</dt><dd>{confidence(rul.confidence)}</dd></div>
              </dl>
              <p>{readable(rul.reason)}</p>
            </>
          ) : (
            <p>{readable(rul.reason)}</p>
          )}
        </article>
      </div>

      <article className="real-report-card">
        <span className="real-report-kicker">RECOMMENDED ACTIONS</span>
        <h4>What is necessary next</h4>
        <div className="real-report-actions">
          {actions.length ? actions.map((item, index) => (
            <div key={`${readable(item.priority)}-${index}`}>
              <strong>{readable(item.priority)}</strong>
              <div>
                <b>{readable(item.action)}</b>
                <small>{readable(item.reason)}</small>
                <small>Basis: {readable(item.basis)}</small>
              </div>
            </div>
          )) : <p>No additional action was generated from the available evidence.</p>}
        </div>
      </article>

      <div className="real-report-two-column">
        <article className="real-report-card">
          <span className="real-report-kicker">EVIDENCE COMPLETENESS</span>
          <h4>Required engineering inputs</h4>
          <div className="real-report-requirements">
            {requirements.map((item, index) => (
              <div key={`${readable(item.item)}-${index}`}>
                <span>{readable(item.item)}</span>
                <strong>{readable(item.status)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="real-report-card">
          <span className="real-report-kicker">GOVERNMENT-LINKED EVIDENCE</span>
          <h4>Records used by the selected-asset report</h4>
          {governmentRecords.length ? (
            <div className="real-report-sources">
              {governmentRecords.map((source, index) => (
                <SourceRow key={`${readable(source.source_code)}-${index}`} source={source} />
              ))}
            </div>
          ) : (
            <p>No qualifying government source record is linked in this report payload.</p>
          )}
          <small>{readable(governmentEvidence.note)}</small>
        </article>
      </div>

      {guidance.length ? (
        <article className="real-report-card">
          <span className="real-report-kicker">OFFICIAL GUIDANCE REFERENCES</span>
          <h4>Government documents used to frame recommendations</h4>
          <div className="real-report-guidance">
            {guidance.map((item, index) => (
              <a
                key={`${readable(item.title)}-${index}`}
                href={readable(item.url, "#")}
                target="_blank"
                rel="noreferrer"
              >
                <strong>{readable(item.title)}</strong>
                <small>{readable(item.authority)}</small>
                <span>{readable(item.role)}</span>
              </a>
            ))}
          </div>
        </article>
      ) : null}

      <div className="real-report-disclaimer">
        <strong>Interpretation boundary</strong>
        <p>{readable(ds.disclaimer)}</p>
      </div>
    </section>
  );
}
