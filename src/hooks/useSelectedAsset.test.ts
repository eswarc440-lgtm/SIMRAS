import { describe, expect, it } from "vitest";
import {
  buildAssetUrl,
  readSelectedAssetCode,
  resolveSelectedAssetCode,
} from "./useSelectedAsset";

const assets = [
  { asset_code: "AP_DAM_00001", name: "Prakasam Barrage" },
  { asset_code: "AP_BR_00001", name: "Godavari Arch Bridge" },
] as any[];

describe("selected asset URL model", () => {
  it("restores a valid asset from the query string", () => {
    expect(readSelectedAssetCode("?asset=AP_BR_00001")).toBe("AP_BR_00001");
    expect(resolveSelectedAssetCode(assets, "AP_BR_00001")).toBe("AP_BR_00001");
  });

  it("falls back only to a real registry asset", () => {
    expect(resolveSelectedAssetCode(assets, "UNKNOWN")).toBe("AP_DAM_00001");
    expect(resolveSelectedAssetCode([], "UNKNOWN")).toBeNull();
  });

  it("builds shareable workflow URLs and preserves unrelated filters", () => {
    expect(buildAssetUrl("digital-twin", "AP_DAM_00001")).toBe(
      "/digital-twin?asset=AP_DAM_00001",
    );
    expect(
      buildAssetUrl(undefined, "AP_BR_00001", "/gis?risk=HIGH"),
    ).toBe("/gis?risk=HIGH&asset=AP_BR_00001");
  });
});
