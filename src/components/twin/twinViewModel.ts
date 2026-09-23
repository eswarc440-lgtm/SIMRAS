import type { AssetSummary } from "../../types/twin";

type UnknownRecord = Record<string, any>;

const dimensionUnits: Record<string, string> = {
  length_m: "m",
  height_m: "m",
  width_m: "m",
  gate_width_m: "m",
  gate_height_m: "m",
  gate_count: "Nos.",
  regulator_gates: "Nos.",
  left_scour_sluices: "Nos.",
  right_scour_sluices: "Nos.",
  completion_year: "-",
  built_year: "-",
};

const telemetryMetrics = [
  ["water_level_m", "Water Level", "m"],
  ["storage_tmc", "Storage", "TMC"],
  ["storage_percent", "Storage", "%"],
  ["inflow_cusecs", "Inflow", "cusecs"],
  ["outflow_cusecs", "Discharge", "cusecs"],
  ["gates_open", "Gates Open", "Nos."],
  ["gate_clearance_m", "Gate Clearance", "m"],
] as const;

function labelFor(key: string) {
  return key
    .replace(/_(m|km|nos|year|percent|tmc|cusecs)$/i, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "NOT AVAILABLE";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function buildTwinViewModel(
  asset: AssetSummary,
  twinResponse: UnknownRecord | null | undefined,
  assessment: UnknownRecord | null | undefined,
  telemetry: UnknownRecord | null | undefined,
  inspections: UnknownRecord[] = [],
  maintenance: UnknownRecord[] = [],
) {
  const dimensions = twinResponse?.dimensions ?? twinResponse?.twin?.dimensions ?? {};
  const dimensionSource =
    twinResponse?.source_profile?.authority ??
    twinResponse?.twin?.model_source ??
    "NOT VERIFIED";
  const sources = Array.isArray(telemetry?.sources)
    ? telemetry.sources.filter(Boolean).map(String)
    : [];
  const telemetryStatus = sources.some((source) => /simulat/i.test(source))
    ? "SIMULATED"
    : "LATEST AVAILABLE";

  return {
    healthScore: asset.health_score ?? assessment?.health_score ?? null,
    riskScore: asset.risk_score ?? assessment?.risk_score ?? null,
    riskLevel: asset.risk_level ?? assessment?.risk_level ?? null,
    rulYears:
      assessment?.rul_years ??
      assessment?.rul_prediction?.predicted_rul_years ??
      asset.remaining_useful_life_years ??
      null,
    lastInspection:
      inspections[0]?.inspection_date ?? asset.last_inspection_date ?? null,
    dimensions: Object.entries(dimensions).map(([key, value]) => ({
      parameter: labelFor(key),
      value: displayValue(value),
      unit: dimensionUnits[key] ?? "-",
      source: String(dimensionSource),
    })),
    telemetry: telemetry
      ? telemetryMetrics.flatMap(([key, metric, unit]) =>
          telemetry[key] === null || telemetry[key] === undefined
            ? []
            : [
                {
                  metric,
                  value: displayValue(telemetry[key]),
                  unit,
                  status: telemetryStatus,
                  lastUpdated: telemetry.last_sync ?? "NOT AVAILABLE",
                  source: sources.join(", ") || "NOT VERIFIED",
                },
              ],
        )
      : [],
    telemetryState: telemetry ? telemetryStatus : "DATA NOT AVAILABLE",
    inspections: inspections.slice(0, 5).map((record) => ({
      id: record.id,
      date: record.inspection_date ?? "NOT AVAILABLE",
      inspector: record.inspector_name ?? "NOT AVAILABLE",
      type: record.inspection_type ?? "NOT AVAILABLE",
      condition: record.condition_rating ?? "NOT AVAILABLE",
      defects: Array.isArray(record.defects) ? record.defects.length : 0,
      status: record.status ?? "NOT AVAILABLE",
    })),
    maintenance: maintenance.slice(0, 5).map((record) => ({
      id: record.id,
      title: record.title ?? "NOT AVAILABLE",
      category: record.category ?? "NOT AVAILABLE",
      priority: record.priority ?? "NOT AVAILABLE",
      dueDate: record.scheduled_end ?? record.due_date ?? "NOT AVAILABLE",
      status: record.status ?? "NOT AVAILABLE",
    })),
  };
}

export type TwinViewModel = ReturnType<typeof buildTwinViewModel>;
