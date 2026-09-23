import { describe, expect, it } from "vitest";
import { buildTwinViewModel } from "./twinViewModel";

const asset = {
  asset_code: "AP_DAM_00001",
  name: "Prakasam Barrage",
  asset_type: "BARRAGE",
  identity_status: "VERIFIED",
  health_score: 78,
  risk_score: 22,
  risk_level: "LOW",
} as any;

describe("buildTwinViewModel", () => {
  it("does not invent dimensions, telemetry, inspections, or maintenance", () => {
    const view = buildTwinViewModel(asset, {}, {}, null, [], []);

    expect(view.dimensions).toEqual([]);
    expect(view.telemetry).toEqual([]);
    expect(view.telemetryState).toBe("DATA NOT AVAILABLE");
    expect(view.inspections).toEqual([]);
    expect(view.maintenance).toEqual([]);
    expect(JSON.stringify(view)).not.toMatch(/587\.5|32\.0|1995|LIVE/);
  });

  it("maps source-backed dimensions and keeps zero telemetry values", () => {
    const view = buildTwinViewModel(
      asset,
      {
        dimensions: { length_m: 1232.92, gate_count: 70 },
        source_profile: { authority: "AP WRD" },
      },
      { rul_years: 18.5 },
      {
        water_level_m: 0,
        last_sync: "2026-09-23T08:00:00Z",
        sources: ["Official reported gauge"],
      },
      [],
      [],
    );

    expect(view.dimensions).toEqual([
      { parameter: "Length", value: "1232.92", unit: "m", source: "AP WRD" },
      { parameter: "Gate Count", value: "70", unit: "Nos.", source: "AP WRD" },
    ]);
    expect(view.telemetry[0]).toMatchObject({
      metric: "Water Level",
      value: "0",
      unit: "m",
      status: "LATEST AVAILABLE",
      source: "Official reported gauge",
    });
  });

  it("labels simulation sources and maps recent operational records", () => {
    const view = buildTwinViewModel(
      asset,
      {},
      {},
      { inflow_cusecs: 120, sources: ["Simulation model"] },
      [{ id: "INSP-1", inspection_date: "2026-09-20", condition_rating: "GOOD", defects: [] }],
      [{ id: "WO-1", title: "Gate service", category: "MECHANICAL", priority: "HIGH", status: "PLANNED" }],
    );

    expect(view.telemetry[0].status).toBe("SIMULATED");
    expect(view.inspections[0].id).toBe("INSP-1");
    expect(view.maintenance[0].priority).toBe("HIGH");
  });
});
