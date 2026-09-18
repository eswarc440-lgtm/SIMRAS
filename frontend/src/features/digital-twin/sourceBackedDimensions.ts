export type SourceBackedDimensionMetric = {
  key: string;
  label: string;
  value: string;
  status: string;
  source: string;
  category: string;
};

const unavailableValues = new Set([
  "",
  "N/A",
  "NA",
  "NULL",
  "NONE",
  "UNKNOWN",
  "WITHHELD",
  "NOT VERIFIED",
  "NOT_VERIFIED",
  "NOT AVAILABLE",
  "NOT_AVAILABLE",
]);

const aliasesByType: Record<string, Set<string>> = {
  dam: new Set([
    "total_length_m",
    "length_m",
    "dam_length_m",
    "width_m",
    "breadth_m",
    "crest_width_m",
    "height_m",
    "dam_height_m",
    "maximum_dam_height_m",
    "gate_count",
    "gate_width_m",
    "gate_height_m",
    "spillway_length_m",
  ]),
  barrage: new Set([
    "total_length_m",
    "length_m",
    "barrage_length_m",
    "width_m",
    "breadth_m",
    "height_m",
    "barrage_height_m",
    "gate_count",
    "regulator_count",
    "gate_width_m",
    "gate_height_m",
    "left_scouring_sluice_count",
    "right_scouring_sluice_count",
  ]),
  bridge: new Set([
    "total_length_m",
    "length_m",
    "bridge_length_m",
    "width_m",
    "deck_width_m",
    "height_m",
    "bridge_height_m",
    "clearance_m",
    "span_count",
    "pier_count",
    "pillar_count",
    "main_span_m",
  ]),
  airport: new Set([
    "runway_length_m",
    "runway_width_m",
    "runway_strip_length_m",
    "runway_strip_width_m",
    "terminal_length_m",
    "terminal_width_m",
    "terminal_height_m",
    "land_area_acres",
  ]),
  temple: new Set([
    "total_length_m",
    "length_m",
    "temple_length_m",
    "width_m",
    "temple_width_m",
    "height_m",
    "temple_height_m",
    "gopuram_height_m",
    "main_entrance_height_ft",
    "gopuram_tiers",
    "pillar_count",
    "land_area_acres",
  ]),
};

export function selectVerifiedDimensionMetrics<T extends SourceBackedDimensionMetric>(
  metrics: readonly T[],
  assetType: string,
): T[] {
  const allowed = aliasesByType[assetType.toLowerCase()] ?? new Set([
    "total_length_m",
    "length_m",
    "width_m",
    "height_m",
  ]);

  return metrics.filter((metric) => {
    if (!allowed.has(metric.key)) return false;
    if (metric.status !== "VERIFIED") return false;

    const value = String(metric.value ?? "").trim().toUpperCase();
    if (unavailableValues.has(value)) return false;
    if (value.startsWith("INSUFFICIENT")) return false;

    return true;
  });
}
