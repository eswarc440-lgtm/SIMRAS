import { describe, expect, it } from "vitest";
import { normalizeCoordinates } from "./coordinates";

describe("normalizeCoordinates", () => {
  it("converts valid GeoJSON coordinates to Leaflet order", () => {
    expect(
      normalizeCoordinates({
        geometry: { type: "Point", coordinates: [80.6053, 16.5062] },
      }),
    ).toEqual({
      geoJson: [80.6053, 16.5062],
      leaflet: [16.5062, 80.6053],
    });
  });

  it("accepts supported latitude and longitude fields", () => {
    expect(
      normalizeCoordinates({ latitude: "16.5062", longitude: "80.6053" }),
    ).toEqual({
      geoJson: [80.6053, 16.5062],
      leaflet: [16.5062, 80.6053],
    });

    expect(
      normalizeCoordinates({
        coordinates: { latitude: 16.5062, longitude: 80.6053 },
      }),
    ).toEqual({
      geoJson: [80.6053, 16.5062],
      leaflet: [16.5062, 80.6053],
    });
  });

  it.each([
    {},
    { geometry: null },
    { geometry: { type: "Point", coordinates: [Number.NaN, 16.5] } },
    { geometry: { type: "Point", coordinates: [181, 16.5] } },
    { geometry: { type: "Point", coordinates: [80.6, 91] } },
    { geometry: { type: "Point", coordinates: [0, 0] } },
  ])("returns null for missing or malformed locations", (input) => {
    expect(normalizeCoordinates(input)).toBeNull();
  });
});
