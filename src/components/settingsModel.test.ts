import { describe, expect, it } from "vitest";
import { defaultPreferences, mergePreferences } from "./settingsModel";
describe("settings model", () => {
  it("deep-merges a section without losing other defaults", () => { const next = mergePreferences(defaultPreferences, { gis: { rememberLastPosition: true } }); expect(next.gis.rememberLastPosition).toBe(true); expect(next.twin.renderingQuality).toBe("auto"); });
  it("does not mutate defaults", () => { mergePreferences(defaultPreferences, { accessibility: { reducedMotion: true } }); expect(defaultPreferences.accessibility.reducedMotion).toBe(false); });
});
