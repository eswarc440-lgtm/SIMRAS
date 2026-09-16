import { describe, expect, it } from "vitest";
import { selectVerifiedDimensionMetrics } from "./sourceBackedDimensions";

const metrics = [
  { key: "total_length_m", label: "Length", value: "1232.92 m", status: "VERIFIED", source: "AP Water Resources", category: "Dimensions" },
  { key: "gate_count", label: "No. of gates", value: "70", status: "VERIFIED", source: "AP Water Resources", category: "Structure" },
  { key: "width_m", label: "Width", value: "Not available", status: "UNAVAILABLE", source: "No linked source value", category: "Dimensions" },
  { key: "height_m", label: "Height", value: "12 m", status: "ESTIMATED", source: "Visual estimate", category: "Dimensions" },
] as const;

describe("selectVerifiedDimensionMetrics", () => {
  it("keeps only verified source-backed values allowed for the asset type", () => {
    const result = selectVerifiedDimensionMetrics(metrics, "barrage");
    expect(result.map((item) => item.key)).toEqual(["total_length_m", "gate_count"]);
  });

  it("never includes unavailable or estimated dimensions in moving annotations", () => {
    const result = selectVerifiedDimensionMetrics(metrics, "barrage");
    expect(result.some((item) => item.status !== "VERIFIED")).toBe(false);
    expect(result.some((item) => /not available/i.test(item.value))).toBe(false);
  });
});
