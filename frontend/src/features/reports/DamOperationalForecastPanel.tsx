import { useEffect, useMemo, useState } from "react";

type ForecastResponse = {
  asset_code?: string;
  asset_name?: string;
  district?: string;

  status?: string;
  reason?: string;

  observation_date?: string | null;
  prediction_date?: string | null;

  observed_level_m?: number | null;
  predicted_level_m?: number | null;

  observed_storage_mcm?: number | null;
  predicted_storage_mcm?: number | null;

  level_status?: string | null;
  storage_status?: string | null;

  level_test_mae?: number | null;
  level_baseline_mae?: number | null;

  storage_test_mae?: number | null;
  storage_baseline_mae?: number | null;

  forecast_method_level?: string | null;
  forecast_method_storage?: string | null;

  history_days?: number | null;
  test_rows?: number | null;

  confidence?: number | null;

  model_status?: string | null;
  prediction_semantics?: string | null;
  source_name?: string | null;

  structural_prediction?: boolean;
  structural_health?: string | null;
  structural_failure_risk?: string | null;
  rul?: string | null;
};

type Props = {
  assetCode: string;
};

function buildApiCandidates(assetCode: string): string[] {
  const code = encodeURIComponent(assetCode);

  const configured = String(
    import.meta.env.VITE_API_BASE_URL ?? "",
  ).replace(/\/+$/, "");

  const urls: string[] = [];

  if (configured) {
    if (/\/api\/v1$/i.test(configured)) {
      urls.push(
        `${configured}/assets/${code}/operational-forecast`,
      );
    } else {
      urls.push(
        `${configured}/api/v1/assets/${code}/operational-forecast`,
      );
    }
  }

  urls.push(
    `/api/v1/assets/${code}/operational-forecast`,
  );

  urls.push(
    `http://localhost:8000/api/v1/assets/${code}/operational-forecast`,
  );

  return [...new Set(urls)];
}

async function fetchForecast(
  assetCode: string,
  signal: AbortSignal,
): Promise<ForecastResponse> {
  const urls = buildApiCandidates(assetCode);

  let lastError: unknown = null;

  for (const url of urls) {
    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        signal,
      });

      if (!response.ok) {
        lastError = new Error(
          `Forecast API returned ${response.status}`,
        );
        continue;
      }

      return (await response.json()) as ForecastResponse;
    } catch (error) {
      if (signal.aborted) {
        throw error;
      }

      lastError = error;
    }
  }

  throw (
    lastError ??
    new Error("Operational forecast API unavailable")
  );
}

function valueOrWithheld(
  value: number | null | undefined,
  unit: string,
  digits = 2,
): string {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return "WITHHELD";
  }

  return `${value.toFixed(digits)} ${unit}`;
}

function formatDate(
  value: string | null | undefined,
): string {
  if (!value) {
    return "WITHHELD";
  }

  const parsed = new Date(`${value}T00:00:00`);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString();
}

function displayMethod(
  value: string | null | undefined,
): string {
  if (!value) {
    return "WITHHELD";
  }

  if (value === "EXTRA_TREES") {
    return "Extra Trees ML";
  }

  if (value === "PERSISTENCE") {
    return "Persistence baseline";
  }

  return value.replaceAll("_", " ");
}

function displayStatus(
  value: string | null | undefined,
): string {
  if (!value) {
    return "WITHHELD";
  }

  return value.replaceAll("_", " ");
}

