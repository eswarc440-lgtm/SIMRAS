import { describe, expect, it } from "vitest";
import { rankDigitalTwins } from "./twinPriority";

type Asset = {
  asset_code: string;
  name: string;
  twin_quality_score?: number;
  risk_score?: number;
  fidelity_level?: string;
  twin_fidelity?: string;
  twin_group?: string;
};

describe("rankDigitalTwins", () => {
  it("places source-backed showcase assets before high-risk approximate assets", () => {
    const items: Asset[] = [
      {
        asset_code: "AP_DAM_RANDOM",
        name: "Approximate High Risk Asset",
        twin_quality_score: 99,
        risk_score: 99,
        fidelity_level: "L0",
      },
      {
        asset_code: "AP_DAM_00001",
        name: "Prakasam Barrage",
        twin_quality_score: 50,
        risk_score: 1,
        fidelity_level: "L2",
      },
      {
        asset_code: "AP_DAM_00002",
        name: "Polavaram Irrigation Project",
        twin_quality_score: 50,
        risk_score: 1,
        fidelity_level: "L2",
      },
    ];

    expect(rankDigitalTwins(items).map((item) => item.asset_code)).toEqual([
      "AP_DAM_00002",
      "AP_DAM_00001",
      "AP_DAM_RANDOM",
    ]);
  });

  it("uses fidelity then evidence quality then name for non-showcase assets and ignores risk", () => {
    const items: Asset[] = [
      { asset_code: "C", name: "Zulu", twin_quality_score: 80, risk_score: 90, fidelity_level: "L0" },
      { asset_code: "B", name: "Beta", twin_quality_score: 40, risk_score: 99, fidelity_level: "L1" },
      { asset_code: "A", name: "Alpha", twin_quality_score: 60, risk_score: 1, fidelity_level: "L1" },
    ];

    expect(rankDigitalTwins(items).map((item) => item.asset_code)).toEqual(["A", "B", "C"]);
  });
});


describe("canonical temple priority", () => {
  it("recognizes AP_TEMPLE_TIRUMALA as the showcase Tirumala twin", () => {
    const items: Asset[] = [
      { asset_code: "AP_TEMPLE_OTHER", name: "Other Temple", twin_quality_score: 999, fidelity_level: "L1" },
      { asset_code: "AP_TEMPLE_TIRUMALA", name: "Sri Venkateswara Swamy Temple, Tirumala", twin_quality_score: 1, fidelity_level: "L1" },
    ];

    expect(rankDigitalTwins(items)[0].asset_code).toBe("AP_TEMPLE_TIRUMALA");
  });
});
