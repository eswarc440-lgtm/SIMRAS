import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Database,
  Download,
  FileText,
  Printer,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import type { AssetSummary, TwinResponse } from "../../types/twin";
import { API_BASE_URL, apiRequest } from "../../services/api";

type Props = {
  selected?: AssetSummary;
  twin?: TwinResponse;
};

type Point = {
  timestamp?: string | null;
  value?: number | null;
  lower_bound?: number | null;
  upper_bound?: number | null;
};

type Assessment = {
  schema_version: string;
  report_id: string;
  generated_at: string;
  asset: {
    id: number;
    asset_code: string;
    name: string;
    asset_type: string;
    subtype?: string | null;
    district?: string | null;
    owner?: string | null;
    status?: string | null;
    identity_status?: string | null;
    built_year?: number | null;
    material?: string | null;
  };
  health: {
    score?: number | null;
    category: string;
    lower_bound?: number | null;
    upper_bound?: number | null;
    factors: string[];
    trend: string;
    history: Point[];
    available: boolean;
  };
  risk: {
    score?: number | null;
    level: string;
    confidence?: number | null;
    poor_condition_probability?: number | null;
    failure_probability?: number | null;
    failure_probability_note?: string | null;
    factors: string[];
    trend: string;
    history: Point[];
    available: boolean;
  };
  rul: {
    estimate?: number | null;
    unit: string;
    lower_bound?: number | null;
    upper_bound?: number | null;
    confidence?: number | null;
    status?: string | null;
    basis?: string | null;
    trend: string;
    history: Point[];
    available: boolean;
  };
  explainability: {
    model_inputs: Array<{
      factor: string;
      current_value?: unknown;
      unit?: string | null;
      expected_range?: string | null;
      difference_from_expected?: string | null;
      impact?: string | null;
      contribution?: number | null;
      used_by_model: boolean;
      source?: string | null;
    }>;
    model_explanation_notes: string[];
    signed_contributions_available: boolean;
    signed_contribution_note: string;
  };
  government_evidence: {
    records: Array<{
      kind: string;
      regulation_or_standard?: string | null;
      evidence_or_requirement?: string | null;
      current_measured_value?: string | null;
      applicable_threshold?: string | null;
      compliance_status?: string | null;
      source_reference?: string | null;
      reference_url?: string | null;
      observed_at?: string | null;
    }>;
    verified_record_count: number;
    verified_standard_count: number;
    message?: string | null;
    threshold_note: string;
  };
  recommendations: Array<{
    recommendation: string;
    priority: string;
    priority_basis?: string | null;
    reason: string;
    supporting_evidence: string[];
    expected_benefit?: string | null;
    suggested_timeframe?: string | null;
    source: string;
  }>;
  supporting_data: Array<{
    name: string;
    current_value?: unknown;
    unit?: string | null;
    expected_range?: string | null;
    reference_type?: string | null;
    difference_from_expected?: string | null;
    status?: string | null;
    trend?: string | null;
    last_updated?: string | null;
    source?: string | null;
    used_by_model: boolean;
    history: Point[];
  }>;
  transparency: {
    prediction?: string | null;
    confidence?: number | null;
    model_name?: string | null;
    model_version?: string | null;
    feature_version?: string | null;
    model_stage?: string | null;
    prediction_method?: string | null;
    prediction_generated_at?: string | null;
    data_points_used: number;
    model_input_count: number;
    evidence_record_count: number;
    model_validated: boolean;
    training_scope?: string | null;
  };
};

function label(value: unknown, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value).replaceAll("_", " ");
}

