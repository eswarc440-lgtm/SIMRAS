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


describe("category-specific structure dimensions", () => {
  it("keeps verified airport runway and runway-strip dimensions for on-structure display", () => {
    const airportMetrics = [
      { key: "runway_length_m", label: "Runway length", value: "2285 m", status: "VERIFIED", source: "AAI eAIP", category: "Dimensions" },
      { key: "runway_width_m", label: "Runway width", value: "45 m", status: "VERIFIED", source: "AAI eAIP", category: "Dimensions" },
      { key: "runway_strip_length_m", label: "Runway strip length", value: "2405 m", status: "VERIFIED", source: "AAI eAIP", category: "Dimensions" },
      { key: "runway_strip_width_m", label: "Runway strip width", value: "150 m", status: "VERIFIED", source: "AAI eAIP", category: "Dimensions" },
    ] as const;

    expect(selectVerifiedDimensionMetrics(airportMetrics, "airport").map((item) => item.key)).toEqual([
      "runway_length_m",
      "runway_width_m",
      "runway_strip_length_m",
      "runway_strip_width_m",
    ]);
  });

  it("keeps verified temple entrance height and gopuram tiers for on-structure display", () => {
    const templeMetrics = [
      { key: "main_entrance_height_ft", label: "Main entrance height", value: "50 ft", status: "VERIFIED", source: "TTD", category: "Dimensions" },
      { key: "gopuram_tiers", label: "Main entrance tiers", value: "7", status: "VERIFIED", source: "TTD", category: "Structure" },
    ] as const;

    expect(selectVerifiedDimensionMetrics(templeMetrics, "temple").map((item) => item.key)).toEqual([
      "main_entrance_height_ft",
      "gopuram_tiers",
    ]);
  });
});
