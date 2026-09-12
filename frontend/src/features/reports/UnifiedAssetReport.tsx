type Props = {
  report: any;
};

type Row = {
  label: string;
  value: unknown;
};

type DetailRow = {
  item: string;
  details: string;
};

function getPath(object: any, path: string): any {
  return path.split(".").reduce(
    (value: any, key: string) =>
      value == null ? undefined : value[key],
    object,
  );
}

function pick(report: any, paths: string[]): any {
  for (const path of paths) {
    const value = getPath(report, path);
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return undefined;
}

function asNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function text(value: unknown, fallback = "NOT AVAILABLE"): string {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  if (typeof value === "boolean") {
    return value ? "YES" : "NO";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }

  return String(value);
}

function score(value: unknown): string {
  const n = asNumber(value);
  return n === undefined ? "WITHHELD" : `${n.toFixed(1)} / 100`;
}

function percent(value: unknown): string {
  const n = asNumber(value);
  if (n === undefined) {
    return "WITHHELD";
  }
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(0)}%`;
}

function unit(value: unknown, suffix: string): string {
  if (value === undefined || value === null || value === "") {
    return "UNKNOWN";
  }
  return `${String(value)} ${suffix}`;
}

function humanize(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

function itemTitle(item: any, index: number): string {
  const keys = [
    "title",
    "label",
    "name",
    "factor",
    "metric",
    "parameter",
    "recommendation",
    "source",
    "date",
    "time",
    "timestamp",
  ];

  for (const key of keys) {
    if (item && item[key] !== undefined && item[key] !== null && item[key] !== "") {
      return String(item[key]);
    }
  }

  return `Record ${index + 1}`;
}

function normalizeDetails(value: any): DetailRow[] {
  if (value === undefined || value === null || value === "") {
    return [];
  }

  if (Array.isArray(value)) {
    return value.slice(0, 50).map((item: any, index: number) => {
      if (item === null || item === undefined) {
        return {
          item: `Record ${index + 1}`,
          details: "NOT AVAILABLE",
        };
      }

      if (typeof item !== "object") {
        return {
          item: `Record ${index + 1}`,
          details: String(item),
        };
      }

      const title = itemTitle(item, index);
      const detailParts = Object.entries(item)
        .filter(([key]) => String(item[key]) !== title)
        .slice(0, 6)
        .map(([key, val]) => `${humanize(key)}: ${text(val)}`);

      return {
        item: title,
        details: detailParts.length ? detailParts.join(" | ") : text(item),
      };
    });
  }

  if (typeof value === "object") {
    return Object.entries(value).slice(0, 50).map(([key, val]) => ({
      item: humanize(key),
      details: text(val),
    }));
  }

  return [
    {
      item: "Information",
      details: String(value),
    },
  ];
}

function SummaryCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="flex min-h-[88px] items-center justify-between gap-4 border border-slate-800 bg-slate-950/25 px-5 py-3">
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {label}
        </div>

        {note ? (
          <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">
            {note}
          </div>
        ) : null}
      </div>

      <div className="shrink-0 text-right text-xl font-bold text-slate-100">
        {value}
      </div>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: any;
}) {
  return (
    <section className="overflow-hidden border border-slate-800 bg-slate-950/20">
      <div className="border-b border-slate-800 bg-slate-900/30 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-100">
          {title}
        </h2>
      </div>
      <div className="p-5">
        {children}
      </div>
    </section>
  );
}

function KeyValueTable({
  rows,
}: {
  rows: Row[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-b border-slate-800 last:border-b-0">
              <td className="w-[42%] px-3 py-3 text-slate-300">
                {row.label}
              </td>
              <td className="px-3 py-3 font-semibold text-slate-100 break-words">
                {text(row.value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailTable({
  rows,
  emptyText,
}: {
  rows: DetailRow[];
  emptyText: string;
}) {
  if (!rows.length) {
    return (
      <div className="text-sm text-slate-400">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              Item
            </th>
            <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              Details
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.item}-${index}`} className="border-b border-slate-800 last:border-b-0">
              <td className="w-[32%] px-3 py-3 text-slate-200 align-top">
                {row.item}
              </td>
              <td className="px-3 py-3 text-slate-300 align-top break-words">
                {row.details}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function UnifiedAssetReport({ report }: Props) {
  const assetType = String(
    pick(report, [
      "asset.asset_type",
      "asset.type",
      "asset_type",
      "identity.asset_type",
      "infrastructure_type",
      "assetIdentity.infrastructure_type",
    ]) ?? "unknown",
  ).toUpperCase();

  const assetName = pick(report, [
    "asset.name",
    "asset_name",
    "name",
    "assetIdentity.asset_name",
    "selected_asset.name",
  ]);

  const assetCode = pick(report, [
    "asset.asset_code",
    "asset_code",
    "identity.asset_code",
    "assetIdentity.asset_code",
    "selected_asset.asset_code",
  ]);

  const district = pick(report, [
    "asset.district",
    "district",
    "assetIdentity.district",
    "selected_asset.district",
  ]);

  const healthScore = pick(report, [
    "health_score",
    "prediction.health_score",
    "prediction.structural.health_score",
    "decision_support.prediction.structural.health_score",
    "assessment.health_score",
    "summary.health_score",
  ]);

  const riskLevel = pick(report, [
    "structural_risk_level",
    "prediction.structural.risk_level",
    "decision_support.prediction.structural.risk_level",
    "risk_level",
    "summary.risk_level",
  ]);

  const riskScore = pick(report, [
    "structural_risk_score",
    "prediction.structural.risk_score",
    "decision_support.prediction.structural.risk_score",
    "risk_score",
    "summary.risk_score",
  ]);

  const confidence = pick(report, [
    "confidence",
    "prediction.confidence",
    "prediction.prediction_confidence",
    "decision_support.prediction.prediction_confidence",
    "summary.confidence",
  ]);

  const rul = pick(report, [
    "rul_years",
    "remaining_useful_life_years",
    "prediction.remaining_useful_life.estimate_years",
    "decision_support.prediction.remaining_useful_life.estimate_years",
    "summary.rul_years",
  ]);

  const identityRows: Row[] = [
    { label: "Asset Code", value: assetCode },
    { label: "Infrastructure Type", value: assetType },
    { label: "District", value: district },
    {
      label: "Identity Status",
      value: pick(report, [
        "asset.identity_status",
        "identity_status",
        "assetIdentity.identity_status",
        "selected_asset.identity_status",
      ]),
    },
    {
      label: "Geometry Source",
      value: pick(report, [
        "asset.geometry_source",
        "geometry_source",
        "assetIdentity.geometry_source",
      ]),
    },
    {
      label: "Generated",
      value: pick(report, [
        "generated_at",
        "metadata.generated_at",
        "report_generated",
      ]),
    },
  ];

  const engineeringRows: Row[] = [
    {
      label: "Length",
      value: unit(
        pick(report, [
          "engineering.length_m",
          "engineering_profile.length_m",
          "dimensions.length_m",
          "length_m",
          "infrastructureSpecifications.length",
        ]),
        "m",
      ),
    },
    {
      label: "Width",
      value: unit(
        pick(report, [
          "engineering.width_m",
          "engineering_profile.width_m",
          "dimensions.width_m",
          "width_m",
          "infrastructureSpecifications.width",
        ]),
        "m",
      ),
    },
    {
      label: "Height",
      value: unit(
        pick(report, [
          "engineering.height_m",
          "engineering_profile.height_m",
          "dimensions.height_m",
          "height_m",
          "infrastructureSpecifications.height",
        ]),
        "m",
      ),
    },
    {
      label: "Built Year",
      value: pick(report, [
        "engineering.built_year",
        "engineering_profile.built_year",
        "built_year",
        "infrastructureSpecifications.built_year",
      ]),
    },
    {
      label: "Material",
      value: pick(report, [
        "engineering.material",
        "engineering_profile.material",
        "material",
        "infrastructureSpecifications.material",
      ]),
    },
  ];

  if (assetType === "DAM") {
    engineeringRows.push(
      {
        label: "Gross Storage",
        value: unit(
          pick(report, [
            "engineering.gross_storage_mcm",
            "engineering_profile.gross_storage_mcm",
            "gross_storage_mcm",
          ]),
          "MCM",
        ),
      },
      {
        label: "Effective Storage",
        value: unit(
          pick(report, [
            "engineering.effective_storage_mcm",
            "engineering_profile.effective_storage_mcm",
            "effective_storage_mcm",
          ]),
          "MCM",
        ),
      },
      {
        label: "FRL",
        value: unit(
          pick(report, [
            "engineering.frl_m",
            "frl_m",
          ]),
          "m",
        ),
      },
      {
        label: "MWL",
        value: unit(
          pick(report, [
            "engineering.mwl_m",
            "mwl_m",
          ]),
          "m",
        ),
      },
      {
        label: "Gates",
        value: pick(report, [
          "engineering.gate_count",
          "gate_count",
          "infrastructureSpecifications.gates",
        ]),
      },
    );
  }

  if (assetType === "BARRAGE") {
    engineeringRows.push(
      {
        label: "Pier Count",
        value: pick(report, [
          "engineering.pier_count",
          "pier_count",
        ]),
      },
      {
        label: "Gate Count",
        value: pick(report, [
          "engineering.gate_count",
          "gate_count",
        ]),
      },
      {
        label: "Flow Velocity",
        value: unit(
          pick(report, [
            "hydrology.velocity_mps",
            "velocity_mps",
          ]),
          "m/s",
        ),
      },
    );
  }

  if (assetType === "BRIDGE") {
    engineeringRows.push(
      {
        label: "Bridge Type",
        value: pick(report, [
          "engineering.bridge_type",
          "bridge_type",
        ]),
      },
      {
        label: "Span Count",
        value: pick(report, [
          "engineering.span_count",
          "span_count",
          "infrastructureSpecifications.spans",
        ]),
      },
      {
        label: "Pier Count",
        value: pick(report, [
          "engineering.pier_count",
          "pier_count",
          "infrastructureSpecifications.piers",
        ]),
      },
      {
        label: "Deck Width",
        value: unit(
          pick(report, [
            "engineering.deck_width_m",
            "deck_width_m",
          ]),
          "m",
        ),
      },
    );
  }

  if (assetType === "ROAD") {
    engineeringRows.push(
      {
        label: "Road Class",
        value: pick(report, [
          "engineering.road_class",
          "road_class",
        ]),
      },
      {
        label: "Lanes",
        value: pick(report, [
          "engineering.lanes",
          "lanes",
          "lane_count",
        ]),
      },
      {
        label: "Pavement Type",
        value: pick(report, [
          "engineering.pavement_type",
          "pavement_type",
        ]),
      },
    );
  }

  if (assetType === "AIRPORT") {
    engineeringRows.push(
      {
        label: "IATA",
        value: pick(report, ["asset.iata", "iata"]),
      },
      {
        label: "ICAO",
        value: pick(report, ["asset.icao", "icao"]),
      },
      {
        label: "Runway Length",
        value: unit(
          pick(report, [
            "engineering.runway_length_m",
            "runway_length_m",
          ]),
          "m",
        ),
      },
      {
        label: "Runway Width",
        value: unit(
          pick(report, [
            "engineering.runway_width_m",
            "runway_width_m",
          ]),
          "m",
        ),
      },
    );
  }

  if (assetType === "TEMPLE") {
    engineeringRows.push(
      {
        label: "Construction Period",
        value: pick(report, [
          "engineering.construction_period",
          "construction_period",
        ]),
      },
      {
        label: "Heritage Status",
        value: pick(report, [
          "heritage.status",
          "heritage_status",
        ]),
      },
      {
        label: "Gopuram Height",
        value: unit(
          pick(report, [
            "engineering.gopuram_height_m",
            "gopuram_height_m",
          ]),
          "m",
        ),
      },
    );
  }

  const transparencyRows: Row[] = [
    {
      label: "Model",
      value: pick(report, [
        "model.name",
        "prediction.model_name",
        "model_name",
      ]),
    },
    {
      label: "Model Version",
      value: pick(report, [
        "model.version",
        "prediction.model_version",
        "model_version",
      ]),
    },
    {
      label: "Prediction Method",
      value: pick(report, [
        "prediction.prediction_method",
        "prediction_method",
      ]),
    },
    {
      label: "Feature Version",
      value: pick(report, [
        "prediction.feature_version",
        "feature_version",
      ]),
    },
    {
      label: "Model Stage",
      value: pick(report, [
        "model.stage",
        "prediction.stage",
        "model_stage",
      ]),
    },
    {
      label: "Local Validation",
      value:
        pick(report, [
          "model.locally_validated",
          "decision_support.model.locally_validated",
        ]) === true
          ? "AP LOCALLY VALIDATED"
          : "VALIDATION PENDING / EVIDENCE GATED",
    },
  ];

  const factorRows = normalizeDetails(
    pick(report, [
      "prediction.factors",
      "explanation.factors",
      "model_explanation.factors",
      "factors",
    ]),
  );

  const evidenceRows = normalizeDetails(
    pick(report, [
      "government_evidence",
      "official_evidence",
      "evidence.records",
      "evidence",
    ]),
  );

  const recommendationRows = normalizeDetails(
    pick(report, [
      "recommendations",
      "assessment.recommendations",
      "prediction.recommendations",
    ]),
  );

  const supportingRows = normalizeDetails(
    pick(report, [
      "supporting_data",
      "observations",
      "current_observations",
      "environmental_data",
      "hydrology",
      "climate",
    ]),
  );

  const historyRows = normalizeDetails(
    pick(report, [
      "historical_trends",
      "history",
      "timeseries",
      "time_series",
    ]),
  );

  return (
    <div
      data-simras-compact-report="true"
      className="mx-auto max-w-[1700px] space-y-5"
    >
      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-6">
        <div className="text-sm font-semibold text-slate-100">
          SIMRAS Asset Health Assessment Report
        </div>

        <h1 className="mt-6 text-4xl font-bold text-slate-100">
          {text(assetName, "Selected Infrastructure")}
        </h1>

        <div className="mt-8 text-3xl font-semibold text-slate-100">
          {assetType} - Selected Asset Report
        </div>
      </div>

      <Panel title="Condition & Risk Summary">
        <div className="grid gap-2 sm:grid-cols-1 md:grid-cols-2 xl:grid-cols-5">
          <SummaryCard
            label="Health Score"
            value={score(healthScore)}
            note="Current asset health output."
          />
          <SummaryCard
            label="Risk Level"
            value={text(riskLevel, "WITHHELD")}
            note="Current structural risk level."
          />
          <SummaryCard
            label="Risk Score"
            value={score(riskScore)}
            note="Current structural risk score."
          />
          <SummaryCard
            label="Confidence"
            value={percent(confidence)}
            note="Current model/input confidence."
          />
          <SummaryCard
            label="Remaining Useful Life"
            value={
              asNumber(rul) === undefined
                ? "WITHHELD"
                : `${asNumber(rul)!.toFixed(1)} years`
            }
            note="Shown only when evidence supports RUL."
          />
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Asset Identity">
          <KeyValueTable rows={identityRows} />
        </Panel>

        <Panel title="Infrastructure Specifications">
          <KeyValueTable rows={engineeringRows} />
        </Panel>

        <Panel title="Why the Model Predicted This">
          <DetailTable
            rows={factorRows}
            emptyText="No validated model explanation is currently available."
          />
        </Panel>

        <Panel title="Government Evidence & Standards">
          <DetailTable
            rows={evidenceRows}
            emptyText="No authoritative evidence is currently available."
          />
        </Panel>

        <Panel title="Recommendations">
          <DetailTable
            rows={recommendationRows}
            emptyText="No evidence-backed recommendations are currently available."
          />
        </Panel>

        <Panel title="Supporting Data">
          <DetailTable
            rows={supportingRows}
            emptyText="No supporting observations are currently available."
          />
        </Panel>

        <Panel title="Historical Trends">
          <DetailTable
            rows={historyRows}
            emptyText="No validated historical trend records are currently available."
          />
        </Panel>

        <Panel title="Prediction Transparency">
          <KeyValueTable rows={transparencyRows} />
        </Panel>
      </div>
    </div>
  );
}