function dateTime(value?: string | null) {
  if (!value) return "N/A";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function percent(value?: number | null) {
  if (value == null) return "N/A";
  const scaled = Math.abs(value) <= 1 ? value * 100 : value;
  return `${Math.round(scaled)}%`;
}

function score(value?: number | null) {
  return value == null ? "N/A" : `${Math.round(value)}/100`;
}

function valueWithUnit(value: unknown, unit?: string | null) {
  if (value === null || value === undefined || value === "") return "N/A";
  return `${String(value)}${unit ? ` ${unit}` : ""}`;
}

function tone(value?: string | null) {
  const upper = String(value ?? "").toUpperCase();
  if (["EXCELLENT", "GOOD", "LOW", "VALID", "AVAILABLE", "ACTIVE"].includes(upper)) {
    return "good";
  }
  if (["WARNING", "MEDIUM", "MONITOR", "RESEARCH_TRANSFER"].includes(upper)) {
    return "warn";
  }
  if (["HIGH", "CRITICAL", "POOR", "INVALID"].includes(upper)) {
    return "bad";
  }
  return "neutral";
}

function Badge({ value }: { value?: string | null }) {
  return (
    <span className={`ai-report-badge tone-${tone(value)}`}>
      {label(value)}
    </span>
  );
}

function MiniTrend({
  points,
  ariaLabel,
}: {
  points: Point[];
  ariaLabel: string;
}) {
  const usable = points
    .map((point) => Number(point.value))
    .filter((value) => Number.isFinite(value));

  if (usable.length < 2) {
    return (
      <div className="ai-report-no-trend">
        No historical trend available
      </div>
    );
  }

  const min = Math.min(...usable);
  const max = Math.max(...usable);
  const span = Math.max(max - min, 1e-9);
  const width = 320;
  const height = 88;

  const coordinates = usable.map((value, index) => {
    const x =
      usable.length === 1
        ? width / 2
        : (index / (usable.length - 1)) * width;
    const y =
      height -
      8 -
      ((value - min) / span) * (height - 16);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg
      className="ai-report-mini-trend"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel}
    >
      <polyline
        points={coordinates.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function HealthRing({
  scoreValue,
  category,
}: {
  scoreValue?: number | null;
  category: string;
}) {
  const actual = Math.max(
    0,
    Math.min(100, Number(scoreValue ?? 0)),
  );
  const style = {
    "--health-score": `${actual}%`,
  } as CSSProperties;

  return (
    <div
      className={`ai-report-health-ring tone-${tone(category)}`}
      style={style}
    >
      <div>
        <strong>
          {scoreValue == null ? "N/A" : Math.round(scoreValue)}
        </strong>
        <span>/100</span>
      </div>
    </div>
  );
}

function TrendPanel({
  title,
  points,
  trend,
  unit,
}: {
  title: string;
  points: Point[];
  trend: string;
  unit: string;
}) {
  return (
    <article className="ai-report-trend-card">
      <header>
        <span>{title}</span>
        <Badge value={trend} />
      </header>
      <MiniTrend
        points={points}
        ariaLabel={`${title} historical trend`}
      />
      <small>
        {points.length
          ? `${points.length} stored prediction point(s) · ${unit}`
          : "No stored prediction history"}
      </small>
    </article>
  );
}

export function SelectedAssetReports({
  selected,
  twin,
}: Props) {
  const selectedCode =
    selected?.asset_code ?? twin?.asset.asset_code;

  const [report, setReport] = useState<Assessment>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [downloading, setDownloading] =
    useState<"pdf" | "docx">();

  const assessmentPath = useMemo(
    () =>
      selectedCode
        ? `/api/v1/reports/assets/${encodeURIComponent(
            selectedCode,
          )}/assessment`
        : undefined,
    [selectedCode],
  );

  useEffect(() => {
    if (!assessmentPath) {
      setReport(undefined);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(undefined);
    setReport(undefined);

    apiRequest<Assessment>(assessmentPath)
      .then((payload) => {
        if (!cancelled) setReport(payload);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        const message =
          reason &&
          typeof reason === "object" &&
          "message" in reason
            ? String(
                (reason as { message?: unknown }).message,
              )
            : String(reason);
        setError(message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [assessmentPath]);

  async function download(format: "pdf" | "docx") {
    if (!assessmentPath || !selectedCode) return;

    setDownloading(format);
    setError(undefined);

    try {
      const response = await fetch(
        `${API_BASE_URL}${assessmentPath}/${format}`,
        {
          headers: {
            Accept:
              format === "pdf"
                ? "application/pdf"
                : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          },
        },
      );

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(
          detail ||
            `${format.toUpperCase()} export failed with HTTP ${response.status}`,
        );
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = `${selectedCode}-SIMRAS-Asset-Health-Assessment.${
        format === "docx" ? "docx" : "pdf"
      }`;

      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (cause: unknown) {
      setError(
        cause instanceof Error ? cause.message : String(cause),
      );
    } finally {
      setDownloading(undefined);
    }
  }

  if (!selectedCode) {
    return (
      <section className="ai-report-shell">
        <div className="ai-report-empty">
          <FileText className="size-8" />
          <strong>
            Select an asset to generate its health assessment
            report.
          </strong>
        </div>
      </section>
    );
  }

  return (
    <section className="ai-report-shell">
      {loading && (
        <div className="ai-report-loading">
          <Activity className="size-5" />
          <span>
            Building the live asset health assessment from
            current backend data…
          </span>
        </div>
      )}

      {error && (
        <div className="ai-report-error">
          <AlertTriangle className="size-5" />
          <div>
            <strong>Report could not be loaded</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {report && (
        <div className="ai-report-document">
          <header className="ai-report-header">
            <div>
              <span className="ai-report-kicker">
                AI-POWERED ASSET HEALTH ASSESSMENT
              </span>
              <h2>{report.asset.name}</h2>
              <p>
                {report.asset.asset_code} ·{" "}
                {label(report.asset.asset_type)} ·{" "}
                {label(
                  report.asset.district,
                  "District N/A",
                )}
              </p>
            </div>

            <div className="ai-report-header-meta">
              <div>
                <span>Report ID</span>
                <strong>{report.report_id}</strong>
              </div>
              <div>
                <span>Generated</span>
                <strong>
                  {dateTime(report.generated_at)}
                </strong>
              </div>
              <div>
                <span>Asset status</span>
                <Badge value={report.asset.status} />
              </div>
            </div>
          </header>

          <div className="ai-report-export-bar">
            <button
              type="button"
              onClick={() => download("pdf")}
              disabled={Boolean(downloading)}
            >
              <Download className="size-4" />
              {downloading === "pdf"
                ? "Preparing PDF…"
                : "Download PDF"}
            </button>

            <button
              type="button"
              onClick={() => download("docx")}
              disabled={Boolean(downloading)}
            >
              <FileText className="size-4" />
              {downloading === "docx"
                ? "Preparing Word…"
                : "Download Word"}
            </button>

            <button
              type="button"
              onClick={() => window.print()}
            >
              <Printer className="size-4" />
              Print Report
            </button>
          </div>

          <section className="ai-report-priority-grid">
            <article className="ai-report-health-card">
              <div>
                <span className="ai-report-section-label">
                  1 · HEALTH SCORE
                </span>
                <h3>Asset health</h3>
                <Badge value={report.health.category} />
                <p>
                  {report.health.lower_bound != null &&
                  report.health.upper_bound != null
                    ? `Prediction interval ${report.health.lower_bound}–${report.health.upper_bound}/100`
                    : "Prediction interval is not available in the current model output."}
                </p>
              </div>
              <HealthRing
                scoreValue={report.health.score}
                category={report.health.category}
              />
            </article>

            <article className="ai-report-risk-card">
              <span className="ai-report-section-label">
                2 · RISK ASSESSMENT
              </span>
              <div className="ai-report-card-title">
                <h3>{label(report.risk.level)}</h3>
                <Badge value={report.risk.level} />
              </div>
              <dl>
                <div>
                  <dt>Risk score</dt>
                  <dd>{score(report.risk.score)}</dd>
                </div>
                <div>
                  <dt>Risk confidence</dt>
                  <dd>
                    {percent(report.risk.confidence)}
                  </dd>
                </div>
                <div>
                  <dt>Poor-condition probability</dt>
                  <dd>
                    {report.risk
                      .poor_condition_probability == null
                      ? "N/A"
                      : `${Math.round(
                          report.risk
                            .poor_condition_probability,
                        )}%`}
                  </dd>
                </div>
                <div>
                  <dt>Structural failure probability</dt>
                  <dd>
                    {report.risk.failure_probability == null
                      ? "Not separately available"
                      : `${Math.round(
                          report.risk
                            .failure_probability,
                        )}%`}
                  </dd>
                </div>
              </dl>
              <small>
                {report.risk.failure_probability_note}
              </small>
            </article>

            <article className="ai-report-rul-card">
              <span className="ai-report-section-label">
                3 · REMAINING USEFUL LIFE
              </span>
              <h3>
                {report.rul.estimate == null
                  ? "N/A"
                  : `${report.rul.estimate} ${report.rul.unit}`}
              </h3>
              <Badge value={report.rul.status} />
              <dl>
                <div>
                  <dt>Confidence range</dt>
                  <dd>
                    {report.rul.lower_bound == null ||
                    report.rul.upper_bound == null
                      ? "N/A"
                      : `${report.rul.lower_bound}–${report.rul.upper_bound} ${report.rul.unit}`}
                  </dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>
                    {percent(report.rul.confidence)}
                  </dd>
                </div>
              </dl>
              {report.rul.basis && (
                <small>{report.rul.basis}</small>
              )}
            </article>
          </section>

          <section className="ai-report-trends">
            <TrendPanel
              title="Health trend"
              points={report.health.history}
              trend={report.health.trend}
              unit="/100"
            />
            <TrendPanel
              title="Risk trend"
              points={report.risk.history}
              trend={report.risk.trend}
              unit="/100"
            />
            <TrendPanel
              title="RUL trend"
              points={report.rul.history}
              trend={report.rul.trend}
              unit={report.rul.unit}
            />
          </section>

          <section className="ai-report-panel">
            <header className="ai-report-panel-header">
              <div>
                <span className="ai-report-section-label">
                  4 · EXPLAINABLE AI
                </span>
                <h3>
                  Why did the AI make this prediction?
                </h3>
              </div>
              <BrainCircuit className="size-5" />
            </header>

            <div className="ai-report-table-wrap">
              <table className="ai-report-table">
                <thead>
                  <tr>
                    <th>Factor</th>
                    <th>Current value</th>
                    <th>Expected / reference range</th>
                    <th>Difference</th>
                    <th>Impact on prediction</th>
                    <th>Contribution</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {report.explainability.model_inputs.map(
                    (item) => (
                      <tr key={item.factor}>
                        <td>
                          <strong>{item.factor}</strong>
                          {item.used_by_model && (
                            <span className="ai-report-inline-chip">
                              MODEL INPUT
                            </span>
                          )}
                        </td>
                        <td>
                          {valueWithUnit(
                            item.current_value,
                            item.unit,
                          )}
                        </td>
                        <td>
                          {item.expected_range ?? "N/A"}
                        </td>
                        <td>
                          {item.difference_from_expected ??
                            "N/A"}
                        </td>
                        <td>{item.impact ?? "N/A"}</td>
                        <td>
                          {item.contribution == null
                            ? "Not stored"
                            : item.contribution}
                        </td>
                        <td>{item.source ?? "N/A"}</td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>

            {report.explainability
              .model_explanation_notes.length > 0 && (
              <div className="ai-report-factor-notes">
                {report.explainability.model_explanation_notes.map(
                  (factor) => (
                    <div key={factor}>{factor}</div>
                  ),
                )}
              </div>
            )}

            {!report.explainability
              .signed_contributions_available && (
              <div className="ai-report-trace-note">
                <ShieldCheck className="size-4" />
                <span>
                  {
                    report.explainability
                      .signed_contribution_note
                  }
                </span>
              </div>
            )}
          </section>

          <section className="ai-report-panel">
            <header className="ai-report-panel-header">
              <div>
                <span className="ai-report-section-label">
                  5 · GOVERNMENT / REGULATORY EVIDENCE
                </span>
                <h3>
                  Government Evidence & Standards
                </h3>
              </div>
              <ShieldCheck className="size-5" />
            </header>

            {report.government_evidence.records
              .length === 0 ? (
              <div className="ai-report-empty-evidence">
                No verified government/regulatory
                evidence available for this prediction.
              </div>
            ) : (
              <>
                <div className="ai-report-table-wrap">
                  <table className="ai-report-table">
                    <thead>
                      <tr>
                        <th>Regulation / standard</th>
                        <th>Evidence or requirement</th>
                        <th>Current measured value</th>
                        <th>Applicable threshold</th>
                        <th>Compliance</th>
                        <th>Source / reference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.government_evidence.records.map(
                        (item, index) => (
                          <tr
                            key={`${item.kind}-${index}`}
                          >
                            <td>
                              {item.regulation_or_standard ?? (
                                <span className="ai-report-muted">
                                  Verified evidence source —
                                  no stored standard
                                </span>
                              )}
                            </td>
                            <td>
                              {item.evidence_or_requirement ??
                                "N/A"}
                            </td>
                            <td>
                              {item.current_measured_value ??
                                "N/A"}
                            </td>
                            <td>
                              {item.applicable_threshold ??
                                "N/A"}
                            </td>
                            <td>
                              <Badge
                                value={
                                  item.compliance_status
                                }
                              />
                            </td>
                            <td>
                              <div>
                                {item.source_reference ??
                                  "N/A"}
                              </div>
                              {item.reference_url && (
                                <a
                                  href={
                                    item.reference_url
                                  }
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Open source ↗
                                </a>
                              )}
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="ai-report-trace-note">
                  <ShieldCheck className="size-4" />
                  <span>
                    {
                      report.government_evidence
                        .threshold_note
                    }
                  </span>
                </div>
              </>
            )}
          </section>

          <section className="ai-report-panel">
            <header className="ai-report-panel-header">
              <div>
                <span className="ai-report-section-label">
                  6 · RECOMMENDATIONS
                </span>
                <h3>AI recommendations</h3>
              </div>
              <Wrench className="size-5" />
            </header>

            {report.recommendations.length === 0 ? (
              <div className="ai-report-empty-evidence">
                No recommendation is available from the
                current backend recommendation logic.
              </div>
            ) : (
              <div className="ai-report-recommendations">
                {report.recommendations.map(
                  (item, index) => (
                    <article
                      key={`${item.recommendation}-${index}`}
                    >
                      <header>
                        <Badge value={item.priority} />
                        <strong>
                          {item.recommendation}
                        </strong>
                      </header>
                      <dl>
                        <div>
                          <dt>Priority basis</dt>
                          <dd>
                            {item.priority_basis ??
                              "N/A"}
                          </dd>
                        </div>
                        <div>
                          <dt>Reason</dt>
                          <dd>{item.reason}</dd>
                        </div>
                        <div>
                          <dt>Supporting evidence</dt>
                          <dd>
                            {item.supporting_evidence
                              .length
                              ? item.supporting_evidence.join(
                                  " · ",
                                )
                              : "N/A"}
                          </dd>
                        </div>
                        <div>
                          <dt>Expected benefit</dt>
                          <dd>
                            {item.expected_benefit ??
                              "Not quantified by current recommendation logic"}
                          </dd>
                        </div>
                        <div>
                          <dt>Suggested timeframe</dt>
                          <dd>
                            {item.suggested_timeframe ??
                              "Not specified by current recommendation logic"}
                          </dd>
                        </div>
                      </dl>
                    </article>
                  ),
                )}
              </div>
            )}
          </section>

          <section className="ai-report-panel">
            <header className="ai-report-panel-header">
              <div>
                <span className="ai-report-section-label">
                  7 · SUPPORTING DATA
                </span>
                <h3>
                  Prediction inputs and measured context
                </h3>
              </div>
              <Database className="size-5" />
            </header>

            <div className="ai-report-table-wrap">
              <table className="ai-report-table">
                <thead>
                  <tr>
                    <th>Sensor / input</th>
                    <th>Current value</th>
                    <th>
                      Expected / historical range
                    </th>
                    <th>Status</th>
                    <th>Trend</th>
                    <th>Last updated</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {report.supporting_data.length ===
                  0 ? (
                    <tr>
                      <td colSpan={7}>
                        No sensor/environment supporting
                        data is stored for this asset.
                      </td>
                    </tr>
                  ) : (
                    report.supporting_data.map(
                      (item) => (
                        <tr
                          key={`${item.name}-${item.source}`}
                        >
                          <td>{label(item.name)}</td>
                          <td>
                            {valueWithUnit(
                              item.current_value,
                              item.unit,
                            )}
                          </td>
                          <td>
                            {item.expected_range ?? "N/A"}
                            {item.reference_type ===
                              "HISTORICAL_EMPIRICAL_P05_P95" && (
                              <small className="ai-report-block-note">
                                Historical P05–P95, not a
                                regulatory threshold
                              </small>
                            )}
                          </td>
                          <td>
                            <Badge
                              value={item.status}
                            />
                          </td>
                          <td>
                            {label(item.trend)}
                          </td>
                          <td>
                            {dateTime(
                              item.last_updated,
                            )}
                          </td>
                          <td>
                            {item.source ?? "N/A"}
                          </td>
                        </tr>
                      ),
                    )
                  )}
                </tbody>
              </table>
            </div>

            <div className="ai-report-support-charts">
              {report.supporting_data
                .filter(
                  (item) => item.history.length >= 2,
                )
                .slice(0, 6)
                .map((item) => (
                  <article
                    key={`chart-${item.name}-${item.source}`}
                  >
                    <header>
                      <strong>
                        {label(item.name)}
                      </strong>
                      <Badge value={item.trend} />
                    </header>
                    <MiniTrend
                      points={item.history}
                      ariaLabel={`${item.name} historical trend`}
                    />
                    <small>
                      {item.unit ?? "Value"} ·{" "}
                      {item.history.length} stored
                      point(s)
                    </small>
                  </article>
                ))}
            </div>
          </section>

          <section className="ai-report-panel">
            <header className="ai-report-panel-header">
              <div>
                <span className="ai-report-section-label">
                  8 · PREDICTION TRANSPARENCY
                </span>
                <h3>Model and data traceability</h3>
              </div>
              <ShieldCheck className="size-5" />
            </header>

            <div className="ai-report-transparency-grid">
              <article>
                <span>Prediction</span>
                <strong>
                  {label(
                    report.transparency.prediction,
                  )}
                </strong>
              </article>
              <article>
                <span>Confidence</span>
                <strong>
                  {percent(
                    report.transparency.confidence,
                  )}
                </strong>
              </article>
              <article>
                <span>Model</span>
                <strong>
                  {report.transparency.model_name ??
                    "N/A"}
                </strong>
                <small>
                  {report.transparency.model_version ??
                    "Version N/A"}
                </small>
              </article>
              <article>
                <span>Prediction generated</span>
                <strong>
                  {dateTime(
                    report.transparency
                      .prediction_generated_at,
                  )}
                </strong>
              </article>
              <article>
                <span>Data points used</span>
                <strong>
                  {
                    report.transparency
                      .data_points_used
                  }
                </strong>
              </article>
              <article>
                <span>Evidence records</span>
                <strong>
                  {
                    report.transparency
                      .evidence_record_count
                  }
                </strong>
              </article>
            </div>

            <div className="ai-report-model-footer">
              <span>
                Method:{" "}
                {label(
                  report.transparency
                    .prediction_method,
                )}
              </span>
              <span>
                Stage:{" "}
                {label(
                  report.transparency.model_stage,
                )}
              </span>
              <span>
                Local validation:{" "}
                {report.transparency
                  .model_validated
                  ? "Validated"
                  : "Not established"}
              </span>
              <span>
                Training scope:{" "}
                {label(
                  report.transparency
                    .training_scope,
                )}
              </span>
            </div>
          </section>

          <footer className="ai-report-footer">
            <ShieldCheck className="size-4" />
            <p>
              All populated values in this report come
              from the current SIMRAS database, stored
              histories, canonical Twin/ML output, or
              authoritative source metadata. Missing
              failure probabilities, government
              thresholds, regulatory standards, and
              signed XAI contributions remain explicitly
              unavailable.
            </p>
          </footer>
        </div>
      )}
    </section>
  );
}
