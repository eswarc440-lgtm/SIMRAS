import { describe, expect, it } from "vitest";
import { normalizeAssetRegistrationPayload } from "./assetRegistration";

describe("asset registration payload", () => {
  it("normalizes the wizard payload into the API contract", () => {
    const payload = normalizeAssetRegistrationPayload({
      asset_code: "",
      name: "Test Bridge",
      type: "bridge",
      subtype: "prestressed_concrete_bridge",
      category: "BRIDGE",
      district: "East Godavari",
      state: "Andhra Pradesh",
      coordinates: { latitude: 16.989, longitude: 81.782 },
      specifications: {
        built_year: 2015,
        material: "Reinforced Concrete",
        dimension_authority: "Roads & Buildings Department",
        length_m: 450,
        height_m: 18,
        element_count: 12,
      },
      condition: "Good",
      health_score: 78.5,
      risk_score: 22,
      priority: 2,
    });

    expect(payload).toMatchObject({
      name: "Test Bridge",
      asset_type: "bridge",
      latitude: 16.989,
      longitude: 81.782,
      dimensions: {
        built_year: 2015,
        material: "Reinforced Concrete",
        dimension_authority: "Roads & Buildings Department",
        length_m: 450,
        height_m: 18,
        element_count: 12,
      },
    });
    expect(payload).not.toHaveProperty("coordinates");
    expect(payload).not.toHaveProperty("specifications");
  });

  it("rejects missing names and out-of-range coordinates", () => {
    expect(() => normalizeAssetRegistrationPayload({ name: "", type: "bridge" })).toThrow(
      "Official asset name is required",
    );
    expect(() =>
      normalizeAssetRegistrationPayload({
        name: "Bad Location",
        type: "bridge",
        coordinates: { latitude: 99, longitude: 81 },
      }),
    ).toThrow("Coordinates must be within Andhra Pradesh bounds");
  });
});