export default function DamOperationalForecastPanel({
  assetCode,
}: Props) {
  const [data, setData] =
    useState<ForecastResponse | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setError(null);
    setData(null);

    void fetchForecast(
      assetCode,
      controller.signal,
    )
      .then((response) => {
        setData(response);
      })
      .catch((requestError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Operational forecast unavailable",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [assetCode]);

  const status = useMemo(() => {
    if (!data) {
      return "WITHHELD";
    }

    return (
      data.model_status ??
      data.status ??
      "WITHHELD"
    );
  }, [data]);

  const isMl =
    status === "VALIDATED_OPERATIONAL_ML";

  const isBaseline =
    status === "VALIDATED_PERSISTENCE_BASELINE";

  const isReportable =
    isMl || isBaseline;

  const statusClass = isMl
    ? "border-emerald-300 bg-emerald-50 text-emerald-800"
    : isBaseline
      ? "border-blue-300 bg-blue-50 text-blue-800"
      : "border-amber-300 bg-amber-50 text-amber-900";

  if (loading) {
    return (
      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <h3 className="text-base font-semibold">
          Operational Reservoir Forecast
        </h3>

        <p className="mt-2 text-sm text-muted-foreground">
          Checking validated reservoir observations and forecast evidence...
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold">
            Operational Reservoir Forecast
          </h3>

          <span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">
            WITHHELD
          </span>
        </div>

        <p className="mt-3 text-sm text-muted-foreground">
          Forecast service is unavailable. No operational prediction is displayed.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">
            Operational Reservoir Forecast
          </h3>

          <p className="mt-1 text-sm text-muted-foreground">
            Next-day reservoir level/storage forecast derived from official observed time-series.
          </p>
        </div>

        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusClass}`}
        >
          {displayStatus(status)}
        </span>
      </div>

      {!isReportable ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="font-medium text-amber-950">
            Current operational prediction withheld
          </div>

          <p className="mt-1 text-sm leading-6 text-amber-900">
            {data?.reason ??
              "No forecast currently satisfies the production freshness and validation gates."}
          </p>

          <p className="mt-2 text-xs text-amber-800">
            SIMRAS does not replace missing or stale observations with synthetic prediction values.
          </p>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label="Observed Water Level"
          value={valueOrWithheld(
            data?.observed_level_m,
            "m",
          )}
        />

        <Metric
          label="Next-Day Water Level"
          value={
            isReportable
              ? valueOrWithheld(
                  data?.predicted_level_m,
                  "m",
                )
              : "WITHHELD"
          }
        />

        <Metric
          label="Observed Storage"
          value={valueOrWithheld(
            data?.observed_storage_mcm,
            "MCM",
          )}
        />

        <Metric
          label="Next-Day Storage"
          value={
            isReportable
              ? valueOrWithheld(
                  data?.predicted_storage_mcm,
                  "MCM",
                )
              : "WITHHELD"
          }
        />
      </div>

      <div className="mt-5 grid gap-x-8 gap-y-3 border-t pt-4 text-sm sm:grid-cols-2">
        <Evidence
          label="Observation Date"
          value={formatDate(
            data?.observation_date,
          )}
        />

        <Evidence
          label="Prediction Date"
          value={
            isReportable
              ? formatDate(
                  data?.prediction_date,
                )
              : "WITHHELD"
          }
        />

        <Evidence
          label="Level Forecast Method"
          value={
            isReportable
              ? displayMethod(
                  data?.forecast_method_level,
                )
              : "WITHHELD"
          }
        />

        <Evidence
          label="Storage Forecast Method"
          value={
            isReportable
              ? displayMethod(
                  data?.forecast_method_storage,
                )
              : "WITHHELD"
          }
        />

        <Evidence
          label="Level Validation MAE"
          value={
            data?.level_test_mae != null
              ? `${data.level_test_mae.toFixed(4)} m`
              : data?.level_baseline_mae != null
                ? `${data.level_baseline_mae.toFixed(4)} m`
                : "WITHHELD"
          }
        />

        <Evidence
          label="Storage Validation MAE"
          value={
            data?.storage_test_mae != null
              ? `${data.storage_test_mae.toFixed(4)} MCM`
              : data?.storage_baseline_mae != null
                ? `${data.storage_baseline_mae.toFixed(4)} MCM`
                : "WITHHELD"
          }
        />

        <Evidence
          label="Confidence"
          value={
            data?.confidence != null
              ? `${Math.round(
                  data.confidence * 100,
                )}%`
              : "WITHHELD"
          }
        />

        <Evidence
          label="Historical Observation Days"
          value={
            data?.history_days != null
              ? String(
                  data.history_days,
                )
              : "WITHHELD"
          }
        />
      </div>

      <div className="mt-5 rounded-lg border bg-muted/30 p-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Prediction Semantics
        </div>

        <p className="mt-1 text-sm">
          Reservoir operational forecasting only. This is not a structural failure probability,
          structural health assessment, or remaining-useful-life estimate.
        </p>
      </div>

      <div className="mt-3 text-xs text-muted-foreground">
        Evidence source:{" "}
        {data?.source_name
          ? data.source_name.replaceAll(
              "_",
              " ",
            )
          : "Official NWDP reservoir observations"}
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  const withheld =
    value === "WITHHELD";

  return (
            <div
              role="row"
              data-simras-report-table-row="true"
              style={{
                display: "grid",
                gridTemplateColumns:
                  "minmax(240px, 34%) minmax(0, 1fr)",
                width: "100%",
                minHeight: 44,
                borderBottom:
                  "1px solid rgba(148,163,184,.16)",
                background:
                  "rgba(2,12,21,.16)",
              }}
            >
              {/* SIMRAS_REPORT_TABLE_ROW_V3 */}

              <div
                role="cell"
                style={{
                  padding: "10px 14px",
                  color: "#94b8d3",
                  fontSize: 13,
                  fontWeight: 500,
                  lineHeight: 1.45,
                  borderRight:
                    "1px solid rgba(148,163,184,.12)",
                }}
              >
                {label}
              </div>

              <div
                role="cell"
                style={{
                  padding: "10px 14px",
                  color: "#f1f5f9",
                  fontSize: 13,
                  fontWeight: 700,
                  lineHeight: 1.45,
                  minWidth: 0,
                  overflowWrap: "anywhere",
                }}
              >
                {value}
              </div>
            </div>
          );
}

function Evidence({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b pb-2">
      <span className="text-muted-foreground">
        {label}
      </span>

      <span className="text-right font-medium">
        {value}
      </span>
    </div>
  );
}